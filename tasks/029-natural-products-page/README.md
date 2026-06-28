# local/029-natural-products-page

Benchmark task for translating OSWorld Chrome example `0d8b7de3-e8de-4d86-b9fd-dd2dce58a217`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to browse from Drugs.com to the natural products database
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.drugs.com/`
- The verifier succeeds only if the active Chrome tab URL matches either
  `https://www.drugs.com/npc/` or `https://www.drugs.com/npp/`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`0d8b7de3-e8de-4d86-b9fd-dd2dce58a217`, which asks:

`Browse the natural products database.`

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
        "https://drugs.com"
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
- `playwright`, `pytest`, and `tldextract`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.drugs.com/` in a single live
  Chrome tab

That keeps the task faithful to OSWorld’s live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The existing Chrome tab should be browsed to the natural products database page
- Chrome should be left open on the final page so the verifier can inspect the active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to
  `https://www.drugs.com/npc/`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld metric logic used by this example:

- `is_expected_active_tab` from `desktop_env/evaluators/metrics/chrome.py`
- `compare_urls` from `desktop_env/evaluators/metrics/utils.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld’s `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

The verifier preserves the original OSWorld `or` semantics: either `.../npc/` or `.../npp/`
is accepted.

## Reward Logic

- `0`: the active Chrome tab does not match the expected natural products database URLs
- `1`: the active Chrome tab matches one of the exact OSWorld accepted URLs
