# local/044-etsy-saved-passwords

Benchmark task for translating OSWorld Chrome example `12086550-11c0-466b-b367-1d9e75b3910e`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to open the saved passwords area in Password Manager
- The starting Chrome state matches the OSWorld setup: Chrome is already open on a live shared
  display
- The verifier succeeds only if the active Chrome tab URL matches
  `chrome://password-manager/passwords` under the exact OSWorld approximate active-tab metric

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`12086550-11c0-466b-b367-1d9e75b3910e`, which asks:

`Computer, please navigate to the area in my browser settings where my passwords are stored. I want to check my login information for Etsy without revealing it just yet.`

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

This local task does not preserve the OSWorld accessibility-tree HTTP bridge. Instead, the
task container starts a fixed Xvfb display and a live Chrome instance whose active tab is
prepared to match a fresh Chrome start page.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `pytest`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus bus
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to prepare a single live Chrome tab on
  `chrome://newtab/`

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- Chrome should be navigated to `chrome://password-manager/passwords`
- Stored passwords should not be revealed
- Chrome should be left open on the final page so the verifier can inspect the active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to
  `chrome://password-manager/passwords`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld metric logic used by this example:

- `is_expected_active_tab_approximate` from `desktop_env/evaluators/metrics/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

This example uses the original OSWorld `goto_prefix=""` setting, so the adapted getter keeps
the raw `chrome://...` address-bar value instead of prepending `https://`.

## Reward Logic

- `0`: the active Chrome tab does not satisfy OSWorld `is_expected_active_tab_approximate`
- `1`: the active Chrome tab satisfies OSWorld `is_expected_active_tab_approximate`
