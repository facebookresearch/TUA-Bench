# local/049-remove-dog-background

Benchmark task for translating OSWorld GIMP example `2a729ded-3296-423d-aec4-7dd55ed5fbb3` into a local Harbor task.

This task evaluates whether an agent can use GIMP to remove the background from a provided dog image and export a transparent PNG.

## Task summary

- The agent starts with `/app/dog_with_background.png`
- The agent must export `/app/dog_without_background.png`
- The original `1578x948` canvas must be preserved
- The dog should remain intact while the surrounding background becomes transparent

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld GIMP example
`2a729ded-3296-423d-aec4-7dd55ed5fbb3`, which asks:

`Could you use GIMP to make the background of this image transparent for me?`

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

## System design

### Environment

`environment/Dockerfile` installs:

- `gimp`
- `curl`
- `numpy`, `pillow`, `scikit-image`, `pytest`
- lightweight X11 support packages

During the image build it fetches the source image from the original OSWorld asset URL
and places it at `/app/dog_with_background.png`.

### Agent contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `gimp`
- The expected final output is `/app/dog_without_background.png`

### Oracle

- `solution/solve.sh` is the oracle baseline
- It downloads the gold cutout at runtime and copies it into `/app/dog_without_background.png`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output passes the exact OSWorld `check_structure_sim` evaluator
- `0`: otherwise

The PNG is always copied into `/logs/artifacts/dog_without_background.png` on exit.

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example:

- `check_structure_sim`
- `structure_check_by_ssim`

The only Harbor-specific difference is that this task does not replicate the OSWorld
`pyautogui` export postconfig. The agent is expected to write the final PNG directly to
`/app/dog_without_background.png`.

## Reward logic

- `0`: output does not satisfy `check_structure_sim`
- `1`: output satisfies `check_structure_sim`

## Important files

- `instruction.md`: task prompt and output contract
- `environment/Dockerfile`: task runtime image
- OSWorld source asset URL: fetched by `environment/Dockerfile` during image build
- `task.toml`: Harbor task config
- `solution/solve.sh`: oracle implementation
- `tests/test.sh`: verifier entrypoint and reward writing
- `tests/test_outputs.py`: exact OSWorld structure-sim evaluator port

The oracle and verifier both fetch the gold reference cutout at runtime from:

`https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/dog_cutout_gold.png`

Because the gold reference is no longer bundled locally, the oracle and verifier both depend on network access to this URL.
