# local/039-manchester-forecast

Benchmark task for translating OSWorld Chrome example `368d9ba4-203c-40c1-9fa3-da2f1430ce63`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to find Manchester, GB's monthly forecast on AccuWeather for this month
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.accuweather.com/`
- The verifier succeeds only if the active Chrome tab URL satisfies both exact OSWorld checks:
  - `get_url_dashPart(..., partIndex=-2)` must return `{"time": "{month}-weather"}`
  - `is_expected_url_pattern_match` must find `/manchester/` in the live URL

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`368d9ba4-203c-40c1-9fa3-da2f1430ce63`, which asks:

`Find the Monthly forecast for Manchester, GB for this month`

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
        "https://www.accuweather.com/"
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
- `playwright`, `pytest`, `pytz`, and `requests`
- `tmux` and `asciinema` for Harbor's non-root agent bootstrap
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.accuweather.com/` in a single
  live Chrome tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The existing Chrome tab should be navigated to Manchester, GB's monthly forecast page for
  the current month on AccuWeather
- Chrome should be left open on the final page so the verifier can inspect the live active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to AccuWeather's real
  Manchester monthly page for the current month using the month-specific `.../{month}-weather/...`
  path and current year query

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: both exact OSWorld URL checks pass
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `get_url_dashPart` from `desktop_env/evaluators/getters/chrome.py`
- `get_rule_relativeTime` and `apply_rules_to_timeFormat` from
  `desktop_env/evaluators/getters/misc.py`
- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`
- `is_expected_url_pattern_match` from `desktop_env/evaluators/metrics/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

The verifier keeps the original binary OSWorld semantics: both checks must pass.

## Reward Logic

- `0`: either the month-slug check or the Manchester URL-pattern check fails
- `1`: both exact OSWorld URL checks pass
