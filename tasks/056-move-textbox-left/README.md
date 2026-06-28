# local/056-move-textbox-left

Benchmark task for translating OSWorld GIMP example `e2dd0213-26db-4349-abe5-d5667bfd725c` into a local Harbor task.

## Task Summary

- The agent starts with `/app/orange_background.xcf`
- The agent must export `/app/leftside_textbox.png`
- The verifier uses the exact OSWorld `check_textbox_on_leftside`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`e2dd0213-26db-4349-abe5-d5667bfd725c`, which asks:

`Can you assist me in shifting the text box to the left? I keep accidentally selecting the image layer beneath it.`

In OSWorld, the setup phase launches:

```json
{
  "type": "launch",
  "parameters": {
    "command": [
      "gimp",
      "/home/user/Desktop/orange_background.xcf"
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

- `/app/orange_background.xcf` fetched from the original OSWorld asset URL

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

`tests/test.sh` always copies `/app/leftside_textbox.png` into `/logs/artifacts/leftside_textbox.png` when present.

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example: `check_textbox_on_leftside`.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
