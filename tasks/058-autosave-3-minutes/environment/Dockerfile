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
    build-essential \
    ca-certificates \
    curl \
    dbus-x11 \
    ffmpeg \
    fonts-liberation \
    libsndfile1 \
    libreoffice-impress \
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
    fastdtw==0.3.4 \
    librosa==0.11.0 \
    numpy==2.3.3 \
    pillow==11.2.1 \
    python-pptx==1.0.2 \
    scikit-image==0.25.2 \
    scipy==1.16.2 \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'exec dbus-run-session -- xvfb-run -a /usr/bin/libreoffice "$@"' \
    > /usr/local/bin/libreoffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/soffice \
 && ln -sf /usr/local/bin/libreoffice /usr/local/bin/loimpress \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config/libreoffice/4/user \
 && chmod +x /usr/local/bin/libreoffice \
 && chown -R agent:agent /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
