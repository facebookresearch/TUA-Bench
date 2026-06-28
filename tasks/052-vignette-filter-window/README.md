# local/052-vignette-filter-window

Benchmark task for translating OSWorld GIMP example `a746add2-cab0-4740-ac36-c3769d9bfb46` into a local Harbor task.

## Task Summary

- The agent opens the requested GIMP filter window
- The verifier inspects `~/.config/GIMP/2.10/action-history`
- The task succeeds only if the action history records the expected action

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`a746add2-cab0-4740-ac36-c3769d9bfb46`, which asks:

`Help me open up the Vignette filter window.`

In OSWorld, the setup phase launches:

```json
{
  "type": "launch",
  "parameters": {
    "command": [
      "gimp",
      "/home/user/Desktop/dog_with_background.png"
    ]
  }
}
```

This local task does not pre-launch the GUI application, but the prompt explicitly tells the
agent to use GIMP so the intended tool choice matches the OSWorld task.

## System Design

### Environment

`environment/Dockerfile` installs:

- `gimp`
- `curl`
- `numpy`, `pillow`, `scikit-image`, `pytest`
- lightweight X11 support packages

During the image build it fetches:

- `/app/dog_with_background.png` fetched from the original OSWorld asset URL

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `gimp`

### Oracle

- `solution/solve.sh` is the oracle baseline
- It creates a verifier-passing output for this task with the smallest possible local action

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always copies `~/.config/GIMP/2.10/action-history` into `/logs/artifacts/action-history` when present.

`tests/test_outputs.py` ports the exact OSWorld `check_include_exclude` evaluator logic with only the local action-history path adapted.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
