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
RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    curl \
    dbus-x11 \
    libreoffice-calc \
    python3 \
    python3-venv \
    tmux \
    xauth \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    openpyxl==3.1.5 \
    pandas==2.3.2 \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'exec dbus-run-session -- xvfb-run -a /usr/bin/libreoffice "$@"' \
    > /usr/local/bin/libreoffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/soffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/localc \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config/libreoffice/4/user && curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/1de60575-bb6e-4c3d-9e6a-2fa699f9f197/EntireSummerSales.xlsx -o /app/EntireSummerSales.xlsx \
 && chmod +x /usr/local/bin/libreoffice \
 && chown -R agent:agent /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
