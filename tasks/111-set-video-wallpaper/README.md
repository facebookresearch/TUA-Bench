# local/111-set-video-wallpaper

Benchmark task for translating OSWorld VLC example `efcf0d81-0835-4880-b2fd-d866e8bc2294` into a local Harbor task.

## Task Summary

- The agent starts with `~/Desktop/Interstellar Movie - Official Trailer.mp4`
- Output contract: No extra output file is required. Leave the final wallpaper set when you finish.
- Verifier behavior: The exact OSWorld `compare_images` metric over the persisted wallpaper image and the cloud gold reference.

## OSWorld Source

- Example id: `efcf0d81-0835-4880-b2fd-d866e8bc2294`
- Original instruction: `Make this part of the video my computer's background picture`

## What Was Preserved

- The original VLC wallpaper-setting intent and the same target video moment.
- The exact OSWorld `compare_images` metric semantics, including the original base-score option.

## What Was Simplified

- The live VM wallpaper getter is adapted to a persisted local wallpaper artifact.
- The translated task keeps the same visual target while avoiding desktop-specific wallpaper APIs.

## Environment

- The task image installs `vlc`, `ffmpeg`, and a terminal-first `vlc` or `cvlc` shim.
- The image creates `/home/agent/Desktop`, `/home/agent/Videos`, and VLC config and state directories ahead of time.
- The original OSWorld input assets are fetched during image build and placed at `~/Desktop/Interstellar Movie - Official Trailer.mp4`.
- The local VLC shim persists session state under `~/.local/state/tua-vlc` so the exact evaluator getters can be reproduced locally.

## Oracle

- `solution/solve.sh` is the oracle baseline.
- It applies the smallest local action that satisfies the translated task contract.

## Verifier

- `tests/test.sh` writes the task reward to `/logs/verifier/reward.txt`.
- `tests/test.sh` always copies the relevant task artifact or state snapshot into `/logs/artifacts/`.
- `tests/test_outputs.py` ports the exact OSWorld VLC metric bodies wherever the original evaluator is directly reusable.

## Reward Logic

- `tests/test.sh` writes the exact OSWorld `compare_images` score in the range `[0, 1]`.
- The original `reference_base_result` option is preserved, so scores below the base threshold collapse to `0`.

## Important Files

- `instruction.md`: task prompt and output contract
- `environment/Dockerfile`: task runtime image
- `environment/vlcshim.py`: terminal-first VLC shim used by the local environment
- `task.toml`: Harbor task config
- `solution/solve.sh`: oracle implementation
- `tests/test.sh`: verifier entrypoint and reward writing
- `tests/test_outputs.py`: exact VLC evaluator port and local getter adaptations

## Network dependency

The oracle and verifier both depend on the runtime gold reference at:

`https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294/interstellar.png`
