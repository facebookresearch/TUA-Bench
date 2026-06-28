# local/106-create-charles-ssh-user

Benchmark task for translating OSWorld OS example `5812b315-e7bd-4265-b51f-863c02174c28` into a local Harbor task.

## Task Summary

- Local task description: Create the requested local user account for charles with the specified password and home directory.
- Output contract: No extra output file is required. The verifier checks the created account and home directory directly.
- Verifier behavior: A task-specific local verifier aligned with the original OSWorld `check_include_exclude` evaluator over the original shell login and passwd-state check.

## What Was Preserved

- The original account-creation intent, password value, and `/home/test1` home-directory contract.
- The exact OSWorld shell check that validates password login, passwd home directory, and write permission.

## What Was Simplified

- The local translation does not require a live `sshd` because the original evaluator only checked local account state via `su`.
- Passwordless `sudo` is available to the `agent` user so the system-account change remains feasible inside the container.

## Environment

- The image prepares `/home/test1` and downloads the original `check_password.sh` expect script.
- The `agent` user can run administrative commands with `sudo` inside the task container.

## Oracle

- `solution/solve.sh` is the oracle baseline.
- It applies the smallest local action that satisfies the translated task contract.

## Verifier

- `tests/test.sh` writes a binary reward to `/logs/verifier/reward.txt`.
- `tests/test.sh` always persists the relevant task artifact or state snapshot into `/logs/artifacts/`.
- `tests/test_outputs.py` keeps the exact OSWorld metric behavior for this task wherever the original evaluator is directly portable.

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
