# local/055-resize-dog-layer

Benchmark task for translating OSWorld GIMP example `d16c99dc-2a1e-46f2-b350-d97c86c85c15` into a local Harbor task.

## Task Summary

- The agent starts with `/app/dog_with_background.png, /app/dog_with_background_two_layers.xcf`
- The agent must export `/app/resized.png`
- The verifier uses the exact OSWorld `check_image_size` and `check_structure_sim_resized` evaluators

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`d16c99dc-2a1e-46f2-b350-d97c86c85c15`, which asks:

`Could you assist me with resizing the dog layer of an image? I need to adjust the height to 512 pixels while maintaining the original aspect ratio?`

In OSWorld, the setup phase launches:

```json
{
  "type": "launch",
  "parameters": {
    "command": [
      "gimp",
      "/home/user/Desktop/dog_with_background_two_layers.xcf"
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
- `/app/dog_with_background_two_layers.xcf` fetched from the original OSWorld asset URL

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

`tests/test.sh` always copies `/app/resized.png` into `/logs/artifacts/resized.png` when present.

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example: `check_image_size, check_structure_sim_resized`.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
