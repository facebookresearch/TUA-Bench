#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

set -euo pipefail

CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CASE_DIR"

set +eu
set +o pipefail
source /opt/openfoam11/etc/bashrc >/dev/null 2>&1
set -o pipefail
set -e
set -u

python3 build_case.py --design design.json

rm -rf constant/polyMesh constant/fluid/polyMesh constant/solid/polyMesh postProcessing VTK processor* logs renders metrics.json
for entry in ./*; do
  name="$(basename "$entry")"
  if [[ -d "$entry" && "$name" =~ ^[0-9]+([.][0-9]+)?$ && "$name" != "0" ]]; then
    rm -rf "$entry"
  fi
done

mkdir -p logs

blockMesh > logs/blockMesh.log 2>&1
topoSet > logs/topoSet.log 2>&1
splitMeshRegions -cellZones -defaultRegionName solid -overwrite > logs/splitMeshRegions.log 2>&1
topoSet -region solid -dict system/solidZonesDict > logs/topoSetSolid.log 2>&1
foamMultiRun > logs/foamMultiRun.log 2>&1

python3 extract_metrics.py --case "$CASE_DIR" --output "$CASE_DIR/metrics.json"
python3 render_svgs.py --case "$CASE_DIR" --metrics "$CASE_DIR/metrics.json" --output-dir "$CASE_DIR/renders"
