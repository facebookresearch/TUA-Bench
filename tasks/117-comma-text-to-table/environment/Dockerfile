# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network
RUN install -d -m 755 /tmp/apt-archives \
 && install -d -o _apt -g root -m 700 /tmp/apt-archives/partial \
 && apt-get update \
 && apt-get install -y --no-install-recommends -o Dir::Cache::archives=/tmp/apt-archives \
    asciinema \
    ca-certificates \
    curl \
    dbus-x11 \
    libreoffice-writer \
    python3 \
    python3-venv \
    tmux \
    xauth \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir \
    python-docx==1.2.0 \
 && tmux -V \
 && asciinema --version \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'exec dbus-run-session -- xvfb-run -a /usr/bin/libreoffice "$@"' \
    > /usr/local/bin/libreoffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/soffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/lowriter \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config/libreoffice/4/user \
 && curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_writer/936321ce-5236-426a-9a20-e0e3c5dc536f/Graphemes_Sound_Letter_Patterns.docx -o /app/Graphemes_Sound_Letter_Patterns.docx \
 && chmod +x /usr/local/bin/libreoffice \
 && chown -R agent:agent /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config \
 && apt-get clean \
 && rm -rf /tmp/apt-archives \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
