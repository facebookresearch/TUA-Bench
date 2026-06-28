# local/057-set-undo-steps-100

Benchmark task for translating OSWorld GIMP example `7b7617bd-57cc-468e-9c91-40c4ec2bcb3d` into a local Harbor task.

## Task Summary

- The agent changes the requested GIMP setting
- The verifier inspects `~/.config/GIMP/2.10/gimprc`
- The task succeeds only if the config file matches the exact OSWorld rule

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`7b7617bd-57cc-468e-9c91-40c4ec2bcb3d`, which asks:

`Set the minimum number of undo steps to 100.`

In OSWorld, the setup phase launches:

```json
{
  "type": "launch",
  "parameters": {
    "command": [
      "gimp"
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

- no input files are fetched for this task

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

`tests/test.sh` always copies `~/.config/GIMP/2.10/gimprc` into `/logs/artifacts/gimprc` when present.

`tests/test_outputs.py` ports the exact OSWorld `check_config_status` evaluator logic with only the local config path adapted.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
