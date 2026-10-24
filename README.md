
# BioBatch Sentinel

**A tool-using RL environment for synthetic bio-monitoring code tasks.**

BioBatch Sentinel evaluates whether an AI agent can inspect a Python project, modify code, validate its changes, and complete tasks successfully. It provides deterministic task setup, programmatic verification, reference-solution and no-op baselines, reward scoring, structured telemetry, and Docker-based execution.

The tasks are synthetic software exercises inspired by sensor and process-monitoring concepts. They are not intended for real-world process control.

## Demo Task

### `sensor_calibration` — Easy

Implement `sensors.calibrate_reading(raw, offset, scale)` by subtracting the offset from the raw reading before multiplying by the scale.

**Expected behavior:**

```python
calibrated = (raw - offset) * scale
```

## Task Suite

| Task | Difficulty | Objective |
|---|---|---|
| `sensor_calibration` | Easy | Subtract offset, then multiply by scale |
| `ph_alarm` | Easy | Apply strict out-of-range boundary checks |
| `do_trend` | Medium | Average valid dissolved-oxygen values, ignoring `None` |
| `contamination_signal` | Medium | Apply an inclusive threshold |
| `recovery_action` | Medium | Apply ordered action-priority rules |

## Architecture

BioBatch Sentinel consists of the following components:

- **Harness:** Coordinates model calls, episode execution, tool actions, verification, rewards, and logs.
- **Sandbox Control Service:** Manages task resets, workspace operations, and tool routing.
- **Executor Worker:** Executes submitted Python snippets in a separate container configured with `network_mode: none`.
- **Verifier:** Uses programmatic checks and regression tests rather than an LLM judge.
- **Telemetry:** Records model inputs and outputs, parsed actions, tool results, errors, state hashes, rewards, and episode termination.

The executor's network restriction is a defense-in-depth measure, not a guarantee of perfect security isolation.

## Getting Started

### Prerequisites

- Docker Desktop with WSL2 on Windows, or Docker on Linux/macOS
- Docker Compose v2
- Model configuration and credentials supplied for the hackathon
- Git (optional, for version control)

### 1. Configure the Environment

Create a local configuration file from the example:

```bash
cp .env.example .env
```

On Windows Command Prompt, use:

```cmd
copy .env.example .env
```

Edit `.env` with the model settings supplied for the hackathon.

**Security note:** Keep real credentials in `.env`. Never commit API keys or other secrets to version control or include them in submission archives.

### 2. Build and Launch the Environment

Run the required command from the project root:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from harness
```

The harness runs baseline checks before model evaluation. If a baseline fails, the model run should not proceed.

## Testing

### Run Baseline Checks

Validate the reference solutions and no-op baselines across the complete task suite:

```bash
docker compose run --build --rm -e MODE=baselines harness
```

### Run the Model Across All Tasks

```bash
docker compose run --build --rm -e MODE=all harness
```

### Test the Demo Task with a No-Op Agent

```bash
docker compose run --build --rm -e MODEL=mock/idle harness
```

Inspect the generated `logs/` directories for baseline results, episode telemetry, errors, and evaluation summaries.

## Baselines and Reward Scoring

Each task includes a reference solution and a no-op baseline.

The baseline gate requires:

| Baseline | Required Score |
|---|---:|
| Reference solution (oracle) | At least `0.95` |
| No-op baseline | At most `0.05` |

### Recorded Results

The recorded baseline gate passed for all five tasks.

| Metric | Recorded Result |
|---|---:|
| Reference solution scores | `1.00` on all five tasks |
| No-op baseline scores | `0.00` on all five tasks |
| Full model run | All five tasks solved |
| Full model mean reward | `1.00` |
| Separate no-op model run | Terminated unsuccessfully with reward `0.00` |

These are recorded test results, not a guarantee that every model or future run will achieve the same performance.

## Submission Evidence

The reference-material package contains the following artifacts:

- `baseline-results/gate.json` — Recorded baseline gate results
- `test-run-logs/` — Test execution logs
- `sample-trajectories/` — Sample agent trajectories
- `design-doc.pdf` — Design documentation
- `deck.pdf` — Project presentation

## Configuration and Security

- `.env.example` contains configuration placeholders.
- `.env` contains local configuration and must not be committed.
- API keys and other credentials must not appear in source code, logs, or submission archives.
- The verifier and reward logic must remain inaccessible to the agent's code execution.
- The executor is configured without network access; verify the Docker configuration before submission.
- The executor's network restriction is a defense-in-depth measure and does not guarantee complete isolation.

## Project Structure

```text
.
├── Dockerfile.harness
├── Dockerfile.sandbox
├── Dockerfile.executor
├── docker-compose.yml
├── executor/
├── harness/
├── sandbox/
├── inputs/
├── baseline-results/
├── test-run-logs/
├── sample-trajectories/
├── design-doc.pdf
├── deck.pdf
└── README.md
```

## Overview

BioBatch Sentinel is built on the hackathon's RL environment template and extends it with a custom five-task suite and a separate network-restricted executor.

The project provides a reproducible environment for evaluating whether AI agents can use tools to inspect code, implement solutions, validate behavior, and complete synthetic software tasks under programmatic verification.
