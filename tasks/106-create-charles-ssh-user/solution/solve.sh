#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


        set -euo pipefail

        sudo mkdir -p /home/test1
if ! id -u charles >/dev/null 2>&1; then
  sudo useradd -d /home/test1 -M -s /bin/bash charles
fi
echo 'charles:Ex@mpleP@55w0rd!' | sudo chpasswd
sudo chown charles:charles /home/test1
sudo chmod 700 /home/test1
