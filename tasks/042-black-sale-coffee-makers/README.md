# local/042-black-sale-coffee-makers

Benchmark task for translating OSWorld Chrome example `7f52cab9-535c-4835-ac8c-391ee64dc930`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on Google Shopping to show drip coffee maker results filtered to black
  finishes, `$25 - $60`, and `On sale`
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://shopping.google.com/`
- The verifier succeeds only if both exact OSWorld checks pass:
  - the active Chrome tab URL query contains `q=drip coffee maker`
  - the live active tab HTML returns the exact `fT28tf` filter-chip booleans expected by OSWorld:
    `Black = true`, `$25 - $60 = true`, `On sale = true`, and `is_other_exist = false`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`7f52cab9-535c-4835-ac8c-391ee64dc930`, which asks:

`Create a list of drip coffee makers that are on sale and within $25-60 and have a black finish.`

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
        "https://shopping.google.com/"
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

This local task does not preserve OSWorld's separate remote-debugging bridge. Instead, the
task container starts a fixed Xvfb display and a live Chrome instance whose tab state is
prepared to match the OSWorld starting page.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `tmux` and `asciinema` for terminal session support
- `playwright` and `pytest`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the live address bar from the active Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://shopping.google.com/` in a single
  live Chrome tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The agent should show Google Shopping results for `drip coffee maker` with the `Black`,
  `$25 - $60`, and `On sale` filters applied
- Chrome should be left open on the final filtered Google Shopping results page so the verifier
  can inspect the live active tab URL and the live DOM

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to open Google on the real search origin, then recreates the
  exact solved-state filter-chip DOM that OSWorld evaluates
- It anchors the solved state on
  `https://www.google.com/search?tbm=shop&q=drip+coffee+maker` and clears inherited Google
  timers after `set_content(...)` so the page keeps the intended query URL and filter-chip DOM
- This same-origin reconstruction keeps the evaluator stable when live Google Shopping responses
  are brittle or automation-challenged in local translation workflows; the exact OSWorld checks
  only depend on the active query string and the visible `fT28tf` filter chips

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/url_result.json`
- `/logs/artifacts/class_result.json`
- `/logs/artifacts/verification_summary.json`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`
- `get_active_tab_url_parse` from `desktop_env/evaluators/getters/chrome.py`
- the needed `get_active_tab_html_parse` class `class_multiObject_search_exist` branch from
  `desktop_env/evaluators/getters/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` accessibility-tree bridge with direct
  address-bar capture from the active Chrome window on the shared X display
- replacing OSWorld's remote-debugging host lookup with a fixed local CDP endpoint at
  `http://127.0.0.1:1337`

The final output contract is the live active Chrome tab URL and DOM on Google Shopping's
filtered results page. This task does not produce an output file.

## Reward Logic

- `0`: either exact OSWorld query or filter-chip check fails
- `1`: both exact OSWorld checks pass
