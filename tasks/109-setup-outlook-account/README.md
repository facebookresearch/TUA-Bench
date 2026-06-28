# local/109-setup-outlook-account

Benchmark task for translating OSWorld Thunderbird example `15c3b339-88f7-4a86-ab16-e71c58dcb01e` into a local Harbor task.

## Task Summary

- Fill the Outlook account setup page inside Thunderbird and leave it open.
- The prompt explicitly requires Thunderbird.
- The required final state is the live Thunderbird window state described by the prompt.

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Thunderbird example
`15c3b339-88f7-4a86-ab16-e71c58dcb01e`, which asks:

`Help me access my outlook account with address "anonym-x2024@outlook.com" and password 'password' (without ') in Thunderbird. Just fill in the information and stay on that page. I will check it manually later.`

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

- The Thunderbird profile archive is fetched at image-build time from `https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/thunderbird/15c3b339-88f7-4a86-ab16-e71c58dcb01e/thunderbird-profile-blank.tar.gz`.

### Agent Contract

- Harbor runs the agent in `/app` as user `agent`.
- Thunderbird is pre-launched on the shared `:99` display before the agent starts.
- The required final state is the live Thunderbird window state described by the prompt.

### Oracle

- `solution/solve.sh` is the oracle baseline.
- It makes the smallest local state change needed to satisfy the translated verifier.

### Verifier

The verifier rebuilds the live AT-SPI accessibility tree locally and applies the exact OSWorld `check_accessibility_tree` rules.

`tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt` and always persists the
relevant task artifact to `/logs/artifacts`.

## Reward Logic

- `0`: the translated task contract is not satisfied
- `1`: the translated task contract is satisfied
