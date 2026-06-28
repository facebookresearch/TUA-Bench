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
    ca-certificates \
    curl \
    dbus-x11 \
    gimp \
    python3 \
    python3-venv \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
    file \
    imagemagick \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    numpy==2.3.3 \
    pillow==11.2.1 \
    scikit-image==0.25.2 \
    pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app \
 && curl -fL \
    "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/dog_with_background.png" \
    -o /app/dog_with_background.png \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN chown -R agent:agent /app

USER agent
WORKDIR /app
