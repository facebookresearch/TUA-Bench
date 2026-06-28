# local/115-remove-explorer-find-key

Benchmark task for translating OSWorld VS Code example `ea98c5d7-3cf9-4f9b-8ad3-366b58e0fcae` into a local Harbor task.

## Task Summary

- Local task description: Remove the `Ctrl+F` Tree View Find keybinding in VS Code.
- Output contract: No extra output file is required. The verifier reads VS Code's persisted `keybindings.json` directly.
- Verifier behavior: The exact OSWorld `check_json_keybindings` metric over VS Code's `keybindings.json`.

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld VS Code example `ea98c5d7-3cf9-4f9b-8ad3-366b58e0fcae`, which asks:

`Please help me remove the shortcut "ctrl+f" for Tree view Find (Explorer search) in VS Code Explorer view to avoid shortcut conflict.`

## What Was Preserved

- The original VS Code keybinding intent and the exact expected binding object.
- The original success condition that the binding must be saved in VS Code's keybindings file.

## What Was Simplified

- The local task keeps VS Code explicit but evaluates the saved keybindings file directly instead of replaying the keyboard-shortcuts GUI.
- The verifier uses the same JSON-list semantics as OSWorld's `check_json_keybindings` helper.

## Environment

- The image provides a lightweight terminal-oriented `code` shim that persists VS Code extension, settings, keybinding, and current-target state at the usual VS Code paths.
- VS Code keybindings persist at `~/.config/Code/User/keybindings.json`.

## Oracle

- `solution/solve.sh` is the oracle baseline.
- It applies the smallest local action that satisfies the translated task contract.

## Verifier

- `tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt`.
- `tests/test.sh` always persists the relevant task artifact or VS Code state snapshot into `/logs/artifacts/`.
- `tests/test_outputs.py` ports the exact OSWorld VS Code metric helper for this task wherever the original evaluator is directly portable.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
