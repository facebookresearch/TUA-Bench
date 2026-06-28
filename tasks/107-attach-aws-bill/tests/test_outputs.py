# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from pathlib import Path

import lxml.etree
from lxml.cssselect import CSSSelector

RULES = {'expect': ['Attachment added!']}
SUBJECT = 'New-month AWS Bill'
ATTACHMENT_NAME = 'aws-bill.pdf'

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


def check_list(result: str, rules):
    import re

    if result is None:
        return 0.0

    expect_patterns = [re.compile(pattern) for pattern in rules.get("expect", [])]
    expect_metrics = [False] * len(expect_patterns)
    with open(result, encoding="utf-8") as handle:
        for line in handle:
            for index, pattern in enumerate(expect_patterns):
                expect_metrics[index] = expect_metrics[index] or (pattern.search(line) is not None)
    return float(all(expect_metrics))


def _create_node(node: Accessible, depth: int = 0):
    import pyatspi
    from pyatspi import Accessible, Component, StateType, Text as ATText, Value as ATValue, Action as ATAction

    attribute_dict = {"name": node.name}
    for state in node.getState().get_states():
        state_name = StateType._enum_lookup[state].split("_", maxsplit=1)[1].lower()
        if state_name:
            attribute_dict[f"{{{NS['st']}}}{state_name}"] = "true"
    for key, value in node.get_attributes().items():
        if key:
            attribute_dict[f"{{{NS['attr']}}}{key}"] = value
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
        value: ATValue = node.queryValue()
        attribute_dict[f"{{{NS['val']}}}value"] = str(value.currentValue)
    except NotImplementedError:
        pass
    try:
        action: ATAction = node.queryAction()
        for index in range(action.nActions):
            name = action.getName(index).replace(" ", "-")
            attribute_dict[f"{{{NS['act']}}}{name}_desc"] = action.getDescription(index)
            attribute_dict[f"{{{NS['act']}}}{name}_kb"] = action.getKeyBinding(index)
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
            if index == 1024:
                break
            xml_node.append(_create_node(child, depth + 1))
    except Exception:
        pass
    return xml_node


def load_runtime_env():
    env_file = Path("/tmp/tua-env.sh")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line.startswith("export "):
                continue
            key, sep, value = line[len("export ") :].partition("=")
            if not sep or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[key] = value
    os.environ.setdefault("GNOME_ACCESSIBILITY", "1")
    os.environ.setdefault("GTK_MODULES", "gail:atk-bridge")


def record_tree_error(message: str) -> None:
    Path("/tmp/accessibility_tree_error.txt").write_text(f"{message.rstrip()}\n", encoding="utf-8")


def empty_tree(reason: str | None = None):
    if reason:
        record_tree_error(reason)
    root = lxml.etree.Element("desktop-frame", nsmap=NS)
    tree = lxml.etree.tostring(root, encoding="unicode")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return lxml.etree.fromstring(tree)


def dump_tree_xml() -> str:
    import pyatspi

    desktop = pyatspi.Registry.getDesktop(0)
    root = lxml.etree.Element("desktop-frame", nsmap=NS)
    for application in desktop:
        root.append(_create_node(application, 1))
    return lxml.etree.tostring(root, encoding="unicode")


def dump_tree_main() -> int:
    load_runtime_env()
    try:
        tree = dump_tree_xml()
    except Exception as exc:
        print(f"Failed to capture accessibility tree: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(tree)
    return 0


def get_tree():
    load_runtime_env()

    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--dump-tree"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        message = f"Failed to capture accessibility tree (exit {result.returncode})."
        if result.stderr.strip():
            message = f"{message}\n{result.stderr.strip()}"
        return empty_tree(message)

    tree = result.stdout.strip()
    if not tree:
        return empty_tree("Failed to capture accessibility tree: subprocess returned no XML output.")

    try:
        parsed = lxml.etree.fromstring(tree)
    except lxml.etree.XMLSyntaxError as exc:
        return empty_tree(f"Failed to parse accessibility tree XML: {exc}")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return parsed


def get_writer_window(tree, subject: str):
    exact_name = f"Write: {subject} - Thunderbird"
    prefix = f"Write: {subject}"
    fallback = None

    for application in tree.findall("./application"):
        if application.get("name") != "Thunderbird":
            continue
        for frame in application.findall("./frame"):
            frame_name = frame.get("name", "")
            if frame_name == exact_name:
                return frame
            if fallback is None and frame_name.startswith(prefix):
                fallback = frame
    return fallback


def expand_attachment_bucket(button) -> bool:
    screencoord = button.get(f"{{{NS['cp']}}}screencoord")
    size = button.get(f"{{{NS['cp']}}}size")
    if not screencoord or not size:
        return False

    x, y = ast.literal_eval(screencoord)
    width, height = ast.literal_eval(size)
    center_x = x + width // 2
    center_y = y + height // 2

    subprocess.run(
        ["xdotool", "mousemove", "--sync", str(center_x), str(center_y)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ["xdotool", "click", "1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return True


def check_attachment(subject: str, name: str) -> bool:
    item_name_prefix = " ".join(Path(name).stem.split()) + " .pdf"
    for _ in range(15):
        tree = get_tree()
        writer_window = get_writer_window(tree, subject)
        if writer_window is None:
            time.sleep(1)
            continue

        bucket_selector = CSSSelector(
            'panel[attr|id="attachmentArea"]>list-box[attr|id="attachmentBucket"]',
            namespaces=NS,
        )
        buckets = bucket_selector(writer_window)
        if not buckets:
            button_selector = CSSSelector(
                'panel[attr|id="attachmentArea"]>push-button[name*="Attachment"]',
                namespaces=NS,
            )
            buttons = button_selector(writer_window)
            if buttons and expand_attachment_bucket(buttons[0]):
                time.sleep(0.5)
                tree = get_tree()
                writer_window = get_writer_window(tree, subject)
                if writer_window is None:
                    time.sleep(1)
                    continue
                buckets = bucket_selector(writer_window)
        if buckets:
            item_selector = CSSSelector(f'list-item[name^="{item_name_prefix}"]', namespaces=NS)
            if item_selector(buckets[0]):
                return True
        time.sleep(1)
    return False


def run_evaluation():
    output_path = Path("/tmp/thunderbird-attachment-check.txt")
    if check_attachment(SUBJECT, ATTACHMENT_NAME):
        output_path.write_text("Attachment added!\n", encoding="utf-8")
    else:
        output_path.write_text("Attachment not detected!\n", encoding="utf-8")
    return check_list(str(output_path), RULES)


def run_sanity():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        good = Path(tmpdir) / "good.txt"
        bad = Path(tmpdir) / "bad.txt"
        good.write_text("Attachment added!\n", encoding="utf-8")
        bad.write_text("Attachment not detected!\n", encoding="utf-8")
        return {
            "fail_score": check_list(str(bad), RULES),
            "pass_score": check_list(str(good), RULES),
        }


def test_main():
    assert run_evaluation() == 1.0, "Thunderbird compose window does not contain the expected attachment"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        import json as _json

        print(_json.dumps(run_sanity(), sort_keys=True))
    elif len(sys.argv) > 1 and sys.argv[1] == "--dump-tree":
        raise SystemExit(dump_tree_main())
    else:
        print(run_evaluation())
