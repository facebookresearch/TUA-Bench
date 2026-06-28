# local/036-license-eligibility

Benchmark task for translating OSWorld Chrome example `a728a36e-8bf1-4bb6-9a03-ef039a5233f0`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on the Virginia DMV site to find the Driver License Eligibility
  Requirements page
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.dmv.virginia.gov/`
- The verifier succeeds only if the active Chrome tab URL matches the exact OSWorld regex pattern
  `^https://(www\.)?dmv\.virginia\.gov/licenses-ids/license/applying/eligibility`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`a728a36e-8bf1-4bb6-9a03-ef039a5233f0`, which asks:

`Find the Driver License Eligibility Requirements`

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
        "https://www.dmv.virginia.gov/"
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
- `playwright` and `pytest`
- lightweight X11 support packages
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus daemon
- launches Chromium with `--remote-debugging-port=1337`
- uses `environment/chrome_state.py task` to open `https://www.dmv.virginia.gov/` in a single
  live Chrome tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- The existing Chrome tab should be used to find the Virginia DMV driver license eligibility page
- Chrome should be left open on the final Virginia DMV page so the verifier can inspect the active
  tab URL

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to navigate the live browser to
  `https://www.dmv.virginia.gov/licenses-ids/license/applying/eligibility`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/Preferences`

`tests/test_outputs.py` ports the exact OSWorld evaluator function used by this example:

- `is_expected_url_pattern_match` from `desktop_env/evaluators/metrics/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` AT-SPI bridge with direct address-bar
  capture from the active Chrome window on the shared X display

The final output contract is the live active Chrome tab URL on the Virginia DMV site. This task
does not produce an output file.

## Reward Logic

- `0`: the active Chrome tab URL does not satisfy the exact OSWorld regex pattern
- `1`: the active Chrome tab URL satisfies
  `^https://(www\.)?dmv\.virginia\.gov/licenses-ids/license/applying/eligibility`
