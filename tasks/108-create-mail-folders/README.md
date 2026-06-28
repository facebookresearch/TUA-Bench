# local/108-create-mail-folders

Benchmark task for translating OSWorld Thunderbird example `a10b69e1-6034-4a2b-93e1-571d45194f75` into a local Harbor task.

## Task Summary

- Create COMPANY and UNIVERSITY local folders in Thunderbird.
- The prompt explicitly requires Thunderbird.
- The required saved state lives under the translated local output path.

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Thunderbird example
`a10b69e1-6034-4a2b-93e1-571d45194f75`, which asks:

`Create two local folders in Thunderbird for me: COMPANY and UNIVERSITY.`

The local translation preserves the original Thunderbird intent and exact evaluator semantics,
while adapting the execution model from OSWorld's GUI harness to this repo's Harbor task layout.

## System Design

### Environment

`environment/Dockerfile` installs Thunderbird plus the minimum GUI and verifier dependencies
needed for a local Harbor translation:

- `thunderbird`
- AT-SPI and X11 packages so Thunderbird can run on the shared virtual display
- `pytest`, `lxml`, and `cssselect` for the translated verifier
- `tmux` and `asciinema` for terminal session support

- The Thunderbird profile archive is fetched at image-build time from `https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/thunderbird/dd84e895-72fd-4023-a336-97689ded257c/thunderbird-profile.tar.gz`.

### Agent Contract

- Harbor runs the agent in `/app` as user `agent`.
- Thunderbird is pre-launched on the shared `:99` display before the agent starts.
- The required saved state lives under the translated local output path.

### Oracle

- `solution/solve.sh` is the oracle baseline.
- It makes the smallest local state change needed to satisfy the translated verifier.

### Verifier

The verifier applies the exact OSWorld `check_list` rules to the translated local output path.

`tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt` and always persists the
relevant task artifact to `/logs/artifacts`.

## Reward Logic

- `0`: the translated task contract is not satisfied
- `1`: the translated task contract is satisfied
