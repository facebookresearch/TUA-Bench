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
    dbus-x11 \
    fonts-liberation \
    libreoffice-calc \
    python3 \
    python3-uno \
    python3-venv \
    tmux \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    cssselect==1.3.0 \
    formulas==1.3.1 \
    lxml==5.4.0 \
    openpyxl==3.1.5 \
    pandas==2.3.2 \
    pymupdf==1.26.4 \
    pypdf==6.1.1 \
    rapidfuzz==3.13.0 \
    xmltodict==0.14.2 \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'exec dbus-run-session -- xvfb-run -a /usr/bin/libreoffice "$@"' \
    > /usr/local/bin/libreoffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/soffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/localc \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config/libreoffice/4/user && curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/6054afcb-5bab-4702-90a0-b259b5d3217c/Date_Budget_Variance_HideNA.xlsx -o /app/Date_Budget_Variance_HideNA.xlsx \
 && chmod +x /usr/local/bin/libreoffice \
 && chown -R agent:agent /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
