# local/063-red-slide-numbers

Benchmark task for translating OSWorld LibreOffice Impress example `ac9bb6cb-1888-43ab-81e4-a98a547918cd` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: I am preparing a PPT in Libreoffice impress. The slide number is barely visible to me. Please help me change the color of the slide number to red?
- Main output path: `/app/saa-format-guide.pptx`
- Verifier behavior: the exact OSWorld `check_page_number_colors` metric

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `check_page_number_colors` metric.
- The explicit local output contract at `/app/saa-format-guide.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` keeps only the task-critical runtime: `libreoffice-impress`, `tmux`, `asciinema`, the minimal headless X11 packages needed to launch Impress from the terminal, and no extra pip packages because the active verifier path is stdlib-only.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/saa-format-guide.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` keeps only the active OSWorld `check_page_number_colors` path with local path/getter adaptations

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
