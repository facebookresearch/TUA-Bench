#!/opt/venv/bin/python
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


import os
import argparse
import subprocess
import time
from pathlib import Path

TASK_URL = "chrome://newtab/"
SOLVED_URL = "chrome://password-manager/passwords"
PROFILE_DIR = Path.home() / ".config/google-chrome"
BROWSER_PATTERN = f"/usr/lib/chromium/chromium.*--user-data-dir={PROFILE_DIR}"


def cleanup_profile_locks() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for path in PROFILE_DIR.glob("Singleton*"):
        if path.is_dir():
            subprocess.run(["rm", "-rf", str(path)], check=True)
        else:
            path.unlink()


def terminate_browser_processes() -> None:
    subprocess.run(
        ["pkill", "-f", BROWSER_PATTERN],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        running = subprocess.run(
            ["pgrep", "-f", BROWSER_PATTERN],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if running.returncode != 0:
            return
        time.sleep(0.5)

    subprocess.run(
        ["pkill", "-9", "-f", BROWSER_PATTERN],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(1)


def launch_browser(initial_url: str) -> subprocess.Popen:
    return subprocess.Popen(
        ["google-chrome", f"--remote-debugging-port={os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}", initial_url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _find_chrome_window_id() -> str | None:
    deadline = time.time() + 30
    commands = [
        ["xdotool", "search", "--onlyvisible", "--class", "chromium"],
        ["xdotool", "search", "--onlyvisible", "--class", "Chromium"],
        ["xdotool", "search", "--onlyvisible", "--name", "Chromium|Google Chrome"],
    ]
    while time.time() < deadline:
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
        time.sleep(0.5)
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


def _navigate_via_address_bar(window_id: str, target_url: str) -> None:
    _focus_chrome_window(window_id)
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+l"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(0.2)
    subprocess.run(
        ["xdotool", "type", "--window", window_id, "--clearmodifiers", "--delay", "15", target_url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "Return"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(1.5)


def ensure_target_url(window_id: str, target_url: str) -> None:
    for _ in range(5):
        current_url = _copy_address_bar(window_id)
        if current_url == target_url:
            return
        _navigate_via_address_bar(window_id, target_url)
    raise RuntimeError(f"Chrome address bar never reached expected URL: {target_url}")


def set_state(mode: str) -> None:
    if mode == "task":
        target_url = TASK_URL
    elif mode == "solved":
        target_url = SOLVED_URL
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    terminate_browser_processes()
    cleanup_profile_locks()
    launch_browser(target_url)
    window_id = _find_chrome_window_id()
    if window_id is None:
        raise RuntimeError("Could not find a visible Chrome window")

    if mode == "solved":
        ensure_target_url(window_id, target_url)

    time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["task", "solved"])
    args = parser.parse_args()
    set_state(args.mode)


if __name__ == "__main__":
    main()
