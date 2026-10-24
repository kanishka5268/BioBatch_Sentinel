# Trusted control service. Agent Python runs in the isolated executor.
import hashlib, json, os, shutil, subprocess, tempfile, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", "/workspace")).resolve()
QUEUE = Path(os.environ.get("QUEUE_DIR", "/queue")).resolve()
PORT = int(os.environ.get("PORT", "8000"))
MAX_OUTPUT, RUN_TIMEOUT, CASE_TIMEOUT, QUEUE_TIMEOUT = 4000, 20, 5, 30

CHILD = r'''
import json, sys
ns = {}
try:
    exec(compile(sys.argv[1], "<check>", "exec"), ns)
    out = {"ok": True, "result": ns.get("result")}
except BaseException as exc:
    out = {"ok": False, "exc": type(exc).__name__}
sys.stdout.write("\\n@@RESULT@@" + json.dumps(out, default=str))
'''

def safe_path(relative):
    path = (WORKSPACE / relative).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError("path must stay inside the project directory")
    return path

def clip(value):
    return value if len(value) <= MAX_OUTPUT else value[:MAX_OUTPUT] + f"\\n[output cut at {MAX_OUTPUT} characters]"

def all_files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path

def tool_list_files(args):
    files = [str(p.relative_to(WORKSPACE)) for p in all_files(WORKSPACE)]
    return "\\n".join(files) if files else "(no files)"

def tool_read_file(args):
    path = safe_path(args["path"])
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {args['path']}")
    return clip(path.read_text(errors="replace"))


def tool_write_file(args):
    path = safe_path(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"])
    os.chmod(path, 0o666)
    return f"wrote {len(args['content'])} characters to {args['path']}"

def tool_run_python(args):
    request_id = uuid.uuid4().hex
    req, resp = QUEUE / f"{request_id}.request.json", QUEUE / f"{request_id}.response.json"
    req.write_text(json.dumps({"id": request_id, "code": args["code"], "timeout": RUN_TIMEOUT}))
    deadline = time.monotonic() + QUEUE_TIMEOUT
    try:
        while time.monotonic() < deadline:
            if resp.exists():
                try:
                    result = json.loads(resp.read_text())
                finally:
                    resp.unlink(missing_ok=True)
                return clip(result.get("output", "(no output)"))
            time.sleep(0.05)
        return "error: isolated executor timed out waiting for a result"
    finally:
        req.unlink(missing_ok=True)
        resp.unlink(missing_ok=True)

TOOLS = {"list_files": tool_list_files, "read_file": tool_read_file,
         "write_file": tool_write_file, "run_python": tool_run_python}


def do_reset(body):
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    for child in WORKSPACE.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)

    for name, content in body["files"].items():
        path = safe_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, 0o666)

    for path in sorted(WORKSPACE.rglob("*"), reverse=True):
        if path.is_dir():
            os.chmod(path, 0o777)

    os.chmod(WORKSPACE, 0o777)
    return {"ok": True}

def do_tool(body):
    name, args = body["name"], body.get("args", {})
    if name not in TOOLS:
        return {"output": f"error: unknown tool '{name}'", "is_error": True}
    try:
        return {"output": TOOLS[name](args), "is_error": False}
    except Exception as exc:
        return {"output": f"error: {type(exc).__name__}: {exc}", "is_error": True}

def do_verify(body):
    results = []
    scratch = Path(tempfile.mkdtemp(prefix="verify-"))
    try:
        copy = scratch / "project"
        shutil.copytree(WORKSPACE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        for code in body["cases"]:
            try:
                done = subprocess.run([os.environ.get("PYTHON", "python"), "-c", CHILD, code],
                    cwd=copy, capture_output=True, text=True, timeout=CASE_TIMEOUT,
                    env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"})
                marker = "@@RESULT@@"
                results.append(json.loads(done.stdout.rsplit(marker, 1)[1]) if marker in done.stdout
                               else {"ok": False, "exc": "NoResult"})
            except subprocess.TimeoutExpired:
                results.append({"ok": False, "exc": "Timeout"})
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return {"results": results}

def do_state(_body=None):
    files = {str(p.relative_to(WORKSPACE)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in all_files(WORKSPACE)}
    return {"files": files}

ROUTES_POST = {"/reset": do_reset, "/tool": do_tool, "/verify": do_verify}

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == "/health": self._send(200, {"ok": True})
        elif self.path == "/state": self._send(200, do_state())
        else: self._send(404, {"error": "not found"})
    def do_POST(self):
        handler = ROUTES_POST.get(self.path)
        if handler is None: return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, handler(body))
        except Exception as exc:
            self._send(400, {"error": f"{type(exc).__name__}: {exc}"})
    def log_message(self, *args): pass

if __name__ == "__main__":
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    QUEUE.mkdir(parents=True, exist_ok=True)
    os.chmod(QUEUE, 0o700)
    print(f"control service listening on :{PORT}, workspace {WORKSPACE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
