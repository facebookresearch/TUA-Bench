# local/038-zurich-rental-car

Benchmark task for translating OSWorld Chrome example `1704f00f-79e6-43a7-961b-cedd3724d5fd`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on Rentalcars.com to find a large rental car in Zurich from next Monday
  to Friday, sorted by price
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.rentalcars.com/`
- The verifier succeeds only if the active Chrome tab URL satisfies both exact OSWorld query
  checks:
  - `locationName`, `dropLocationName`, `filterCriteria_carCategory`, and
    `filterCriteria_sortBy`
  - `puDay`, `puMonth`, `puYear`, `doDay`, `doMonth`, and `doYear` after applying the original
    `rule_relativeTime` logic in `Europe/Zurich`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`1704f00f-79e6-43a7-961b-cedd3724d5fd`, which asks:

`Find a large car from next Monday to Friday in Zurich, sorted by price.`

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
        "https://www.rentalcars.com/"
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

This local task does not preserve OSWorld's separate remote-debugging bridge. Instead, the task
container starts a fixed Xvfb display and a live Chrome instance whose tab state is prepared to
match the OSWorld starting page.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `playwright`, `pytest`, and `pytz`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the live address bar from the active Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.rentalcars.com/` in a single
  live Chrome tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The agent should search Rentalcars.com for a large Zurich rental from next Monday to Friday,
  with pick-up and drop-off both in Zurich, then sort the results by price
- Chrome should be left open on the final search results page so the verifier can inspect the
  live active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to compute the exact OSWorld relative dates in
  `Europe/Zurich` and navigate the live browser to Rentalcars.com's real
  `SearchResults.do?...` page with the expected query parameters

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `get_active_tab_url_parse` from `desktop_env/evaluators/getters/chrome.py`
- `get_rule_relativeTime` and `apply_rules_to_timeFormat` from
  `desktop_env/evaluators/getters/misc.py`
- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

The final output contract is the live active Chrome tab URL on Rentalcars.com's search results
page. This task does not produce an output file.

## Reward Logic

- `0`: either exact OSWorld query-param check fails
- `1`: both exact OSWorld query-param checks pass
