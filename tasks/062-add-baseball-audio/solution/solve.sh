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

python - <<'PY'
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

output_path = localize_path("/app/Mady_and_Mia_Baseball.pptx")
import zipfile
import xml.etree.ElementTree as ET

slide_rels_name = "ppt/slides/_rels/slide1.xml.rels"
namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
audio_target = f"file://{localize_path('/app/Baseball.mp3')}"

with zipfile.ZipFile(output_path, "r") as archive:
    members = {name: archive.read(name) for name in archive.namelist()}

root = ET.fromstring(members[slide_rels_name])
relationships = root.findall(f"{{{namespace}}}Relationship")
audio_relationship = None
max_id = 0
for relationship in relationships:
    rel_id = relationship.attrib.get("Id", "")
    if rel_id.startswith("rId"):
        try:
            max_id = max(max_id, int(rel_id[3:]))
        except ValueError:
            pass
    if "audio" in relationship.attrib.get("Type", ""):
        audio_relationship = relationship

attributes = {
    "Id": f"rId{max_id + 1}",
    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/audio",
    "Target": audio_target,
}
if audio_relationship is None:
    ET.SubElement(root, f"{{{namespace}}}Relationship", attributes)
else:
    audio_relationship.attrib.update(attributes)

members[slide_rels_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
with zipfile.ZipFile(output_path, "w") as archive:
    for name, data in members.items():
        archive.writestr(name, data)
PY
