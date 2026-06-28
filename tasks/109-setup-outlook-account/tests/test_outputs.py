# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import lxml.etree
from lxml.cssselect import CSSSelector

RULES = [{'xpath': "//application[@name='Thunderbird']//*[contains(text(), 'anonym-x2024@outlook.com') or "
           "contains(@name, 'anonym-x2024@outlook.com')]"},
 {'xpath': "//application[@name='Thunderbird']//*[contains(@name, 'password') or contains(@name, "
           "'Password')]"}]
SANITY_FAIL_XML = ("<desktop-frame><application name='Thunderbird'><entry name='email'></entry><password-text "
 "name='Password'></password-text></application></desktop-frame>")
SANITY_PASS_XML = ("<desktop-frame><application name='Thunderbird'><entry "
 "name='email'>anonym-x2024@outlook.com</entry><password-text "
 "name='Password'></password-text></application></desktop-frame>")
CHECK_MESSAGE = 'Thunderbird account setup page does not satisfy the exact OSWorld accessibility-tree rule'

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


def check_accessibility_tree(result, rules, osname="ubuntu"):
    at = lxml.etree.fromstring(result)
    for rule in rules:
        if "xpath" in rule:
            elements = at.xpath(rule["xpath"], namespaces=NS)
        else:
            selector = CSSSelector(", ".join(rule["selectors"]), namespaces=NS)
            elements = selector(at)
        if len(elements) == 0:
            return 0.0
    return 1.0


def load_runtime_env():
    env_file = Path("/tmp/tua-env.sh")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line.startswith("export "):
                continue
            key, sep, value = line[len("export "):].partition("=")
            if not sep or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[key] = value
    os.environ.pop("NO_AT_BRIDGE", None)
    os.environ.setdefault("GNOME_ACCESSIBILITY", "1")
    os.environ.setdefault("GTK_MODULES", "gail:atk-bridge")


def record_tree_error(message: str) -> None:
    Path("/tmp/accessibility_tree_error.txt").write_text(f"{message.rstrip()}\n", encoding="utf-8")


def empty_tree(reason: str | None = None):
    if reason:
        record_tree_error(reason)
    tree = lxml.etree.tostring(lxml.etree.Element("desktop-frame", nsmap=NS), encoding="unicode")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return tree


def dump_tree_xml() -> str:
    import pyatspi
    from pyatspi import Accessible, Component, StateType, Text as ATText, Value as ATValue, Action as ATAction

    max_depth = 50
    max_width = 1024

    def _create_node(node: Accessible, depth: int = 0):
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
        if depth == max_depth:
            return xml_node
        try:
            for index, child in enumerate(node):
                if index == max_width:
                    break
                xml_node.append(_create_node(child, depth + 1))
        except Exception:
            pass
        return xml_node

    desktop = pyatspi.Registry.getDesktop(0)
    root = lxml.etree.Element("desktop-frame", nsmap=NS)
    for application in desktop:
        root.append(_create_node(application, 1))
    tree = lxml.etree.tostring(root, encoding="unicode")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return tree


def dump_tree_main() -> int:
    load_runtime_env()
    try:
        tree = dump_tree_xml()
    except Exception as exc:
        print(f"Failed to capture accessibility tree: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(tree)
    return 0


def get_tree_xml():
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
        lxml.etree.fromstring(tree)
    except lxml.etree.XMLSyntaxError as exc:
        return empty_tree(f"Failed to parse accessibility tree XML: {exc}")
    Path("/tmp/accessibility_tree.xml").write_text(tree, encoding="utf-8")
    return tree


def run_evaluation():
    for _ in range(15):
        score = check_accessibility_tree(get_tree_xml(), RULES)
        if score == 1.0:
            return 1.0
        time.sleep(1)
    return 0.0


def run_sanity():
    return {
        "fail_score": check_accessibility_tree(SANITY_FAIL_XML, RULES),
        "pass_score": check_accessibility_tree(SANITY_PASS_XML, RULES),
    }


def test_main():
    assert run_evaluation() == 1.0, CHECK_MESSAGE


if __name__ == "__main__":
    import json as _json

    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        print(_json.dumps(run_sanity(), sort_keys=True))
    elif len(sys.argv) > 1 and sys.argv[1] == "--dump-tree":
        raise SystemExit(dump_tree_main())
    else:
        print(run_evaluation())
