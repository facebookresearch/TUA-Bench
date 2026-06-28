# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import zipfile
import sys
from pathlib import Path


TASK_SPEC = {'expected': [{'rules': {'text': 'ls', 'type': 'text'}, 'type': 'rule'},
              {'rules': {'text': '1s', 'type': 'text'}, 'type': 'rule'},
              {'rules': {'text': '1s', 'type': 'text'}, 'type': 'rule'}],
 'result': [{'dest': 'ls.png', 'path': '/home/user/Desktop/ls.png', 'type': 'vm_file'},
            {'dest': 'ls.png', 'path': '/home/user/Desktop/ls.png', 'type': 'vm_file'},
            {'dest': 'ls.png', 'path': '/home/user/Desktop/ls.png', 'type': 'vm_file'}],
 'slug': '069-linux-ls-tutorial'}
CACHE_DIR = Path("/tmp") / TASK_SPEC["slug"] / "oracle"
ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")


def localize_path(path: str | Path) -> Path:
    raw = str(path)
    if ROOT_OVERRIDE:
        root = Path(ROOT_OVERRIDE)
        if raw.startswith("/app/"):
            return root / "app" / raw.removeprefix("/app/")
        if raw == "/app":
            return root / "app"
        if raw.startswith("/home/user/"):
            return root / "home" / "user" / raw.removeprefix("/home/user/")
        if raw == "/home/user":
            return root / "home" / "user"
    return Path(raw).expanduser()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rewrite_root_path_text(text: str) -> str:
    if not ROOT_OVERRIDE:
        return text
    home_root = str(localize_path("/home/user"))
    app_root = str(localize_path("/app"))
    text = text.replace(home_root, "__TUA_HOME_REAL__").replace(app_root, "__TUA_APP_REAL__")
    text = text.replace("/home/user/", "__TUA_HOME__/").replace("/home/user", "__TUA_HOME__")
    text = text.replace("/app/", "__TUA_APP__/").replace("/app", "__TUA_APP__")
    return (
        text.replace("__TUA_HOME__", home_root)
        .replace("__TUA_APP__", app_root)
        .replace("__TUA_HOME_REAL__", home_root)
        .replace("__TUA_APP_REAL__", app_root)
    )


def prepare_subprocess_command(command, shell: bool):
    if not ROOT_OVERRIDE:
        return command
    if shell:
        text = command if isinstance(command, str) else " ".join(str(part) for part in command)
        return rewrite_root_path_text(text)
    if isinstance(command, str):
        return rewrite_root_path_text(command)
    return [rewrite_root_path_text(str(part)) for part in command]


def subprocess_env(kwargs: dict) -> dict:
    env = os.environ.copy()
    env.update(kwargs.get("env", {}))
    if ROOT_OVERRIDE:
        home = str(localize_path("/home/user"))
        env["HOME"] = home
        local_bin = str(localize_path("/home/user/.local/bin"))
        python_bin = str(Path(sys.executable).resolve().parent)
        path_parts = [python_bin, local_bin]
        existing_path = env.get("PATH")
        if existing_path:
            path_parts.append(existing_path)
        env["PATH"] = ":".join(path_parts)
        python_paths = [
            str(localize_path("/home/user/.local/lib/python3.13/site-packages")),
            str(localize_path("/home/user/.local/lib/python3.12/site-packages")),
            str(localize_path("/home/user/.local/lib/python3.11/site-packages")),
        ]
        existing = env.get("PYTHONPATH")
        if existing:
            python_paths.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(python_paths)
    return env


def subprocess_cwd(kwargs: dict) -> str | None:
    if kwargs.get("cwd") is not None:
        return kwargs["cwd"]
    if ROOT_OVERRIDE:
        return str(localize_path("/home/user"))
    return None


def resolve_subprocess_invocation(command, shell: bool):
    if shell:
        return prepare_subprocess_command(command, True), True
    if isinstance(command, list) and any(token in {"|", "||", "&&", ";", ">", ">>", "<", "2>", "2>>"} for token in command):
        return prepare_subprocess_command(" ".join(str(part) for part in command), True), True
    return prepare_subprocess_command(command, False), False


if ROOT_OVERRIDE:
    _ORIG_RUN = subprocess.run
    _ORIG_POPEN = subprocess.Popen
    _ORIG_CHECK_OUTPUT = subprocess.check_output

    def _patched_run(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_RUN(command, *args, **kwargs)

    def _patched_popen(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_POPEN(command, *args, **kwargs)

    def _patched_check_output(command, *args, **kwargs):
        shell = bool(kwargs.get("shell", False))
        command, shell = resolve_subprocess_invocation(command, shell)
        kwargs["shell"] = shell
        kwargs["env"] = subprocess_env(kwargs)
        kwargs["cwd"] = subprocess_cwd(kwargs)
        return _ORIG_CHECK_OUTPUT(command, *args, **kwargs)

    subprocess.run = _patched_run
    subprocess.Popen = _patched_popen
    subprocess.check_output = _patched_check_output


def fetch(url: str, dest_name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / dest_name
    if not target.exists():
        subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "1", url, "-o", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return target


def main() -> int:
    output = localize_path("/home/user/Desktop/ls.png")
    ensure_parent(output)
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1200, 500), "white")
    draw = ImageDraw.Draw(image)
    font = None
    for candidate in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(candidate, 220)
            break
        except Exception:
            continue
    if font is not None:
        draw.text((80, 80), "ls", fill="black", font=font)
    else:
        draw.rectangle((180, 200, 340, 760), fill="black")
        draw.rectangle((340, 680, 760, 760), fill="black")
        draw.rectangle((920, 200, 1080, 760), fill="black")
        draw.arc((920, 520, 1340, 940), start=180, end=360, fill="black", width=120)
    image.save(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
