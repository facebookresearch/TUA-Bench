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
    gimp \
    python3 \
    python3-venv \
    tmux \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    numpy==2.3.3 \
    pillow==11.2.1 \
    scikit-image==0.25.2 \
    pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app && curl -fL --retry 3 --retry-delay 1 \
    "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/gimp/e2dd0213-26db-4349-abe5-d5667bfd725c/orange_background.xcf" \
    -o /app/orange_background.xcf \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN chown -R agent:agent /app

USER agent
WORKDIR /app
