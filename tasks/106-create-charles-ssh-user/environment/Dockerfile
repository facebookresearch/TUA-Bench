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
RUN apt-get update && apt-get install -y \
    asciinema \
    ca-certificates \
    curl \
    expect \
    file \
    python3 \
    python3-venv \
    sudo \
    tmux \
    unzip \
    util-linux \
    xz-utils \
    zip \
    && python3 -m venv "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
    && "$VIRTUAL_ENV/bin/pip" install pytest==8.4.1 \
    && useradd -m -s /bin/bash agent \
    && echo 'agent ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/agent \
    && chmod 0440 /etc/sudoers.d/agent \
    && mkdir -p /app /home/agent/.config/tua \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN bash -lc 'set -euo pipefail && mkdir -p /home/test1'
RUN chown -R agent:agent /app /home/agent
USER agent
WORKDIR /app
RUN bash -lc 'set -euo pipefail && mkdir -p /app/.osworld && curl -fsSL --retry 3 --retry-delay 1 '"'"'https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/os/5812b315-e7bd-4265-b51f-863c02174c28/check_password.sh'"'"' -o '"'"'/app/.osworld/check_password.sh'"'"' && chmod +x /app/.osworld/check_password.sh'
