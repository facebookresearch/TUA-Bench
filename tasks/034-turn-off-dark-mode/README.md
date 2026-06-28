# local/034-turn-off-dark-mode

Benchmark task for translating OSWorld Chrome example `93eabf48-6a27-4cb6-b963-7d5fe1e0d3a9`
into a local Harbor task.

## Task Summary

- The agent uses Chrome to turn off dark mode from Chrome's built-in Appearance settings
- The starting Chrome state matches the OSWorld setup: Chrome is already open and dark mode is
  pre-enabled in the saved profile
- The verifier succeeds only if the exact OSWorld appearance-mode getter returns `light` or
  `system` and the live active Chrome URL matches `chrome://settings/appearance`

The full prompt contract lives in `instruction.md`.

This task is a terminal-oriented translation of the OSWorld Chrome example
`93eabf48-6a27-4cb6-b963-7d5fe1e0d3a9`, which asks:

`Could you assist me in turning off the dark mode feature in Google Chrome? I've noticed that while dark mode is great for reducing glare, it actually makes it more challenging for me to read text clearly, especially with my astigmatism.`

In OSWorld, the setup phase:

- prewrites `browser.theme.color_scheme = 2` and `color_scheme2 = 2` into the Chrome
  `Preferences` file
- launches `google-chrome --remote-debugging-port=1337`
- launches the `socat` remote-debugging bridge

This local task preserves the dark-mode-on starting state and the live browser requirement, but
drops the extra `socat` bridge because the task image can connect directly to the local Chrome
CDP endpoint.

## System Design

### Environment

`environment/Dockerfile` installs:

- Debian bookworm `chromium`
- `pytest`
- `playwright` so the verifier can port the exact OSWorld `chrome_appearance_mode_ui` getter via
  `connect_over_cdp`
- `xclip` and `xdotool` so the verifier can read the active address bar from the live Chrome
  window
- a `google-chrome` wrapper that launches Chromium on the shared `:99` Xvfb display

When the container starts, `environment/task-entrypoint.sh`:

- starts `Xvfb :99`
- starts a session D-Bus bus
- runs `environment/chrome_state.py task` to seed Chrome dark mode in
  `~/.config/google-chrome/Default/Preferences`
- launches Chromium with `--remote-debugging-port=1337` on `chrome://newtab/`

That keeps the task faithful to OSWorld's live-browser setup while still making the browser
reachable from the terminal through a fixed display.

### Agent Contract

- Harbor runs the agent inside the task container as user `agent`
- The agent works in `/app`
- The prompt explicitly instructs the agent to use `Chrome`
- Chrome is already open with dark mode enabled
- Chrome dark mode must be turned off from Chrome's built-in settings
- Chrome should be left open on `chrome://settings/appearance` when the task is finished

### Oracle

- `solution/solve.sh` is the oracle baseline
- It calls `chrome_state.py solved` to rewrite the Chrome appearance preference to light mode and
  relaunch the live browser on `chrome://settings/appearance`

### Verifier

`tests/test.sh` runs a single pytest check and writes a binary reward:

- `1`: the output satisfies the translated task contract
- `0`: otherwise

`tests/test.sh` always preserves these artifacts when present:

- `/logs/artifacts/Preferences`
- `/logs/artifacts/active_url.txt`
- `/logs/artifacts/appearance_mode.txt`

`tests/test_outputs.py` ports the exact OSWorld evaluator logic used by this example:

- `get_chrome_appearance_mode_ui` from `desktop_env/evaluators/getters/chrome.py`
- `get_chrome_color_scheme` from `desktop_env/evaluators/getters/chrome.py`
- `match_in_list` from `desktop_env/evaluators/metrics/general.py`
- `is_expected_url_pattern_match` from `desktop_env/evaluators/metrics/chrome.py`

The Harbor-specific getter adaptation is:

- replacing OSWorld's VM env object with a fixed local `http://127.0.0.1:1337` CDP endpoint
- replacing OSWorld's accessibility-tree bridge with direct address-bar capture from the active
  Chrome window on the shared X display

This example uses the original OSWorld `goto_prefix=""` setting, so the adapted getter keeps the
raw `chrome://...` address-bar value instead of prepending `https://`.

## Reward Logic

- `0`: either the appearance-mode getter still reports `dark` or the active Chrome tab is not on
  `chrome://settings/appearance`
- `1`: both exact OSWorld checks pass
