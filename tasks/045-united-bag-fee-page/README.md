# local/045-united-bag-fee-page

Benchmark task for translating OSWorld Chrome example `c1fa57f3-c3db-4596-8f09-020701085416`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on United Airlines to open the checked bag fee calculator
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.united.com/en/us`
- The verifier succeeds only if the active Chrome tab resolves to a URL matching the exact
  OSWorld regex pattern `united\.com/en/us/checked-bag-fee-calculator(/.*)?`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`c1fa57f3-c3db-4596-8f09-020701085416`, which asks:

`Open the baggage fee calculator in United Airlines website.`

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
  },
  {
    "type": "chrome_open_tabs",
    "parameters": {
      "urls_to_open": [
        "https://www.united.com/en/us"
      ]
    }
  },
  {
    "type": "activate_window",
    "parameters": {
      "window_name": "Google Chrome"
    }
  }
]
```

This local task does not preserve the OSWorld accessibility-tree HTTP bridge. Instead, the
task container starts a fixed Xvfb display and a live Chrome instance whose active tab is
prepared to match the OSWorld starting state.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `tmux` and `asciinema` for terminal session support
- `playwright` and `pytest`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.united.com/en/us` in a single
  live Chrome tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The existing Chrome tab should be used to open United Airlines' checked bag fee calculator
- Chrome should be left open on the final United Airlines calculator page so the verifier can
  inspect the active tab

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser directly to
  `https://www.united.com/en/us/checked-bag-fee-calculator`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/active_tab_info.json`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example:

- `is_expected_url_pattern_match` from `desktop_env/evaluators/metrics/chrome.py`
- `get_active_tab_info` from `desktop_env/evaluators/getters/chrome.py`, with only the
  accessibility-tree read adapted to local shared-display address-bar capture

The final output contract is the live active Chrome tab URL on United Airlines. This task does
not produce an output file.

## Reward Logic

- `0`: the active Chrome tab does not satisfy OSWorld `is_expected_url_pattern_match`
- `1`: the active Chrome tab satisfies OSWorld `is_expected_url_pattern_match`
