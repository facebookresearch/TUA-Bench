# local/027-add-dota-dlc-cart

Benchmark task for translating OSWorld Chrome example `121ba48f-9e17-48ce-9bc6-a4fb17a7ebba`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to find Dota 2 on Steam and add all DLC to the cart
- The starting Chrome state matches the OSWorld setup: `https://www.dota2.com/home` and
  `https://store.steampowered.com/` are already open in separate tabs
- The verifier succeeds only if the exact OSWorld cart metric sees
  `The Dota 2 Official Soundtrack` in the Steam cart page HTML

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`121ba48f-9e17-48ce-9bc6-a4fb17a7ebba`, which asks:

`Find Dota 2 game and add all DLC to cart.`

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
        "https://www.dota2.com/home",
        "https://store.steampowered.com"
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
task container starts a fixed Xvfb display and a live Chrome instance whose tabs are prepared
to match the OSWorld starting state.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `playwright` and `pytest`
- lightweight X11 support packages
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open the Dota 2 home page and the Steam store

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The expected final state is that the Steam cart contains the Dota 2 DLC that OSWorld checks
- Chrome should be left running on the Steam cart page so the verifier can inspect the live
  browser session

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to open the Dota 2 Steam page and submit Steam's exact
  `add_all_dlc_to_cart` form for this game

The Dota 2 store page currently exposes two DLC entries, but only
`The Dota 2 Official Soundtrack` is a paid add-to-cart item. That is why the exact OSWorld
evaluator only checks for that soundtrack string in the final cart page HTML.

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/page_info.json`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld logic used by this example:

- `get_page_info` from `desktop_env/evaluators/getters/chrome.py`
- `is_added_to_steam_cart` from `desktop_env/evaluators/metrics/chrome.py`

The only Harbor-specific changes are:

- replacing the OSWorld environment object with a fixed local CDP endpoint at `127.0.0.1:1337`
- launching the fallback browser locally with the task's `google-chrome` wrapper
- using the shared `:99` Xvfb display and local Chrome profile prepared by the task container

## Reward Logic

- `0`: the Steam cart page HTML does not contain `The Dota 2 Official Soundtrack`
- `1`: the exact OSWorld cart evaluator finds `The Dota 2 Official Soundtrack` in the cart page
