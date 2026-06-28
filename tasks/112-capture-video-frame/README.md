# local/112-capture-video-frame

Benchmark task for translating OSWorld VLC example `fba2c100-79e8-42df-ae74-b592418d54f4` into a local Harbor task.

## Task Summary

- The agent starts with `~/Desktop/Interstellar Movie - Official Trailer.mp4`
- The expected final output is `~/Desktop/interstellar.png`
- Verifier behavior: The exact OSWorld `compare_images` metric over the final output artifact and the cloud gold reference.

## OSWorld Source

- Example id: `fba2c100-79e8-42df-ae74-b592418d54f4`
- Original instruction: `Snap a photo of the current video scene, save it as 'interstellar.png', and put it on the Desktop, please.`

## What Was Preserved

- The original VLC media-editing intent and final output path.
- The exact OSWorld `compare_images` metric semantics.

## What Was Simplified

- GUI-only export steps are reduced to the final output artifact path that the exact evaluator scores.
- A headless `vlc` or `cvlc` workflow is acceptable in the terminal-first Harbor environment.

## Environment

- The task image installs `vlc`, `ffmpeg`, and a terminal-first `vlc` or `cvlc` shim.
- The image creates `/home/agent/Desktop`, `/home/agent/Videos`, and VLC config and state directories ahead of time.
- The original OSWorld input assets are fetched during image build and placed at `~/Desktop/Interstellar Movie - Official Trailer.mp4`.

## Oracle

- `solution/solve.sh` is the oracle baseline.
- It applies the smallest local action that satisfies the translated task contract.

## Verifier

- `tests/test.sh` writes the task reward to `/logs/verifier/reward.txt`.
- `tests/test.sh` always copies the relevant task artifact or state snapshot into `/logs/artifacts/`.
- `tests/test_outputs.py` ports the exact OSWorld VLC metric bodies wherever the original evaluator is directly reusable.

## Reward Logic

- `tests/test.sh` writes the exact OSWorld `compare_images` score in the range `[0, 1]`.
- No custom thresholding or local partial-credit logic is added beyond the original metric behavior.

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

`https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vlc/fba2c100-79e8-42df-ae74-b592418d54f4/interstellar.png`
