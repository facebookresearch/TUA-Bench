# local/067-align-slide-textboxes

Benchmark task for translating OSWorld LibreOffice Impress example `05dd4c1d-c489-4c85-8389-a7836c4f0567` into a local Harbor task.

## Task Summary

- Intended application: `LibreOffice Impress`
- Local task description: Align the text of the first textbox on slide 3 to the right, on slide 4 to the center, and on slide 5 to the left. Ensure that the alignment is applied correctly to each respective slide.
- Main output path: `/app/38_1.pptx`
- Verifier behavior: the exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination

## What Was Preserved

- The original LibreOffice Impress user intent and application constraint.
- The exact OSWorld `compare_pptx_files` + `compare_pptx_files` metric combination.
- The explicit local output contract at `/app/38_1.pptx`.

## What Was Simplified

- The original OSWorld Desktop or Downloads paths are translated to `/app/...` where practical.
- The GUI save-hotkey postconfig is simplified to an explicit local file contract.

## Environment

`environment/Dockerfile` keeps `libreoffice-impress`, the headless X runtime needed to launch it from the terminal, and only the active `compare_pptx_files` verifier dependency set for this task.

The verifier still carries broader upstream helper branches, but their extra media or image dependencies are loaded lazily so this task does not pay for them at image-build time.

During the image build it fetches the source task assets directly into `/app`.

## Output Contract

- The presentation must be saved in place at `/app/38_1.pptx`.

## Oracle

- `solution/solve.sh` is the oracle baseline
- It produces a verifier-passing result with the smallest local action that preserves the translated contract

## Verifier

- `tests/test.sh` writes the scalar reward to `/logs/verifier/reward.txt`
- `tests/test.sh` always copies the produced task artifact or inspection sidecar into `/logs/artifacts/`
- `tests/test_outputs.py` ports the exact OSWorld Impress evaluator helpers with only local path or getter adaptations

## Reward Logic

- The reward is the exact combined OSWorld metric value in `[0, 1]`.
