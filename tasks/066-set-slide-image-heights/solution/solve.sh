#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
AGENT_HOME="${AGENT_HOME:-/home/agent}"
localize_path() {
  case "$1" in
    /app/*)
      printf "%s/%s" "${APP_DIR:-/app}" "${1#/app/}"
      ;;
    /home/agent/*)
      printf "%s/%s" "${AGENT_HOME:-/home/agent}" "${1#/home/agent/}"
      ;;
    *)
      printf "%s" "$1"
      ;;
  esac
}
OUTPUT_PATH="$(localize_path "/app/30_1.pptx")"
TMP_PATH="$(mktemp)"

curl -fsSL --retry 10 --retry-all-errors --retry-delay 2 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_impress/7ae48c60-f143-4119-b659-15b8f485eb9a/30_1_Gold.pptx -o "$TMP_PATH"
mkdir -p "$(dirname "$OUTPUT_PATH")"
cp "$TMP_PATH" "$OUTPUT_PATH"
rm -f "$TMP_PATH"
