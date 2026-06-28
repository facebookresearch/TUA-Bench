# local/113-add-folders-workspace

Benchmark task for translating OSWorld VS Code example `6ed0a554-cbee-4b44-84ea-fd6c042f4fe1` into a local Harbor task.

## Task Summary

- Local task description: Add `data1` and `data2` to the current VS Code workspace.
- Output contract: The verifier checks the updated workspace file at `/app/project.code-workspace` directly.
- Verifier behavior: A semantic workspace-folder check over the workspace JSON file.

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld VS Code example `6ed0a554-cbee-4b44-84ea-fd6c042f4fe1`, which asks:

`Please help me add folder "/home/user/data1" and folder "/home/user/data2" to the current workspace.`

## What Was Preserved

- The original VS Code workspace-edit intent and the expected workspace-folder list.
- The original success condition that the requested folders must persist in the workspace file.

## What Was Simplified

- The local task keeps VS Code explicit but evaluates the saved workspace file directly instead of replaying GUI actions.
- The terminal-oriented `code` shim supports opening a workspace file and updating it through `code --add`.

## Environment

- The image provides a lightweight terminal-oriented `code` shim that persists VS Code extension, settings, keybinding, and current-target state at the usual VS Code paths.
- The workspace file is prepared at `/app/project.code-workspace` before the agent starts.
- The task starts with `/app/project.code-workspace` as the current VS Code workspace.

## Oracle

- `solution/solve.sh` is the oracle baseline.
- It applies the smallest local action that satisfies the translated task contract.

## Verifier

- `tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt`.
- `tests/test.sh` always persists the relevant task artifact or VS Code state snapshot into `/logs/artifacts/`.
- `tests/test_outputs.py` checks the workspace folder list after resolving relative entries against `/app/project.code-workspace`, so both `data1` and `/app/data1` satisfy the same folder requirement.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
