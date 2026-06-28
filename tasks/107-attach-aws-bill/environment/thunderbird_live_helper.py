#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
import concurrent.futures
import configparser
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import lxml.etree
import pyatspi
from lxml.cssselect import CSSSelector
from pyatspi import Accessible, STATE_SHOWING, Action as ATAction
from pyatspi import Component, StateType, Text as ATText, Value as ATValue


THUNDERBIRD_ROOT = Path.home() / ".thunderbird"
THUNDERBIRD_BIN = os.environ.get("TUA_THUNDERBIRD_BIN") or shutil.which("thunderbird") or "/usr/bin/thunderbird"
THUNDERBIRD_EXECUTABLES = {"crashhelper", "thunderbird", "thunderbird-bin"}
MAX_DEPTH = 50
MAX_WIDTH = 1024
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

ABOUT_PROFILES_RULE = [
    {
        "selectors": [
            'application[name=Thunderbird] page-tab-list[attr|id="tabmail-tabs"]>page-tab[name="About Profiles"]'
        ]
    }
]

LOGIN_RULES = [
    {
        "xpath": "//application[@name='Thunderbird']//*[contains(text(), 'anonym-x2024@outlook.com') or contains(@name, 'anonym-x2024@outlook.com')]"
    },
    {
        "xpath": "//application[@name='Thunderbird']//*[contains(@name, 'password') or contains(@name, 'Password')]"
    },
]


def resolve_profile_dir() -> Path:
    ini_path = THUNDERBIRD_ROOT / "profiles.ini"
    config = configparser.ConfigParser(interpolation=None)
    config.read(ini_path, encoding="utf-8")

    for section_name in config.sections():
        if not section_name.startswith("Install"):
            continue
        default_path = config[section_name].get("Default")
        if default_path:
            return THUNDERBIRD_ROOT / default_path

    for section_name in config.sections():
        if section_name.startswith("Profile") and config[section_name].get("Default") == "1":
            if config[section_name].get("IsRelative", "1") == "1":
                return THUNDERBIRD_ROOT / config[section_name]["Path"]
            return Path(config[section_name]["Path"]).expanduser()

    raise RuntimeError(f"Could not resolve Thunderbird profile from {ini_path}")


def cleanup_profile_locks(profile_dir: Path) -> None:
    for filename in ("lock", ".parentlock"):
        try:
            (profile_dir / filename).unlink()
        except FileNotFoundError:
            pass


def thunderbird_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/tua-dbus-session")
    env.setdefault("XDG_RUNTIME_DIR", f"/tmp/xdg-runtime-{os.getuid()}")
    env.setdefault("GNOME_ACCESSIBILITY", "1")
    env.setdefault("GTK_MODULES", "gail:atk-bridge")
    env.setdefault("MOZ_ENABLE_WAYLAND", "0")
    return env


def thunderbird_pids() -> list[int]:
    # Inspect /proc/<pid>/exe so helper commands don't match their own argv text.
    result = subprocess.run(
        ["ps", "-eo", "pid="],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    pids: list[int] = []
    current_pid = os.getpid()
    for raw_pid in result.stdout.split():
        try:
            pid = int(raw_pid)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        try:
            exe_name = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            continue
        if exe_name in THUNDERBIRD_EXECUTABLES:
            pids.append(pid)
    return pids


def kill_thunderbird() -> None:
    for pid in thunderbird_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + 15
    while time.time() < deadline:
        if not thunderbird_pids():
            cleanup_profile_locks(resolve_profile_dir())
            return
        time.sleep(0.5)
    for pid in thunderbird_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if not thunderbird_pids():
        cleanup_profile_locks(resolve_profile_dir())
        return
    raise RuntimeError("Timed out waiting for Thunderbird to exit")


def wait_for_window(title_fragment: str | None = None, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        commands = []
        if title_fragment:
            commands.append(["xdotool", "search", "--onlyvisible", "--name", title_fragment])
        else:
            commands.extend(
                [
                    ["xdotool", "search", "--onlyvisible", "--class", "thunderbird"],
                    ["xdotool", "search", "--onlyvisible", "--name", "Thunderbird"],
                ]
            )
        for command in commands:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for Thunderbird window state")


def _create_atspi_node(node: Accessible, depth: int = 0, flag: str | None = None):
    attribute_dict = {"name": node.name}

    states = node.getState().get_states()
    for st in states:
        state_name = StateType._enum_lookup[st].split("_", maxsplit=1)[1].lower()
        if state_name:
            attribute_dict[f"{{{NS['st']}}}{state_name}"] = "true"

    for attribute_name, attribute_value in node.get_attributes().items():
        if attribute_name:
            attribute_dict[f"{{{NS['attr']}}}{attribute_name}"] = attribute_value

    if (
        attribute_dict.get(f"{{{NS['st']}}}visible") == "true"
        and attribute_dict.get(f"{{{NS['st']}}}showing") == "true"
    ):
        try:
            component: Component = node.queryComponent()
        except NotImplementedError:
            pass
        else:
            bbox = component.getExtents(pyatspi.XY_SCREEN)
            attribute_dict[f"{{{NS['cp']}}}screencoord"] = str(tuple(bbox[0:2]))
            attribute_dict[f"{{{NS['cp']}}}size"] = str(tuple(bbox[2:]))

    text = ""
    try:
        text_obj: ATText = node.queryText()
        text = text_obj.getText(0, text_obj.characterCount).replace("\ufffc", "").replace("\ufffd", "")
    except NotImplementedError:
        pass

    try:
        node.queryImage()
        attribute_dict["image"] = "true"
    except NotImplementedError:
        pass

    try:
        node.querySelection()
        attribute_dict["selection"] = "true"
    except NotImplementedError:
        pass

    try:
        value: ATValue = node.queryValue()
        for attr_name, getter in [
            ("value", lambda: value.currentValue),
            ("min", lambda: value.minimumValue),
            ("max", lambda: value.maximumValue),
            ("step", lambda: value.minimumIncrement),
        ]:
            try:
                attribute_dict[f"{{{NS['val']}}}{attr_name}"] = str(getter())
            except Exception:
                pass
    except NotImplementedError:
        pass

    try:
        action: ATAction = node.queryAction()
        for index in range(action.nActions):
            action_name = action.getName(index).replace(" ", "-")
            attribute_dict[f"{{{NS['act']}}}{action_name}_desc"] = action.getDescription(index)
            attribute_dict[f"{{{NS['act']}}}{action_name}_kb"] = action.getKeyBinding(index)
    except NotImplementedError:
        pass

    raw_role_name = node.getRoleName().strip()
    role_name = (raw_role_name or "unknown").replace(" ", "-")
    if not flag and raw_role_name == "application" and node.name == "Thunderbird":
        flag = "thunderbird"

    xml_node = lxml.etree.Element(role_name, attrib=attribute_dict, nsmap=NS)
    if text:
        xml_node.text = text

    if depth == MAX_DEPTH:
        return xml_node

    try:
        for index, child in enumerate(node):
            if index == MAX_WIDTH:
                break
            xml_node.append(_create_atspi_node(child, depth + 1, flag))
    except Exception:
        pass

    return xml_node


def get_accessibility_tree() -> str:
    desktop = pyatspi.Registry.getDesktop(0)
    root = lxml.etree.Element("desktop-frame", nsmap=NS)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_create_atspi_node, app_node, 1) for app_node in desktop]
        for future in concurrent.futures.as_completed(futures):
            root.append(future.result())
    tree = lxml.etree.tostring(root, encoding="unicode")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return tree


def check_accessibility_tree(result: str, rules):
    a11y_ns_map = {"ubuntu": NS}
    at = lxml.etree.fromstring(result)
    for rule in rules:
        if "xpath" in rule:
            elements = at.xpath(rule["xpath"], namespaces=a11y_ns_map["ubuntu"])
        else:
            selector = CSSSelector(", ".join(rule["selectors"]), namespaces=a11y_ns_map["ubuntu"])
            elements = selector(at)
        if len(elements) == 0:
            return 0.0
    return 1.0


def launch_thunderbird(*extra_args: str) -> None:
    profile_dir = resolve_profile_dir()
    cleanup_profile_locks(profile_dir)
    command = [THUNDERBIRD_BIN, "-profile", str(profile_dir), *extra_args]
    with open("/tmp/thunderbird-live-helper.log", "a", encoding="utf-8") as log_file:
        subprocess.Popen(command, stdout=log_file, stderr=log_file, env=thunderbird_env())
    wait_for_window()
    time.sleep(5)


def activate_any_thunderbird_window() -> None:
    result = None
    for command in (
        ["xdotool", "search", "--onlyvisible", "--class", "thunderbird"],
        ["xdotool", "search", "--onlyvisible", "--name", "Thunderbird"],
    ):
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            break
    if result is None or result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Could not find a visible Thunderbird window")
    window_id = result.stdout.strip().splitlines()[0]
    subprocess.run(["xdotool", "windowactivate", "--sync", window_id], check=True)
    time.sleep(1)


def fill_login(name: str, email: str, password: str) -> int:
    activate_any_thunderbird_window()
    subprocess.run(["xdotool", "key", "ctrl+a"], check=False)
    subprocess.run(["xdotool", "type", "--delay", "40", name], check=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "key", "Tab"], check=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "type", "--delay", "40", email], check=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "key", "Tab"], check=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "type", "--delay", "40", password], check=True)
    time.sleep(1)

    deadline = time.time() + 10
    while time.time() < deadline:
        if check_accessibility_tree(get_accessibility_tree(), LOGIN_RULES) == 1.0:
            return 0
        time.sleep(1)
    return 1


def open_about_profiles() -> int:
    kill_thunderbird()
    candidates = [
        ["-contentTab", "about:profiles"],
        ["about:profiles"],
    ]
    for extra_args in candidates:
        launch_thunderbird(*extra_args)
        deadline = time.time() + 10
        while time.time() < deadline:
            if check_accessibility_tree(get_accessibility_tree(), ABOUT_PROFILES_RULE) == 1.0:
                return 0
            time.sleep(1)
        kill_thunderbird()
    return 1


def resolve_compose_body() -> str:
    if os.environ.get("THUNDERBIRD_COMPOSE_BODY"):
        return os.environ["THUNDERBIRD_COMPOSE_BODY"]

    body_path = os.environ.get("THUNDERBIRD_COMPOSE_BODY_FILE")
    if not body_path:
        return ""

    body_file = Path(body_path).expanduser()
    if not body_file.exists():
        return ""
    return body_file.read_text(encoding="utf-8").rstrip("\n")


def format_compose_field(key: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"{key}='{escaped}'"


def attach_file(path: str, subject: str, sender: str, recipient: str) -> int:
    kill_thunderbird()
    attachment_uri = path
    if not attachment_uri.startswith("file://"):
        attachment_uri = f"file://{path}"
    compose_fields = [
        format_compose_field("from", sender),
        format_compose_field("to", recipient),
        format_compose_field("subject", subject),
    ]
    body = resolve_compose_body()
    if body:
        compose_fields.append(format_compose_field("body", body))
    compose_fields.append(format_compose_field("attachment", attachment_uri))
    compose_arg = ",".join(compose_fields)
    launch_thunderbird("-compose", compose_arg)
    wait_for_window(subject, timeout=15)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    fill_parser = subparsers.add_parser("fill-login")
    fill_parser.add_argument("--name", required=True)
    fill_parser.add_argument("--email", required=True)
    fill_parser.add_argument("--password", required=True)

    subparsers.add_parser("open-about-profiles")

    attach_parser = subparsers.add_parser("attach-file")
    attach_parser.add_argument("--path", required=True)
    attach_parser.add_argument("--subject", required=True)
    attach_parser.add_argument("--from", dest="sender", required=True)
    attach_parser.add_argument("--to", dest="recipient", required=True)

    args = parser.parse_args(argv[1:])

    if args.command == "fill-login":
        return fill_login(args.name, args.email, args.password)
    if args.command == "open-about-profiles":
        return open_about_profiles()
    if args.command == "attach-file":
        return attach_file(args.path, args.subject, args.sender, args.recipient)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
