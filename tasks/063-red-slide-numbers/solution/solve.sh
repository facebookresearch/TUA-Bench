#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
AGENT_HOME="${AGENT_HOME:-/home/agent}"
export APP_DIR AGENT_HOME

python3 - <<'PY'
import os
from pathlib import Path

APP_DIR = Path(os.environ['APP_DIR'])
AGENT_HOME = Path(os.environ['AGENT_HOME'])

def localize_path(path: str) -> Path:
    if path.startswith('/app/'):
        return APP_DIR / path.removeprefix('/app/')
    if path.startswith('/home/agent/'):
        return AGENT_HOME / path.removeprefix('/home/agent/')
    return Path(path)

output_path = localize_path("/app/saa-format-guide.pptx")
import zipfile
import xml.etree.ElementTree as ET

slide_master_name = "ppt/slideMasters/slideMaster1.xml"
ns = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

with zipfile.ZipFile(output_path, "r") as archive:
    members = {name: archive.read(name) for name in archive.namelist()}

root = ET.fromstring(members[slide_master_name])
target_shape = None
for shape in root.findall(".//p:sp", ns):
    if shape.find(".//p:ph[@type='sldNum']", ns) is not None:
        target_shape = shape
        break
if target_shape is None:
    raise RuntimeError("Could not locate the slide number placeholder")

tx_body = target_shape.find("p:txBody", ns)
if tx_body is None:
    tx_body = ET.SubElement(target_shape, "{%s}txBody" % ns["p"])
paragraph = tx_body.find("a:p", ns)
if paragraph is None:
    paragraph = ET.SubElement(tx_body, "{%s}p" % ns["a"])
run = ET.SubElement(paragraph, "{%s}r" % ns["a"])
run_props = ET.SubElement(run, "{%s}rPr" % ns["a"])
solid_fill = ET.SubElement(run_props, "{%s}solidFill" % ns["a"])
ET.SubElement(solid_fill, "{%s}srgbClr" % ns["a"], {"val": "FF0000"})
ET.SubElement(run, "{%s}t" % ns["a"]).text = ""

members[slide_master_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
with zipfile.ZipFile(output_path, "w") as archive:
    for name, data in members.items():
        archive.writestr(name, data)
PY
