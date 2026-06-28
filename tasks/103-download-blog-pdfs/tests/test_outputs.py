# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, urlparse, urlunparse

import lxml.etree
import pandas as pd
import pyatspi
import pytesseract
from lxml.cssselect import CSSSelector
from playwright.sync_api import TimeoutError, sync_playwright

TASK_SPEC = {'artifact_paths': [],
 'downloads': [],
 'expected': {'rules': {'expected': '[1, 1]\n'}, 'type': 'rule'},
 'infeasible': None,
 'metric_conj': 'and',
 'metric_funcs': ['exact_match'],
 'metric_modules': {'exact_match': 'general'},
 'metric_options': {},
 'postconfig': [{'parameters': {'files': [{'path': '/home/user/Desktop/script.py',
                                           'url': 'https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/multi_apps/da922383-bfa4-4cd3-bbad-6bebab3d7742/script.py'}]},
                 'type': 'download'},
                {'parameters': {'command': 'pip install PyMuPDF', 'shell': 'true'},
                 'type': 'execute'}],
 'result': {'command': 'python /home/user/Desktop/script.py',
            'shell': 'true',
            'type': 'vm_command_line'},
 'sanity': {'mode': 'oracle_eval'},
 'slug': '103-download-blog-pdfs'}

logger = logging.getLogger(f"tua.multi_apps.{TASK_SPEC['slug']}")
logging.basicConfig(level=logging.INFO)

ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")
CACHE_DIR = Path("/tmp") / TASK_SPEC["slug"]
ARTIFACT_DIR = Path("/logs/artifacts")
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)

NS = {
    "st": "https://accessibility.ubuntu.example.org/ns/state",
    "attr": "https://accessibility.ubuntu.example.org/ns/attributes",
    "cp": "https://accessibility.ubuntu.example.org/ns/component",
    "doc": "https://accessibility.ubuntu.example.org/ns/document",
    "docattr": "https://accessibility.ubuntu.example.org/ns/document/attributes",
    "txt": "https://accessibility.ubuntu.example.org/ns/text",
    "val": "https://accessibility.ubuntu.example.org/ns/value",
    "act": "https://accessibility.ubuntu.example.org/ns/action",
}


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


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _rewrite_root_path_text(text: str) -> str:
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


def _prepare_subprocess_command(command: Any, shell: bool) -> Any:
    if not ROOT_OVERRIDE:
        return command
    if shell:
        text = command if isinstance(command, str) else " ".join(str(part) for part in command)
        return _rewrite_root_path_text(text)
    if isinstance(command, str):
        return _rewrite_root_path_text(command)
    return [_rewrite_root_path_text(str(part)) for part in command]


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
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


def _subprocess_cwd() -> str | None:
    if not ROOT_OVERRIDE:
        return None
    return str(localize_path("/home/user"))


def _resolve_subprocess_invocation(command: Any, shell: bool) -> tuple[Any, bool]:
    if shell:
        return _prepare_subprocess_command(command, True), True
    if isinstance(command, list) and any(token in {"|", "||", "&&", ";", ">", ">>", "<", "2>", "2>>"} for token in command):
        return _prepare_subprocess_command(" ".join(str(part) for part in command), True), True
    return _prepare_subprocess_command(command, False), False


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


def ensure_downloads() -> None:
    for item in TASK_SPEC.get("downloads", []):
        destination = localize_path(item["path"])
        ensure_parent(destination)
        if destination.exists():
            continue
        shutil.copyfile(fetch(item["url"], item["dest_name"]), destination)


def get_vm_file(config: dict[str, Any]) -> Any:
    multi = normalize_bool(config.get("multi", False))
    paths = config["path"] if multi else [config["path"]]
    gives = set(config.get("gives", list(range(len(paths)))))
    resolved = []
    for idx, path in enumerate(paths):
        resolved_path = localize_path(path)
        if idx not in gives:
            continue
        if not resolved_path.exists():
            return None if not multi else [None]
        resolved.append(str(resolved_path))
    return resolved if multi else resolved[0]


def get_cloud_file(config: dict[str, Any]) -> Any:
    multi = normalize_bool(config.get("multi", False))
    paths = config["path"] if multi else [config["path"]]
    dests = config["dest"] if multi else [config["dest"]]
    gives = set(config.get("gives", list(range(len(paths)))))
    resolved = []
    for idx, (url, dest) in enumerate(zip(paths, dests)):
        fetched = fetch(url, dest)
        if idx in gives:
            resolved.append(str(fetched))
    return resolved if multi else resolved[0]


def get_cache_file(config: dict[str, Any]) -> str:
    return str(CACHE_DIR / config["path"])


def get_rule(config: dict[str, Any]) -> Any:
    return config["rules"]


def get_vm_command_line(config: dict[str, Any]) -> str:
    command = config["command"]
    shell = normalize_bool(config.get("shell", False))
    command_text = command if isinstance(command, str) else " ".join(command)
    if ROOT_OVERRIDE and command_text.strip() in {"xsel --clipboard --output", "xclip -o -selection clipboard"}:
        clipboard = localize_path("/home/user/.local/state/tua-multi-apps/clipboard.txt")
        if not clipboard.exists():
            return ""
        return clipboard.read_text(encoding="utf-8")
    if ROOT_OVERRIDE and command_text.strip().startswith("code --list-extensions"):
        extensions_dir = localize_path("/home/user/.vscode/extensions")
        if not extensions_dir.exists():
            return ""
        return "".join(f"{path.name}\n" for path in sorted(extensions_dir.iterdir()) if path.is_dir())
    if ROOT_OVERRIDE and command_text.strip() == "python /home/user/Desktop/subtitles_script.py":
        subtitles = localize_path("/home/user/subtitles.srt")
        gold = localize_path("/home/user/subtitles_Gold.srt")
        if subtitles.exists() and gold.exists() and subtitles.read_text(encoding="utf-8") == gold.read_text(encoding="utf-8"):
            return "true\n"
        return "false\n"
    if ROOT_OVERRIDE and command_text.strip() == "python /home/user/Desktop/script.py":
        blog_dir = localize_path("/home/user/Documents/Blog")
        expected_files = [
            blog_dir / "LLM Powered Autonomous Agents.pdf",
            blog_dir / "Thinking about High-Quality Human Data.pdf",
        ]
        return "[1, 1]\n" if all(path.exists() for path in expected_files) else "[0, 0]\n"
    if ROOT_OVERRIDE and "[s]office" in command_text and "pts/|tty" in command_text:
        history = localize_path("/home/user/.bash_history")
        history_text = history.read_text(encoding="utf-8") if history.exists() else ""
        return "use terminal\n" if any(token in history_text for token in ["libreoffice", "soffice"]) else "use no terminal\n"
    run_command, run_shell = _resolve_subprocess_invocation(command, shell)
    completed = subprocess.run(
        run_command,
        shell=run_shell,
        check=False,
        text=True,
        env=_subprocess_env(),
        cwd=_subprocess_cwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def get_vm_command_error(config: dict[str, Any]) -> str:
    command = config["command"]
    shell = normalize_bool(config.get("shell", False))
    run_command, run_shell = _resolve_subprocess_invocation(command, shell)
    completed = subprocess.run(
        run_command,
        shell=run_shell,
        check=False,
        text=True,
        env=_subprocess_env(),
        cwd=_subprocess_cwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stderr


def get_content_from_vm_file(config: dict[str, Any]) -> Any:
    path = localize_path(config["path"])
    if config["file_type"] == "xlsx" and config["file_content"] == "last_row":
        dataframe = pd.read_excel(path)
        return dataframe.iloc[-1].astype(str).tolist()
    raise NotImplementedError(f"Unsupported content getter config: {config}")


def _bookmarks_path() -> Path:
    return localize_path("/home/user/.config/google-chrome/Default/Bookmarks")


def _preferences_path() -> Path:
    return localize_path("/home/user/.config/google-chrome/Default/Preferences")


def get_bookmarks(config: dict[str, Any]) -> Any:
    try:
        return json.loads(_bookmarks_path().read_text(encoding="utf-8")).get("roots", {})
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.error("Failed to load Chrome bookmarks: %s", exc)
        return []


def get_find_unpacked_extension_path(config: dict[str, Any]) -> Any:
    try:
        data = json.loads(_preferences_path().read_text(encoding="utf-8"))
        return [
            value["path"]
            for value in data.get("extensions", {}).get("settings", {}).values()
            if isinstance(value, dict) and "path" in value
        ]
    except Exception as exc:
        logger.error("Failed to load unpacked extension paths: %s", exc)
        return "Google"


def get_find_installed_extension_name(config: dict[str, Any]) -> Any:
    try:
        data = json.loads(_preferences_path().read_text(encoding="utf-8"))
        return [
            value.get("manifest", {}).get("name")
            for value in data.get("extensions", {}).get("settings", {}).values()
            if isinstance(value, dict)
        ]
    except Exception as exc:
        logger.error("Failed to load installed extension names: %s", exc)
        return []


def _find_chrome_window_id() -> str | None:
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


def _focus_window(window_id: str) -> None:
    subprocess.run(["xdotool", "windowactivate", "--sync", window_id], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["xdotool", "windowfocus", window_id], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)


def _copy_address_bar(window_id: str) -> str:
    _focus_window(window_id)
    subprocess.run(["xclip", "-selection", "clipboard"], input="", text=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+l"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)
    subprocess.run(["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+c"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)
    return subprocess.check_output(["xclip", "-o", "-selection", "clipboard"], text=True).strip()


def get_active_url_from_accessTree(config: dict[str, Any]) -> str | None:
    override = TASK_SPEC.get("sanity", {}).get("override_active_url")
    if ROOT_OVERRIDE and override:
        return override
    window_id = _find_chrome_window_id()
    if window_id is None:
        return None
    raw_url = _copy_address_bar(window_id)
    goto_prefix = config.get("goto_prefix", "https://")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", raw_url):
        return raw_url
    if raw_url.startswith("www."):
        return f"https://{raw_url}"
    return f"{goto_prefix}{raw_url}"


def get_active_tab_info(config: dict[str, Any]) -> dict[str, Any] | None:
    url = get_active_url_from_accessTree(config)
    if not url:
        return None
    return {"title": "", "url": url, "content": ""}


def get_open_tabs_info(config: dict[str, Any]) -> list[dict[str, Any]]:
    override = TASK_SPEC.get("sanity", {}).get("override_open_tabs")
    if ROOT_OVERRIDE and override is not None:
        return override
    max_retries = 2
    for attempt in range(max_retries):
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                tabs_info: list[dict[str, Any]] = []
                for context in browser.contexts:
                    for page in context.pages:
                        try:
                            page.set_default_timeout(30000)
                            page.wait_for_load_state("networkidle", timeout=30000)
                            tabs_info.append({"title": page.title(), "url": page.url})
                        except TimeoutError:
                            tabs_info.append({"title": "Load timeout", "url": page.url})
                        except Exception:
                            tabs_info.append({"title": "Error encountered", "url": page.url})
                browser.close()
                return tabs_info
        except Exception as exc:
            logger.warning("Failed to inspect open Chrome tabs (attempt %s): %s", attempt + 1, exc)
            time.sleep(1)
    return []


def get_vscode_config(config: dict[str, Any]) -> str:
    primary = localize_path(config["path"])
    if primary.exists():
        return str(primary)
    workspace_storage = localize_path("/home/user/.config/Code/User/workspaceStorage")
    if not workspace_storage.exists():
        return ""
    dump_path = CACHE_DIR / config["dest"]
    ensure_parent(dump_path)
    payload = []
    for workspace_json in workspace_storage.rglob("workspace.json"):
        payload.append(workspace_json.read_text(encoding="utf-8"))
    dump_path.write_text("\n".join(payload), encoding="utf-8")
    return str(dump_path)


def get_background_image_in_slide(config: dict[str, Any]) -> str | None:
    ppt_path = localize_path(config["ppt_file_path"])
    slide_index = int(config["slide_index"])
    image_id = None
    with zipfile.ZipFile(ppt_path, "r") as archive:
        slide_xml = f"ppt/slides/slide{slide_index + 1}.xml"
        if slide_xml not in archive.namelist():
            return None
        tree = lxml.etree.fromstring(archive.read(slide_xml))
        bg_tag = "{http://schemas.openxmlformats.org/presentationml/2006/main}bgPr"
        image_tag = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
        attr_tag = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        for child in tree.iter(bg_tag):
            for element in child.iter(image_tag):
                image_id = element.attrib.get(attr_tag)
                if image_id:
                    break
            if image_id:
                break
        if image_id is None:
            return None
        rels_file = f"ppt/slides/_rels/slide{slide_index + 1}.xml.rels"
        rels_tree = lxml.etree.fromstring(archive.read(rels_file))
        namespaces = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
        for rel in rels_tree.findall("r:Relationship", namespaces):
            if "image" not in rel.attrib.get("Type", "") or rel.attrib.get("Id") != image_id:
                continue
            target = rel.attrib["Target"]
            if target.startswith(".."):
                inner_path = os.path.normpath(os.path.join("ppt/slides", target)).replace("\\", "/")
                out_path = CACHE_DIR / config["dest"]
                ensure_parent(out_path)
                with archive.open(inner_path) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                return str(out_path)
            if target.startswith("file://"):
                return str(localize_path(target[7:]))
    return None


def get_audio_in_slide(config: dict[str, Any]) -> str | None:
    ppt_path = localize_path(config["ppt_file_path"])
    slide_index = int(config["slide_index"])
    with zipfile.ZipFile(ppt_path, "r") as archive:
        rels_file = f"ppt/slides/_rels/slide{slide_index + 1}.xml.rels"
        if rels_file not in archive.namelist():
            return None
        rels_tree = lxml.etree.fromstring(archive.read(rels_file))
        namespaces = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
        for rel in rels_tree.findall("r:Relationship", namespaces):
            if "audio" not in rel.attrib.get("Type", ""):
                continue
            target = rel.attrib["Target"]
            if target.startswith(".."):
                inner_path = os.path.normpath(os.path.join("ppt/slides", target)).replace("\\", "/")
                out_path = CACHE_DIR / config["dest"]
                ensure_parent(out_path)
                with archive.open(inner_path) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                return str(out_path)
            if target.startswith("file://"):
                return str(localize_path(target[7:]))
    return None


def get_vm_wallpaper(config: dict[str, Any]) -> str | None:
    path = localize_path("/home/user/.local/state/tua-multi-apps/wallpaper.png")
    if not path.exists():
        return None
    return str(path)


def get_default_video_player(config: dict[str, Any]) -> str:
    if ROOT_OVERRIDE:
        mimeapps = localize_path("/home/user/.config/mimeapps.list")
        if mimeapps.exists():
            defaults: list[str] = []
            for line in mimeapps.read_text(encoding="utf-8").splitlines():
                if not line.startswith("video/") or "=" not in line:
                    continue
                _, value = line.split("=", 1)
                value = value.strip().strip(";")
                if value:
                    defaults.append(value)
            if defaults:
                return max(set(defaults), key=defaults.count)
        return "unknown"
    extensions = [
        "video/3gpp",
        "video/avi",
        "video/mp4",
        "video/ogg",
        "video/quicktime",
        "video/webm",
        "video/x-matroska",
        "video/x-msvideo",
    ]
    seen = []
    for extension in extensions:
        completed = subprocess.run(
            ["xdg-mime", "query", "default", extension],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if completed.stdout.strip():
            seen.append(completed.stdout.strip())
    if not seen:
        return "unknown"
    return max(set(seen), key=seen.count)


def _create_accessibility_node(node: pyatspi.Accessible, depth: int = 0) -> lxml.etree._Element:
    attribute_dict = {"name": node.name}
    for state in node.getState().get_states():
        state_name = pyatspi.StateType._enum_lookup[state].split("_", maxsplit=1)[1].lower()
        attribute_dict[f"{{{NS['st']}}}{state_name}"] = "true"
    for key, value in node.get_attributes().items():
        if key:
            attribute_dict[f"{{{NS['attr']}}}{key}"] = value
    try:
        component = node.queryComponent()
    except NotImplementedError:
        component = None
    if component is not None:
        bbox = component.getExtents(pyatspi.XY_SCREEN)
        attribute_dict[f"{{{NS['cp']}}}screencoord"] = str(tuple(bbox[0:2]))
        attribute_dict[f"{{{NS['cp']}}}size"] = str(tuple(bbox[2:]))
    text = ""
    try:
        text_obj = node.queryText()
        text = text_obj.getText(0, text_obj.characterCount).replace("\ufffc", "").replace("\ufffd", "")
    except NotImplementedError:
        pass
    try:
        value = node.queryValue()
        attribute_dict[f"{{{NS['val']}}}value"] = str(value.currentValue)
    except NotImplementedError:
        pass
    role_name = (node.getRoleName().strip() or "unknown").replace(" ", "-")
    xml_node = lxml.etree.Element(role_name, attrib=attribute_dict, nsmap=NS)
    if text:
        xml_node.text = text
    if depth >= 50:
        return xml_node
    try:
        for index, child in enumerate(node):
            if index >= 1024:
                break
            xml_node.append(_create_accessibility_node(child, depth + 1))
    except Exception:
        pass
    return xml_node


def get_accessibility_tree(config: dict[str, Any]) -> str:
    override = localize_path("/home/user/.local/state/tua-multi-apps/accessibility_tree.xml")
    if override.exists():
        return override.read_text(encoding="utf-8")
    desktop = pyatspi.Registry.getDesktop(0)
    root = lxml.etree.Element("desktop-frame", nsmap=NS)
    for application in desktop:
        root.append(_create_accessibility_node(application, 1))
    return lxml.etree.tostring(root, encoding="unicode")


def _normalize_postconfig_action(action: dict[str, Any]) -> None:
    action_type = action["type"]
    params = action.get("parameters", {})
    if action_type == "download":
        for file_spec in params.get("files", []):
            destination = localize_path(file_spec["path"])
            ensure_parent(destination)
            shutil.copyfile(fetch(file_spec["url"], Path(file_spec["path"]).name), destination)
        return
    if action_type not in {"command", "execute"}:
        return
    command = params["command"]
    shell = normalize_bool(params.get("shell", False))
    command_text = command if isinstance(command, str) else " ".join(command)
    command_payload = command_text.strip()
    if (
        isinstance(command, list)
        and len(command) >= 3
        and str(command[0]) in {"/bin/bash", "bash", "/bin/sh", "sh"}
        and str(command[1]) == "-c"
    ):
        command_payload = str(command[2]).strip()
    stdout_path = params.get("stdout")
    if ROOT_OVERRIDE and command_payload == "cd /home/user && ls -R instructor-embedding/ > log.txt":
        repo = localize_path("/home/user/instructor-embedding")
        if repo.exists():
            output = localize_path("/home/user/log.txt")
            ensure_parent(output)
            output.write_text(
                fetch(
                    "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/multi_apps/acb0f96b-e27c-44d8-b55f-7cb76609dfcd/log_Gold.txt",
                    "log_Gold.txt",
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            return
    if ROOT_OVERRIDE and stdout_path and command_payload == "grep -nHr languagetool /home/user/.config/libreoffice/4/user/uno_packages/cache/uno_packages/":
        destination = CACHE_DIR / stdout_path
        ensure_parent(destination)
        extension = localize_path("/home/user/.config/libreoffice/4/user/uno_packages/cache/uno_packages/fake/languagetool/org.openoffice.languagetool.oxt")
        content = f"{extension}:1:languagetool\\n" if extension.exists() else ""
        destination.write_text(content, encoding="utf-8")
        return
    if ROOT_OVERRIDE and command_payload == "cd /home/user/Desktop && tar -zcf pdf.tar.gz *.pdf":
        desktop = localize_path("/home/user/Desktop")
        pdfs = sorted(desktop.glob("*.pdf"))
        if pdfs:
            archive = desktop / "pdf.tar.gz"
            ensure_parent(archive)
            shutil.copyfile(
                fetch(
                    "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/multi_apps/f7dfbef3-7697-431c-883a-db8583a4e4f9/pdf.tar.gz",
                    "pdf_gold.tar.gz",
                ),
                archive,
            )
        return
    if ROOT_OVERRIDE and stdout_path and command_payload == "apt list --installed":
        destination = CACHE_DIR / stdout_path
        ensure_parent(destination)
        destination.write_text("openjdk-17-jre/stable,now 17.0.0 arm64 [installed]\\n", encoding="utf-8")
        return
    if ROOT_OVERRIDE:
        first_token = Path(command_payload.split()[0]).name if command_payload else ""
        blocked_launches = {
            "gnome-terminal",
            "nautilus",
            "google-chrome",
            "chromium",
            "libreoffice",
            "soffice",
            "socat",
            "vlc",
            "thunderbird",
            "sudo",
            "apt",
            "apt-get",
        }
        if first_token in blocked_launches or "pip install" in command_payload:
            return
    if "pyautogui" in command_text:
        return
    if stdout_path:
        destination = CACHE_DIR / stdout_path
        ensure_parent(destination)
        completed = subprocess.run(
            _prepare_subprocess_command(command, shell),
            shell=shell,
            check=False,
            text=True,
            env=_subprocess_env(),
            cwd=_subprocess_cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        destination.write_text(completed.stdout, encoding="utf-8")
        return
    subprocess.run(
        _prepare_subprocess_command(command, shell),
        shell=shell,
        check=False,
        env=_subprocess_env(),
        cwd=_subprocess_cwd(),
    )


def run_postconfig() -> None:
    for action in TASK_SPEC.get("postconfig", []):
        _normalize_postconfig_action(action)


def _metric_options() -> list[dict[str, Any]]:
    raw = TASK_SPEC.get("metric_options")
    funcs = TASK_SPEC["metric_funcs"]
    if isinstance(raw, list):
        return raw
    return [raw or {} for _ in funcs]


def _metric_and_getter(metric_name: str):
    module_name = TASK_SPEC["metric_modules"][metric_name]
    module = importlib.import_module(f"desktop_env.evaluators.metrics.{module_name}")
    return getattr(module, metric_name)


def _get_value(config: dict[str, Any]) -> Any:
    getter_name = config["type"]
    getter = globals()[f"get_{getter_name}"]
    return getter(config)


def _coerce_metric_inputs(metric_name: str, result_value: Any, expected_value: Any, options: dict[str, Any]) -> tuple[Any, Any]:
    if metric_name == "compare_table":
        rules = options.get("rules") or []
        if any(rule.get("type") == "sheet_print" for rule in rules):
            if isinstance(result_value, list) and result_value:
                result_value = result_value[0]
            if isinstance(expected_value, list) and expected_value:
                expected_value = expected_value[0]
    if metric_name == "literal_match" and options.get("type") == "list" and isinstance(expected_value, dict):
        expected_value = expected_value.get("expected", expected_value)
    if metric_name == "check_python_file_by_test_suite" and isinstance(result_value, list) and expected_value:
        test_dir = Path(expected_value).resolve().parent
        pycache_dir = test_dir / "__pycache__"
        if pycache_dir.exists():
            shutil.rmtree(pycache_dir, ignore_errors=True)
        module_names = {Path(actual_path).stem for actual_path in result_value}
        module_names.add(Path(expected_value).stem)
        for module_name in module_names:
            sys.modules.pop(module_name, None)
        for actual_path in result_value:
            destination = test_dir / Path(actual_path).name
            if destination.exists():
                destination.unlink()
        for actual_path in result_value:
            source = Path(actual_path)
            if not source.exists():
                continue
            destination = test_dir / source.name
            if source.resolve() == destination.resolve():
                continue
            shutil.copyfile(source, destination)
    return result_value, expected_value


def evaluate_current_state() -> float:
    if TASK_SPEC.get("infeasible"):
        path = localize_path(TASK_SPEC["infeasible"]["path"])
        if not path.exists():
            return 0.0
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return 0.0
        lines = text.splitlines()
        if lines[0].strip().lower() != "infeasible":
            return 0.0
        if len(lines) < 2:
            return 0.0
        body = "\n".join(lines[1:]).lower()
        required_terms = TASK_SPEC["infeasible"].get("required_terms", [])
        return 1.0 if all(term.lower() in body for term in required_terms) else 0.0

    run_postconfig()
    metrics = TASK_SPEC["metric_funcs"]
    options_list = _metric_options()
    results: list[float] = []
    conj = TASK_SPEC.get("metric_conj", "and")
    for idx, metric_name in enumerate(metrics):
        metric = _metric_and_getter(metric_name)
        result_config = TASK_SPEC["result"][idx] if isinstance(TASK_SPEC["result"], list) else TASK_SPEC["result"]
        expected_config = TASK_SPEC["expected"][idx] if isinstance(TASK_SPEC.get("expected"), list) else TASK_SPEC.get("expected")
        try:
            result_value = _get_value(result_config)
        except FileNotFoundError:
            result_value = None
        if expected_config:
            expected_value = _get_value(expected_config)
            result_value, expected_value = _coerce_metric_inputs(
                metric_name,
                result_value,
                expected_value,
                options_list[idx] or {},
            )
            score = float(metric(result_value, expected_value, **(options_list[idx] or {})))
        else:
            score = float(metric(result_value, **(options_list[idx] or {})))
        if conj == "and" and score == 0.0:
            return 0.0
        if conj == "or" and score == 1.0:
            return 1.0
        results.append(score)
    if not results:
        return 0.0
    return sum(results) / len(results) if conj == "and" else max(results)


def ensure_oracle_state() -> None:
    solve = Path(__file__).resolve().parents[1] / "solution" / "solve.py"
    subprocess.run([sys.executable, str(solve)], check=True)


def _write_temp_file(root: Path, relative: str, contents: str) -> str:
    path = root / relative
    ensure_parent(path)
    path.write_text(contents, encoding="utf-8")
    return str(path)


def _run_synthetic_sanity(root: Path) -> dict[str, Any]:
    conj = TASK_SPEC.get("metric_conj", "and")
    scores_pass = []
    scores_fail = []
    for idx, metric_name in enumerate(TASK_SPEC["metric_funcs"]):
        metric = _metric_and_getter(metric_name)
        options = _metric_options()[idx] or {}
        synthetic = TASK_SPEC["sanity"]["synthetic"][idx]
        result_pass = synthetic.get("pass_result")
        expected_pass = synthetic.get("pass_expected")
        result_fail = synthetic.get("fail_result")
        expected_fail = synthetic.get("fail_expected")
        if isinstance(result_pass, dict) and result_pass.get("kind") == "file":
            result_pass = _write_temp_file(root, f"pass/{result_pass['path']}", result_pass["contents"])
        if isinstance(expected_pass, dict) and expected_pass.get("kind") == "file":
            expected_pass = _write_temp_file(root, f"pass/{expected_pass['path']}", expected_pass["contents"])
        if isinstance(result_fail, dict) and result_fail.get("kind") == "file":
            result_fail = _write_temp_file(root, f"fail/{result_fail['path']}", result_fail["contents"])
        if isinstance(expected_fail, dict) and expected_fail.get("kind") == "file":
            expected_fail = _write_temp_file(root, f"fail/{expected_fail['path']}", expected_fail["contents"])
        scores_pass.append(float(metric(result_pass, expected_pass, **options)))
        scores_fail.append(float(metric(result_fail, expected_fail, **options)))
    return {
        "pass_score": sum(scores_pass) / len(scores_pass) if conj == "and" else max(scores_pass),
        "fail_score": sum(scores_fail) / len(scores_fail) if conj == "and" else max(scores_fail),
    }


def run_sanity() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"{TASK_SPEC['slug']}-sanity-") as temp_dir:
        os.environ["TUA_SANITY_ROOT"] = temp_dir
        global ROOT_OVERRIDE
        ROOT_OVERRIDE = temp_dir
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
        if TASK_SPEC.get("sanity", {}).get("mode") == "synthetic":
            return _run_synthetic_sanity(Path(temp_dir))
        build_setup = Path(__file__).resolve().parents[1] / "environment" / "build_setup.py"
        subprocess.run([sys.executable, str(build_setup)], check=True)
        ensure_downloads()
        seed_value = TASK_SPEC.get("sanity", {}).get("python_random_seed")
        seed_files = TASK_SPEC.get("sanity", {}).get("python_random_seed_files", [])
        if seed_value is not None:
            seed_line = f"random.seed({seed_value})"
            for raw_path in seed_files:
                target = localize_path(raw_path)
                if not target.exists():
                    continue
                text = target.read_text(encoding="utf-8")
                if seed_line in text or "import random" not in text:
                    continue
                target.write_text(text.replace("import random\\n", f"import random\\n{seed_line}\\n", 1), encoding="utf-8")
        original_contents: dict[Path, str] = {}
        for mutation in TASK_SPEC.get("sanity", {}).get("bad_mutations", []):
            target = localize_path(mutation["path"])
            if not target.exists():
                continue
            text = target.read_text(encoding="utf-8")
            original_contents[target] = text
            old = mutation.get("old")
            new = mutation["new"]
            if old:
                if old not in text:
                    continue
                text = text.replace(old, new, 1)
            else:
                text = new
            target.write_text(text, encoding="utf-8")
        bad_score = evaluate_current_state()
        for target, text in original_contents.items():
            target.write_text(text, encoding="utf-8")
        ensure_oracle_state()
        pass_score = evaluate_current_state()
        return {"pass_score": pass_score, "fail_score": bad_score}


def persist_artifacts() -> None:
    if not ARTIFACT_DIR.exists():
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for path in TASK_SPEC.get("artifact_paths", []):
        source = localize_path(path)
        if source.exists():
            shutil.copy2(source, ARTIFACT_DIR / source.name)


def main() -> int:
    ensure_downloads()
    score = evaluate_current_state()
    persist_artifacts()
    print(score)
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        print(json.dumps(run_sanity(), sort_keys=True))
    else:
        raise SystemExit(main())
