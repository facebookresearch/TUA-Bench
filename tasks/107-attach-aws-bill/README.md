# local/107-attach-aws-bill

Benchmark task for translating OSWorld Thunderbird example `d38192b0-17dc-4e1d-99c3-786d0117de77` into a local Harbor task.

## Task Summary

- Attach the AWS bill PDF to the already-open Thunderbird draft message.
- The prompt mirrors the original OS-World wording, with the bill available at both `~/aws-bill.pdf` and `/app/aws-bill.pdf`.
- The required final state is the live draft window with the AWS bill attached.

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Thunderbird example
`d38192b0-17dc-4e1d-99c3-786d0117de77`, which asks:

`Attach the my AWS bill to the email. The bill is stored at ~/aws-bill.pdf. Don't close it or send it. I haven't finish all the contents.`

The local translation preserves the original Thunderbird intent and closely tracks the original evaluator semantics,
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
- `/app/aws-bill.pdf` is fetched at image-build time from `https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/thunderbird/d38192b0-17dc-4e1d-99c3-786d0117de77/invoice0123456789.pdf`.
- The original compose-body HTML is fetched at image-build time from `https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/thunderbird/d38192b0-17dc-4e1d-99c3-786d0117de77/New-month%20AWS%20Bill.html`, and the bill is also exposed at `~/aws-bill.pdf` to match the original prompt.

### Agent Contract

- Harbor runs the agent in `/app` as user `agent`.
- Thunderbird is pre-launched on the shared `:99` display before the agent starts.
- The required final state is the live draft window with `aws-bill.pdf` attached.

### Oracle

- `solution/solve.sh` is the oracle baseline.
- It uses the local Thunderbird helper to satisfy the translated verifier while preserving the seeded compose fields.

### Verifier

The verifier rebuilds Thunderbird's live AT-SPI tree, checks the target compose window for the attachment, includes the upstream attachment-button fallback when attachments are collapsed, and then applies the original OSWorld `check_list` rule.

`tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt` and always persists the
relevant task artifact to `/logs/artifacts`.

## Reward Logic

- `0`: the translated task contract is not satisfied
- `1`: the translated task contract is satisfied
