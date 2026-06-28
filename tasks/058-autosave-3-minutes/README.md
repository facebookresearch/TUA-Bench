# local/058-autosave-3-minutes

Benchmark task for translating OSWorld LibreOffice Impress example `2cd43775-7085-45d8-89fa-9e35c0a915cf` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: Enable auto-save every 3min for me, so that I don't need to hit "ctrl-s" that much.
- Main output path: `/home/agent/.config/libreoffice/4/user/registrymodifications.xcu`
- Verifier behavior: the exact OSWorld `check_auto_saving_time` metric

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `check_auto_saving_time` metric.
- The explicit local output contract at `/home/agent/.config/libreoffice/4/user/registrymodifications.xcu`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` installs `libreoffice-impress`, the Python dependencies needed by the verifier, and lightweight X11 tools so Impress can still be launched from the terminal.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The saved preference file must exist at `/home/agent/.config/libreoffice/4/user/registrymodifications.xcu`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
