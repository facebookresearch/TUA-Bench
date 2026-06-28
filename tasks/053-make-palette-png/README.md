# local/053-make-palette-png

Benchmark task for translating OSWorld GIMP example `06ca5602-62ca-47f6-ad4f-da151cde54cc` into a local Harbor task.

This task evaluates whether an agent can use GIMP to convert a provided image into a palette-based PNG while preserving its visual structure.

## Task summary

- The agent starts with `/app/computer.png`
- The agent must export `/app/palette_computer.png`
- The output must be a palette-based PNG
- The image content should remain visually the same as the original

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`06ca5602-62ca-47f6-ad4f-da151cde54cc`, which asks:

`Could you help me set the image to Palette-Based?`

In OSWorld, the setup phase launches:

```json
{
  "type": "launch",
  "parameters": {
    "command": [
      "gimp",
      "/home/user/Desktop/computer.png"
    ]
  }
}
```

This local task does not pre-launch the GUI application, but the prompt explicitly tells the
agent to use GIMP so the intended tool choice matches the OSWorld task.

## System design

### Environment

`environment/Dockerfile` installs:

- `gimp`
- `curl`
- `numpy`, `pillow`, `scikit-image`, `pytest`
- lightweight X11 support packages

During the image build it fetches the source image from the original OSWorld asset URL
and places it at `/app/computer.png`.

### Agent contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `gimp`
- The expected final output is `/app/palette_computer.png`

### Oracle

- `solution/solve.sh` is the oracle baseline
- It converts `/app/computer.png` into a palette-based PNG and writes `/app/palette_computer.png`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output passes the exact OSWorld `check_palette_and_structure_sim` evaluator
- `0`: otherwise

The PNG is always copied into `/logs/artifacts/palette_computer.png` on exit.

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example:

- `safe_open_image_with_retry`
- `structure_check_by_ssim`
- `check_palette_and_structure_sim`

The only Harbor-specific difference is that this task does not replicate the OSWorld
`pyautogui` export post-action. The agent is expected to write the final PNG directly to
`/app/palette_computer.png`.

## Reward logic

- `0`: output does not satisfy `check_palette_and_structure_sim`
- `1`: output satisfies `check_palette_and_structure_sim`

## Important files

- `instruction.md`: task prompt and output contract
- `environment/Dockerfile`: task runtime image
- OSWorld source asset URL: fetched by `environment/Dockerfile` during image build
- `task.toml`: Harbor task config
- `solution/solve.sh`: oracle implementation
- `tests/test.sh`: verifier entrypoint and reward writing
- `tests/test_outputs.py`: exact OSWorld palette-and-structure evaluator port

This task has no runtime network dependency after the image build completes.
