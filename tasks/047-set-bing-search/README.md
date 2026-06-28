# local/047-set-bing-search

Benchmark task for translating OSWorld Chrome example
`bb5e4c0d-f964-439c-97b6-bdb9747de3f4` into a local Harbor task.

## Task Summary

- The agent uses Chrome to make Bing the default search engine
- The task image starts from a clean Chrome profile
- The verifier inspects `~/.config/google-chrome/Default/Preferences`
- The task succeeds only if the exact OSWorld getter returns a value accepted by the exact
  OSWorld `match_in_list` metric: `Microsoft Bing` or `Bing`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`bb5e4c0d-f964-439c-97b6-bdb9747de3f4`, which asks:

`Can you make Bing the main search engine when I look stuff up on the internet?`

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

This local task does not preserve the remote-debugging bridge or the relaunch step. Instead, it
preserves the same saved-profile evaluation contract and checks the exact saved Chrome
preferences directly after Chrome exits.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- a `google-chrome` wrapper that launches Chromium under `xvfb-run`
- `pytest`
- `tmux` and `asciinema` for terminal session support
- lightweight X11 support packages

The image pre-seeds `~/.config/google-chrome/Default/Preferences` with `{}` so the unsolved
state is deterministic and still matches the OSWorld getter fallback to `Google`.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- Chrome's default search engine should be changed to `Bing`
- Chrome should be quit so the updated profile is written to disk

### Oracle

- `solution/solve.sh` is the oracle baseline
- It writes the smallest valid Chrome preferences file that makes the exact OSWorld getter return
  `Bing`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always copies `~/.config/google-chrome/Default/Preferences` into
`/logs/artifacts/Preferences` when present.

`tests/test_outputs.py` ports the exact OSWorld getter `get_default_search_engine` from
`desktop_env/evaluators/getters/chrome.py` and the exact `match_in_list` metric from
`desktop_env/evaluators/metrics/general.py`, with only the local path and env object removed.

The important OSWorld quirks are preserved exactly:

- when the expected search-engine key is missing or unreadable, the getter falls back to
  `Google`
- the accepted solved values remain the OSWorld list `["Microsoft Bing", "Bing"]`

## Output Contract

- Saved Chrome preferences live at `~/.config/google-chrome/Default/Preferences`
- The verifier reads the `default_search_engine` getter result from that file
- The expected final getter result is one of `Microsoft Bing` or `Bing`

## Reward Logic

- `0`: the task output does not satisfy the verifier
- `1`: the task output satisfies the verifier
