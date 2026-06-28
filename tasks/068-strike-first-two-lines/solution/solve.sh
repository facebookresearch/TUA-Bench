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
OUTPUT_PATH="$(localize_path "/app/New_Club_Spring_2018_Training.pptx")"
TMP_PATH="$(mktemp)"

curl -fsSL --retry 10 --retry-all-errors --retry-delay 2 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_impress/550ce7e7-747b-495f-b122-acdc4d0b8e54/New_Club_Spring_2018_Training_with_strike.data -o "$TMP_PATH"
mkdir -p "$(dirname "$OUTPUT_PATH")"
cp "$TMP_PATH" "$OUTPUT_PATH"
rm -f "$TMP_PATH"
