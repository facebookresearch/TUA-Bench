# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/opt/slicer/bin:/usr/local/bin:${PATH}"

ARG SLICER_DOWNLOAD_URL=https://slicer-packages.kitware.com/api/v1/item/67c51fc129825655577cfee9/download

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    curl \
    dbus-x11 \
    libasound2t64 \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    libfreetype6 \
    libglib2.0-0 \
    libgl1 \
    libglu1-mesa \
    libgtk-3-0 \
    libice6 \
    libnss3 \
    libopengl0 \
    libpulse-mainloop-glib0 \
    libpulse0 \
    libsm6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-util1 \
    libxcb-xinerama0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxi6 \
    libxkbcommon-x11-0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    python3 \
    python3-venv \
    tar \
    tmux \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    nibabel==5.3.2 \
    numpy==2.1.3 \
    scipy==1.14.1 \
    trimesh==4.6.8 \
 && curl -fL --retry 5 --retry-delay 2 --retry-all-errors -o /tmp/slicer.tar.gz "${SLICER_DOWNLOAD_URL}" \
 && tar -xzf /tmp/slicer.tar.gz -C /opt \
 && SLICER_ROOT="$(find /opt -maxdepth 1 -type d -name 'Slicer-*' | head -n 1)" \
 && test -n "${SLICER_ROOT}" \
 && rm -rf /opt/slicer \
 && mv "${SLICER_ROOT}" /opt/slicer \
 && ln -sf /opt/slicer/Slicer /usr/local/bin/Slicer \
 && ln -sf /opt/slicer/bin/PythonSlicer /usr/local/bin/PythonSlicer \
 && tmux -V \
 && asciinema --version \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app/input /app/artifacts /logs/artifacts /logs/agent /logs/verifier \
 && rm -f /tmp/slicer.tar.gz \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY input /app/input

RUN chown -R agent:agent /app /logs /home/agent /opt/slicer

ENTRYPOINT []

WORKDIR /app
USER agent
