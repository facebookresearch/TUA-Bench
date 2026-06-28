# local/031-profile-name-thomas

Benchmark task for translating OSWorld Chrome example `2ae9ba84-3a0d-4d4c-8338-3a1478dc5fe3` into a local Harbor task.

## Task Summary

- The agent changes the Chrome profile name to `Thomas`
- The verifier inspects `~/.config/google-chrome/Default/Preferences`
- The task succeeds only if the exact OSWorld getter returns `Thomas` for `profile.name`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`2ae9ba84-3a0d-4d4c-8338-3a1478dc5fe3`, which asks:

`Lately I have changed my English name to Thomas. I want to update my username. Could you help me change the username in chrome profiles to Thomas?`

In OSWorld, the setup phase launches:

```json
[
  {
    "type": "launch",
    "parameters": {
      "command": [
        "google-chrome",
        "--remote-debugging-port=1337"
      ]
    }
  },
  {
    "type": "launch",
    "parameters": {
      "command": [
        "socat",
        "tcp-listen:9222,fork",
        "tcp:localhost:1337"
      ]
    }
  }
]
```

The OSWorld evaluator then runs this postconfig before checking the result:

```json
[
  {
    "type": "launch",
    "parameters": {
      "command": [
        "pkill",
        "chrome"
      ]
    }
  },
  {
    "type": "launch",
    "parameters": {
      "command": [
        "google-chrome",
        "--remote-debugging-port=1337"
      ]
    }
  },
  {
    "type": "sleep",
    "parameters": {
      "seconds": 3
    }
  }
]
```

This local task does not preserve the remote-debugging bridge or the relaunch step because the
ported verifier reads the same saved profile preference directly from disk after Chrome exits.
The benchmark meaning is preserved by keeping the same Chrome profile path and the exact
`profile_name` getter plus `exact_match` metric.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- a `google-chrome` wrapper that launches Chromium under `xvfb-run`
- `pytest`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages

The wrapper stores the browser profile under `~/.config/google-chrome`, so the local profile
path matches the OSWorld getter on both `amd64` and `arm64`. It also adds Chromium's
`--no-sandbox` flag because the browser otherwise aborts under this containerized Harbor task
runtime before the agent can change the setting.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`

### Oracle

- `solution/solve.sh` is the oracle baseline
- It writes the smallest valid Chrome preferences file that sets `profile.name` to `Thomas`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always copies `~/.config/google-chrome/Default/Preferences` into
`/logs/artifacts/Preferences` when present.

`tests/test_outputs.py` ports the exact OSWorld getter `get_profile_name` from
`desktop_env/evaluators/getters/chrome.py` and the exact `exact_match` metric from
`desktop_env/evaluators/metrics/general.py`, with only the local path and env object removed.

## Output Contract

- Saved Chrome preferences live at `~/.config/google-chrome/Default/Preferences`
- The verifier reads `profile.name`
- The expected final value is exactly `Thomas`

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
