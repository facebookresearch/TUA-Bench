# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

logger = logging.getLogger("desktopenv.chrome_disable_dark_mode")

APPEARANCE_RULE = {"expected": ["light", "system"]}
URL_RULE = {"expected": ["^chrome://settings/appearance/?$"]}
RESULT_CONFIG = {"goto_prefix": ""}
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")
APPEARANCE_MODE_ARTIFACT = Path("/logs/artifacts/appearance_mode.txt")


def get_preferences_path() -> Path:
    return Path(
        os.environ.get(
            "PREFERENCES_PATH",
            str(Path.home() / ".config/google-chrome/Default/Preferences"),
        )
    )


def get_remote_debugging_url() -> str:
    return os.environ.get(
        "REMOTE_DEBUGGING_URL",
        f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
    )


def get_chrome_color_scheme(env, config):
    """
    Get Chrome browser color scheme preference.
    Returns one of: "system", "light", "dark".
    """

    def _normalize_color_scheme(raw_value):
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            if normalized in {"system", "default", "0"}:
                return "system"
            if normalized in {"light", "1"}:
                return "light"
            if normalized in {"dark", "2"}:
                return "dark"
            return None
        if isinstance(raw_value, (int, float)):
            mapping = {0: "system", 1: "light", 2: "dark"}
            return mapping.get(int(raw_value), None)
        return None

    def _extract_mode_from_preferences(data):
        theme_data = data.get("browser", {}).get("theme", {})
        raw_value = theme_data.get("color_scheme2", theme_data.get("color_scheme", None))
        mode = _normalize_color_scheme(raw_value)
        system_theme_flag = data.get("extensions", {}).get("theme", {}).get("system_theme", None)
        if system_theme_flag in [0, "0", False]:
            return "light"
        return mode if mode else "system"

    try:
        final_mode = "system"
        for _ in range(5):
            best_mode = None
            try:
                content = get_preferences_path().read_text(encoding="utf-8")
                data = json.loads(content)
                mode = _extract_mode_from_preferences(data)
                if mode in {"light", "dark"}:
                    best_mode = mode
                elif best_mode is None:
                    best_mode = mode
            except Exception:
                pass

            if best_mode is not None:
                final_mode = best_mode
                if best_mode == "light":
                    return "light"
            time.sleep(1)

        return final_mode
    except Exception as e:
        logger.error("Error: %s", e)
        return "system"


def get_chrome_appearance_mode_ui(env, config):
    """
    Read Chrome appearance mode from the settings UI (chrome://settings/appearance).
    Returns one of: "light", "dark", "system".
    Falls back to get_chrome_color_scheme if UI probing fails.
    """
    remote_debugging_url = get_remote_debugging_url()

    js_probe = r"""
() => {
  const lower = (s) => String(s || '').toLowerCase();
  const allowedPrefPaths = new Set([
    'prefs.browser.theme.color_scheme',
    'prefs.browser.theme.color_scheme2',
    'prefs.extensions.theme.system_theme',
  ]);

  const inferFromText = (s) => {
    const t = lower(s);
    if (t.includes('light')) return 'light';
    if (t.includes('dark')) return 'dark';
    if (t.includes('device') || t.includes('system') || t.includes('default')) return 'system';
    return null;
  };

  const collectShadowRoots = (root, acc) => {
    if (!root) return;
    const all = root.querySelectorAll('*');
    for (const el of all) {
      if (el.shadowRoot) {
        acc.push(el.shadowRoot);
        collectShadowRoots(el.shadowRoot, acc);
      }
    }
  };

  const modes = [];

  try {
    const ui = document.querySelector('settings-ui');
    const prefs = ui && ui.prefs ? ui.prefs : null;
    const visited = new Set();
    const walk = (obj, path) => {
      if (!obj || typeof obj !== 'object') return;
      if (visited.has(obj)) return;
      visited.add(obj);

      if (Object.prototype.hasOwnProperty.call(obj, 'value')) {
        const v = obj.value;
        const p = lower(path);
        if (allowedPrefPaths.has(p)) {
          if (p.endsWith('extensions.theme.system_theme')) {
            if (v === 0 || v === '0' || v === false) modes.push('light');
            if (v === 1 || v === '1' || v === true) modes.push('dark');
          } else {
            if (v === 1 || v === '1' || lower(v) === 'light') modes.push('light');
            if (v === 2 || v === '2' || lower(v) === 'dark') modes.push('dark');
            if (v === 0 || v === '0' || lower(v) === 'system' || lower(v) === 'default' || lower(v) === 'device') modes.push('system');
          }
        }
      }

      for (const [k, v] of Object.entries(obj)) {
        walk(v, path ? `${path}.${k}` : k);
      }
    };
    walk(prefs, 'prefs');
  } catch (e) {}

  try {
    const roots = [document];
    collectShadowRoots(document, roots);
    const candidates = [];
    for (const r of roots) {
      for (const el of r.querySelectorAll('[selected],[checked],[aria-checked="true"],option:checked')) {
        const txt = (el.innerText || el.textContent || '').trim();
        if (txt) candidates.push(txt);
      }
    }
    for (const t of candidates) {
      const m = inferFromText(t);
      if (m) modes.push(m);
    }
  } catch (e) {}

  if (modes.includes('light')) return 'light';
  if (modes.includes('dark')) return 'dark';
  if (modes.includes('system')) return 'system';
  return null;
}
"""

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(remote_debugging_url)
            except Exception:
                return get_chrome_color_scheme(env, config)

            page = browser.contexts[0].new_page()
            page.goto("chrome://settings/appearance", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            mode = page.evaluate(js_probe)
            browser.close()

            if mode in {"light", "dark", "system"}:
                return mode
            return get_chrome_color_scheme(env, config)
    except Exception:
        return get_chrome_color_scheme(env, config)


def match_in_list(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result in expect:
        return 1.0
    else:
        return 0.0


def is_expected_url_pattern_match(result, rules) -> float:
    """
    This function is used to search the expected pattern in the url using regex.
    result is the return value of function "activte_tab_info" or return value of function
    "get_active_url_from_accessTree"
    """
    if not result:
        return 0.0

    if isinstance(result, str):
        result_url = result
        logger.info("result url: %s", result_url)
    elif isinstance(result, dict) and "url" in result:
        result_url = result["url"]
        logger.info("result url: %s", result_url)
    else:
        logger.error(
            "Invalid result format: %s, expected string URL or dict with 'url' field",
            type(result),
        )
        return 0.0

    logger.info("Result URL to match: %s", result_url)

    patterns = rules["expected"]
    logger.info("expected_regex: %s", patterns)
    for pattern in patterns:
        match = re.search(pattern, result_url)
        logger.info("match: %s", match)
        if not match:
            return 0.0
    return 1.0


def _find_chrome_window_id():
    commands = [
        ["xdotool", "search", "--onlyvisible", "--class", "chromium"],
        ["xdotool", "search", "--onlyvisible", "--class", "Chromium"],
        ["xdotool", "search", "--onlyvisible", "--name", "Chromium|Google Chrome"],
    ]
    for command in commands:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            window_ids = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            if window_ids:
                return window_ids[-1]
    return None


def _focus_chrome_window(window_id: str) -> None:
    subprocess.run(
        ["xdotool", "windowactivate", "--sync", window_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ["xdotool", "windowfocus", window_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(0.2)


def _copy_address_bar(window_id: str) -> str:
    _focus_chrome_window(window_id)
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input="",
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+l"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(0.2)
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+c"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(0.2)
    clipboard_text = subprocess.check_output(
        ["xclip", "-o", "-selection", "clipboard"],
        text=True,
    ).strip()
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "Escape"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return clipboard_text


def get_active_url_from_accessTree(config):
    window_id = _find_chrome_window_id()
    if window_id is None:
        logger.error("No visible Chrome window found on the shared X display")
        ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_URL_ARTIFACT.write_text("\n", encoding="utf-8")
        return None

    raw_url = None
    for _ in range(3):
        try:
            candidate = _copy_address_bar(window_id)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to copy active address bar: %s", error)
            candidate = ""
        if candidate and "Search Google" not in candidate and "Type a URL" not in candidate:
            raw_url = candidate
            break
        time.sleep(1)

    if not raw_url:
        logger.error("Failed to read a usable Chrome address bar value")
        ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_URL_ARTIFACT.write_text("\n", encoding="utf-8")
        return None

    goto_prefix = config.get("goto_prefix", "https://")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", raw_url):
        active_tab_url = raw_url
    elif raw_url.startswith("www."):
        active_tab_url = f"https://{raw_url}"
    else:
        active_tab_url = f"{goto_prefix}{raw_url}"

    logger.info("Active tab url now: %s", active_tab_url)
    ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_URL_ARTIFACT.write_text(f"{active_tab_url}\n", encoding="utf-8")
    return active_tab_url


def evaluate_osworld_conditions(appearance_mode, active_url):
    return (
        match_in_list(appearance_mode, APPEARANCE_RULE),
        is_expected_url_pattern_match(active_url, URL_RULE),
    )


def _write_preferences(path: Path, mode_value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "browser": {
            "theme": {
                "color_scheme": mode_value,
                "color_scheme2": mode_value,
            }
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_sanity_evaluator_roundtrip(monkeypatch, tmp_path):
    preference_path = tmp_path / "Preferences"
    monkeypatch.setenv("REMOTE_DEBUGGING_URL", "http://127.0.0.1:1")

    _write_preferences(preference_path, 1)
    monkeypatch.setenv("PREFERENCES_PATH", str(preference_path))
    light_mode = get_chrome_appearance_mode_ui(None, {})
    assert evaluate_osworld_conditions(light_mode, "chrome://settings/appearance") == (1.0, 1.0)
    assert evaluate_osworld_conditions(light_mode, "chrome://settings/privacy") == (1.0, 0.0)

    _write_preferences(preference_path, 2)
    dark_mode = get_chrome_appearance_mode_ui(None, {})
    assert evaluate_osworld_conditions(dark_mode, "chrome://settings/appearance") == (0.0, 1.0)


def test_main():
    # Capture the live address bar before the CDP UI probe in case the remote browser disconnects.
    active_url = get_active_url_from_accessTree(RESULT_CONFIG)
    appearance_mode = get_chrome_appearance_mode_ui(None, {})
    APPEARANCE_MODE_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    APPEARANCE_MODE_ARTIFACT.write_text(f"{appearance_mode}\n", encoding="utf-8")

    appearance_score, url_score = evaluate_osworld_conditions(appearance_mode, active_url)
    assert appearance_score == 1.0, (
        "Chrome appearance mode does not satisfy OSWorld match_in_list for "
        "chrome_appearance_mode_ui"
    )
    assert url_score == 1.0, (
        "Chrome active tab URL does not satisfy OSWorld is_expected_url_pattern_match"
    )
