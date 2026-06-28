# local/037-electric-cars-under-50k

Benchmark task for translating OSWorld Chrome example `82279c77-8fc6-46f6-9622-3ba96f61b477`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on Cars.com to find electric cars with a maximum price of `$50,000`
  within `50` miles of ZIP code `10001`
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.cars.com/`
- The verifier succeeds only if the live active Chrome tab URL satisfies the exact OSWorld query
  checks for `list_price_max`, `maximum_distance`, `zip`, and `fuel_slugs[]`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`82279c77-8fc6-46f6-9622-3ba96f61b477`, which asks:

`Find electric cars with a maximum price of $50,000 within 50 miles of 10001.`

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
        "https://www.cars.com/"
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
- `playwright` and `pytest`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the live address bar from the active Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.cars.com/` in a single live
  Chrome tab

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The agent should search Cars.com for electric cars under `$50,000` within `50` miles of ZIP
  `10001`
- Chrome should be left open on the final search results page so the verifier can inspect the
  live active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to a Cars.com results URL whose
  query string matches the exact OSWorld evaluator contract

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/parsed_result.json`
- `/logs/artifacts/verification_summary.json`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `get_active_tab_url_parse` from `desktop_env/evaluators/getters/chrome.py`
- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

The final output contract is the live active Chrome tab URL on Cars.com's search results page.
This task does not produce an output file.

## Reward Logic

- `0`: the parsed live URL does not satisfy the exact OSWorld `check_direct_json_object` rule
- `1`: the parsed live URL satisfies the exact OSWorld `check_direct_json_object` rule
