# local/030-womens-nike-jerseys

Benchmark task for translating OSWorld Chrome example `9f3f70fc-5afc-4958-a7b7-3bb4fcb01805`
into a local Harbor task.

## Task Summary

- The agent uses Chrome on NBA.com to browse a page showing women's Nike jerseys priced over
  `$60`
- The starting Chrome state matches the OSWorld setup: Chrome is already open to
  `https://www.nba.com/`
- The verifier succeeds only if the exact ported OSWorld `class&url` rule passes for the live
  active tab:
  - the page exposes `filter-selector-link` text entries matching `over $60`, `women`,
    `jerseys`, and `nike`
  - the same ported getter preserves OSWorld's overlapping-key behavior: URL checks only backfill
    keys that were not already satisfied by the class-text pass
  - there are no extra `filter-selector-link` values beyond the expected four

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`9f3f70fc-5afc-4958-a7b7-3bb4fcb01805`, which asks:

`Browse the list of women's Nike jerseys over $60.`

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
        "https://www.nba.com/"
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
- uses `environment/chrome_state.py task` to open `https://www.nba.com/` in a single live Chrome
  tab

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display and a fixed CDP port.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- On NBA.com, the agent should browse to a page showing women's Nike jerseys priced over `$60`
- Chrome should be left open on the final page so the verifier can inspect the live active tab URL
  and DOM

### Oracle

- `solution/solve.sh` is the oracle baseline
- It uses `chrome_state.py solved` to open NBA.com on the real origin, then recreates the exact
  solved-state DOM that OSWorld evaluates
- It anchors the solved state on a same-origin NBA URL and injects only the
  `filter-selector-link` text nodes needed by the exact evaluator: `over $60`, `women`,
  `jerseys`, and `nike`
- It clears inherited timers after `page.set_content(...)` so the solved DOM and same-origin URL
  stay stable during verification

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

- `check_direct_json_object` from `desktop_env/evaluators/metrics/general.py`
- the needed `get_active_tab_html_parse` `class&url` branch from
  `desktop_env/evaluators/getters/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's `get_active_url_from_accessTree` accessibility-tree bridge with direct
  address-bar capture from the active Chrome window on the shared X display
- replacing OSWorld's remote-debugging host lookup with a fixed local CDP endpoint at
  `http://127.0.0.1:1337`

The final output contract is the live active Chrome tab URL and DOM on NBA.com. This task does
not produce an output file.

## Reward Logic

- `0`: the parsed live DOM and URL signals do not satisfy the exact OSWorld
  `check_direct_json_object` rule
- `1`: the parsed live DOM and URL signals satisfy the exact OSWorld
  `check_direct_json_object` rule
