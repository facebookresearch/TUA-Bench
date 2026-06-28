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

output_path = localize_path("/home/agent/.config/libreoffice/4/user/registrymodifications.xcu")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(
    '''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
  <item oor:path="/org.openoffice.Office.Common/Save/Document">
    <prop oor:name="AutoSaveTimeIntervall">
      <value>3</value>
    </prop>
  </item>
</oor:items>
''',
    encoding="utf-8",
)
PY
