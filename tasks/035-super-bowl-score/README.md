# local/035-super-bowl-score

Benchmark task for translating OSWorld Chrome example `f0b971a1-6831-4b9b-a50e-22a6e47f45ba`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on NFL.com to find the score record for the Super Bowl of the 2019 NFL
  season
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.nfl.com/`
- The verifier succeeds only if the active Chrome tab URL matches
  `https://www.nfl.com/scores/2019/post4`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`f0b971a1-6831-4b9b-a50e-22a6e47f45ba`, which asks:

`Please help me find the score record for the Super Bowl of the 2019 NFL season (played in 2020) in the NFL website.`

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
        "https://www.nfl.com/"
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
- `tmux` and `asciinema` for terminal session support
- `playwright`, `pytest`, and `tldextract`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.nfl.com/` in a single live Chrome
  tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The existing Chrome tab should be used to find the NFL score record page for the Super Bowl of
  the 2019 NFL season
- Chrome should be left open on the final NFL page so the verifier can inspect the active
  tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to
  `https://www.nfl.com/scores/2019/post4`

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

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display
- preserving the original `goto_prefix="https://www."` behavior so the adapted getter matches
  OSWorld when Chrome omits the scheme and `www.` in the visible address bar

The final output contract is the live active Chrome tab URL on NFL.com. This task does not
produce an output file.

## Reward Logic

- `0`: the active Chrome tab does not match the exact OSWorld accepted NFL URL
- `1`: the active Chrome tab matches `https://www.nfl.com/scores/2019/post4`
