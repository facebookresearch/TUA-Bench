#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

ffmpeg -loglevel error -y -i /home/agent/Desktop/flipped_1984_Apple_Macintosh_Commercial.mp4 -vf hflip,vflip -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k /home/agent/1984_Apple_Macintosh_Commercial.mp4
