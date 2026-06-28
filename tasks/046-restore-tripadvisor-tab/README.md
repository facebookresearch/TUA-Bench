# local/046-restore-tripadvisor-tab

Benchmark task for translating OSWorld Chrome example `06fe7178-4491-4589-810f-2e2bc9502122`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to restore the most recently closed tab
- The starting Chrome state matches the OSWorld setup: Lonely Planet and Airbnb are open,
  and TripAdvisor was just closed
- The verifier succeeds only if the exact OSWorld getter and metric logic see all three
  expected URLs as open tabs

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`06fe7178-4491-4589-810f-2e2bc9502122`, which asks:

`Can you make my computer bring back the last tab I shut down?`

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
        "https://www.lonelyplanet.com",
        "https://www.airbnb.com",
        "https://www.tripadvisor.com"
      ]
    }
  },
  {
    "type": "chrome_close_tabs",
    "parameters": {
      "urls_to_close": [
        "https://www.tripadvisor.com"
      ]
    }
  }
]
```

This local task does not preserve the remote-debugging bridge or pre-launch Chrome from an
external harness. Instead, the task container starts a fixed Xvfb display and launches a
live Chrome instance whose open tabs are prepared to match the OSWorld starting state.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `playwright`, `pytest`, and `tldextract`
- lightweight X11 support packages
- a `google-chrome` wrapper that launches Chromium on a shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open Lonely Planet, open Airbnb, open
  TripAdvisor, and then close TripAdvisor

That keeps the task faithful to OSWorld’s live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The expected final state is that Chrome has the Lonely Planet, Airbnb, and TripAdvisor
  tabs open
- Chrome should be left running so the verifier can inspect the live tab state

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to put the live browser into the solved tab state

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/open_tabs.json`
- `/logs/artifacts/Preferences`
- `/logs/artifacts/Sessions/`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `get_open_tabs_info` from `desktop_env/evaluators/getters/chrome.py`
- `is_expected_tabs` from `desktop_env/evaluators/metrics/chrome.py`
- `are_lists_equal` and `compare_urls` from `desktop_env/evaluators/metrics/utils.py`

The only Harbor-specific changes are:

- replacing the OSWorld environment object with fixed local process launch logic
- using `127.0.0.1:1337` instead of the OSWorld remote-debugging bridge
- using a fixed `:99` Xvfb display so the agent and browser share the same GUI target
- using `tldextract.TLDExtract(suffix_list_urls=None)` so URL normalization stays local

The verifier preserves an important OSWorld semantic detail: `is_expected_tabs` does not
check tab order. It checks that the set of open URLs matches the expected list.

## Reward Logic

- `0`: Chrome does not satisfy the exact OSWorld tab evaluator
- `1`: Chrome satisfies the exact OSWorld tab evaluator
