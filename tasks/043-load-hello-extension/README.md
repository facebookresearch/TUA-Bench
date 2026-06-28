# local/043-load-hello-extension

Benchmark task for translating OSWorld Chrome example `6766f2b8-8a72-417f-a9e5-56fcaa735837`
into a local Harbor task.

## Task Summary

- The agent unzips `~/Desktop/helloExtension.zip` so the unpacked extension directory is exactly
  `~/Desktop/helloExtension`
- The agent uses Chrome's built-in Extensions page to load `~/Desktop/helloExtension` itself, not
  a nested extracted subdirectory
- The verifier inspects `~/.config/google-chrome/Default/Preferences`
- The task succeeds only if the exact OSWorld getter returns a list containing
  `/home/agent/Desktop/helloExtension`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`6766f2b8-8a72-417f-a9e5-56fcaa735837`, which asks:

`Could you help me unzip the downloaded extension file from /home/user/Desktop/ to /home/user/Desktop/ and configure it in Chrome's extensions?`

In OSWorld, the setup phase:

- downloads `helloExtension.zip` to `/home/user/Desktop/helloExtension.zip`
- runs `unzip /home/user/Desktop/helloExtension.zip -d /home/user/Desktop/` and removes the zip
- launches `google-chrome --remote-debugging-port=1337`
- launches the `socat` bridge from `9222` to `1337`

This local task preserves the same Chrome-profile output semantics by reusing the exact OSWorld
getter `get_find_unpacked_extension_path` and metric `is_in_list`. It intentionally simplifies away
the remote-debugging bridge because the evaluator only reads the saved Chrome `Preferences` file
after the browser exits. It also keeps the downloaded zip on `~/Desktop` so the local prompt still
matches the user-visible unzip step from the original instruction.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- a `google-chrome` wrapper backed by Chromium on a fixed Xvfb display
- `tmux` and `asciinema` for terminal session support
- `unzip`, because the prompt still requires unpacking the downloaded archive
- `pytest`

During image build, the task downloads the OSWorld source archive to
`/home/agent/Desktop/helloExtension.zip`. At runtime, the container entrypoint starts a shared
`DISPLAY=:99` X server and opens Chrome directly to `chrome://extensions/`.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The downloaded archive is at `~/Desktop/helloExtension.zip`
- The expected unpacked directory is `~/Desktop/helloExtension`
- If the zip extracts into `~/Desktop/helloExtension/helloExtension`, the agent should flatten it
  so `manifest.json` ends up directly under `~/Desktop/helloExtension`
- Chrome should be closed at the end so the saved profile is written to disk

### Oracle

- `solution/solve.sh` is the oracle baseline
- It unzips the downloaded archive to `~/Desktop/helloExtension`
- It writes the smallest valid `Preferences` file whose `extensions.settings.*.path` list contains
  `/home/agent/Desktop/helloExtension`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always copies `~/.config/google-chrome/Default/Preferences` into
`/logs/artifacts/Preferences` when present.

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example:

- `get_find_unpacked_extension_path` from `desktop_env/evaluators/getters/chrome.py`
- `is_in_list` from `desktop_env/evaluators/metrics/general.py`

The only Harbor-specific differences are replacing the OSWorld env-controller file read with a
direct local path and exposing `PREFERENCES_PATH` plus `EXPECTED_EXTENSION_PATH` as overrides for
evaluator sanity checks outside the task container.

## Reward Logic

- `0`: the task output does not satisfy OSWorld `is_in_list`
- `1`: the task output satisfies OSWorld `is_in_list`
