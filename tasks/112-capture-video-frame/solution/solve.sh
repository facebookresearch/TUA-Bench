#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

vlc --start-time=120.5 --snapshot-path /home/agent/Desktop --snapshot-prefix interstellar --snapshot-format png '/home/agent/Desktop/Interstellar Movie - Official Trailer.mp4'
