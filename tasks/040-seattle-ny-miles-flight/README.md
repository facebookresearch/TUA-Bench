# local/040-seattle-ny-miles-flight

Benchmark task for translating OSWorld Chrome example `6c4c23a1-42a4-43cc-9db1-2f86ff3738cc`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on Delta to find Seattle to New York flights for the 5th of next month
  and show only fares that can be purchased with miles
- The starting Chrome state matches the OSWorld URL contract: Chrome is already open to
  `https://www.delta.com/`
- The verifier succeeds only if the exact ported OSWorld `active_tab_html_parse` result matches:
  - `start = SEA`
  - `end = NYC`
  - `time = {DoW}, {Month} {Day0D}, {Year}` after `rule_relativeTime`
  - `category = Miles`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`6c4c23a1-42a4-43cc-9db1-2f86ff3738cc`, which asks:

`Find flights from Seattle to New York on 5th next month and only show those that can be purchased with miles.`

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
        "https://www.delta.com/"
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

This local task preserves the Chrome and Delta constraints while using a deterministic same-origin
Delta page at `https://www.delta.com/` inside the live Chrome tab. That keeps the benchmark meaning
intact while preserving the exact OSWorld DOM evaluator.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `tmux` and `asciinema` for terminal session support
- `playwright`, `pytest`, and `pytz`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the live address bar from the active Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open a synthetic Delta flight-search page in a
  single live Chrome tab at `https://www.delta.com/`

That preserves the OSWorld live-browser setup while removing the live Delta anti-bot dependency.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The agent should use the existing Delta tab to search for Seattle to New York flights on the
  5th of next month and switch the search to `Miles`
- Chrome should be left open on the final Delta results page so the verifier can inspect the live
  active tab URL and the live DOM

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to connect to the live browser, open the same-origin Delta page,
  and apply the exact solved state that the OSWorld evaluator expects

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the exact ported OSWorld check passes
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/parsed_result.json`
- `/logs/artifacts/verification_summary.json`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`
- `get_rule_relativeTime` and `apply_rules_to_timeFormat` from
  `desktop_env/evaluators/getters/misc.py`
- the needed `get_active_tab_html_parse` class and `class_multiObject_child` branches from
  `desktop_env/evaluators/getters/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display
- replacing OSWorld's remote-debugging host lookup with a fixed local CDP endpoint at
  `http://127.0.0.1:1337`

The final output contract is the live active Chrome tab URL and DOM on Delta's flight-search page.
This task does not produce an output file.

## Reward Logic

- `0`: the parsed live DOM does not satisfy the exact OSWorld `check_direct_json_object` rule
- `1`: the parsed live DOM satisfies the exact OSWorld `check_direct_json_object` rule
