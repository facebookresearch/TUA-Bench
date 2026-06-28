# local/032-compare-iphones

Benchmark task for translating OSWorld Chrome example `f5d96daf-83a8-4c86-9686-bada31fc66ab`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on Apple's website to compare iPhone 15 Pro Max with iPhone 14 Pro Max
  and iPhone 13 Pro Max
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.apple.com/`
- The verifier succeeds only if the live active Chrome tab URL satisfies the exact OSWorld query
  check for `modelList`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`f5d96daf-83a8-4c86-9686-bada31fc66ab`, which asks:

`Compare iPhone 15 Pro Max with iPhone 14 Pro Max and iPhone 13 Pro Max`

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
        "https://www.apple.com/"
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
- uses `environment/chrome_state.py task` to open `https://www.apple.com/` in a single live
  Chrome tab

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The agent should compare iPhone 15 Pro Max with iPhone 14 Pro Max and iPhone 13 Pro Max on
  Apple's website
- Chrome should be left open on the final comparison page so the verifier can inspect the live
  active tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to Apple's compare page at
  `https://www.apple.com/iphone/compare/?modelList=iphone-15-pro-max,iphone-14-pro-max,iphone-13-pro-max`
- `chrome_state.py` also reapplies that exact same-origin URL with `history.replaceState(...)`
  after navigation so the local solved state preserves the exact OSWorld `modelList` contract if
  Apple canonicalizes the address bar during page boot

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

The final output contract is the live active Chrome tab URL on Apple's compare page. This task
does not produce an output file.

## Reward Logic

- `0`: the parsed live URL does not satisfy the exact OSWorld `check_direct_json_object` rule
- `1`: the parsed live URL satisfies the exact OSWorld `check_direct_json_object` rule
