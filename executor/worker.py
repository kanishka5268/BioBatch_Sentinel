# Queue worker: network_mode:none; agent snippets run as UID/GID 1000.
import json, os, signal, subprocess, time
from pathlib import Path
QUEUE, WORKSPACE = Path("/queue"), Path("/workspace")
MAX_OUTPUT, DEFAULT_TIMEOUT = 4000, 20

def handle(req_path):
    request = {}
    try:
        request = json.loads(req_path.read_text())
        rid, code = request["id"], request["code"]
        timeout = max(1, min(int(request.get("timeout", DEFAULT_TIMEOUT)), 20))
        proc = subprocess.Popen(["/usr/local/bin/python", "-c", code], cwd=WORKSPACE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True, user=1000, group=1000)
        try:
            out, err = proc.communicate(timeout=timeout)
            output = (out + err).strip() or "(no output)"
            output = f"{output}\\n[exit code {proc.returncode}]"
        except subprocess.TimeoutExpired:
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            proc.communicate()
            output = f"error: the code ran longer than {timeout} seconds and was stopped"
        if len(output) > MAX_OUTPUT: output = output[:MAX_OUTPUT] + "\\n[output cut]"
        tmp, final = QUEUE / f".{rid}.response.tmp", QUEUE / f"{rid}.response.json"
        tmp.write_text(json.dumps({"output": output}))
        tmp.replace(final)
    except Exception as exc:
        rid = request.get("id", req_path.name.split(".")[0])
        (QUEUE / f"{rid}.response.json").write_text(
            json.dumps({"output": f"executor error: {type(exc).__name__}: {exc}"}))
    finally:
        req_path.unlink(missing_ok=True)

def main():
    QUEUE.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    os.chmod(QUEUE, 0o700)
    print("isolated executor ready (network_mode: none)", flush=True)
    while True:
        pending = sorted(QUEUE.glob("*.request.json"))
        if not pending: time.sleep(0.05)
        for path in pending: handle(path)

if __name__ == "__main__": main()
