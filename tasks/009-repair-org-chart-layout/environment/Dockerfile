# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DRAWIO_VERSION=29.6.6
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
    fonts-dejavu-core \
    libasound2t64 \
    python3 \
    python3-venv \
    x11-utils \
    xauth \
    xvfb \
    file \
 && arch="$(dpkg --print-architecture)" \
 && case "$arch" in \
      amd64) asset="drawio-amd64-${DRAWIO_VERSION}.deb" ;; \
      arm64) asset="drawio-arm64-${DRAWIO_VERSION}.deb" ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac \
 && curl -fL -o /tmp/drawio.deb \
    "https://github.com/jgraph/drawio-desktop/releases/download/v${DRAWIO_VERSION}/${asset}" \
 && apt-get install -y /tmp/drawio.deb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    cli-anything-drawio==1.0.0 \
    google-genai==1.14.0 \
    openai==2.31.0 \
    pytest==8.4.1 \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'exec dbus-run-session -- xvfb-run -a /opt/drawio/drawio --no-sandbox "$@"' \
    > /usr/local/bin/drawio \
 && ln -sf /usr/local/bin/drawio /usr/local/bin/draw.io \
 && ln -sf /usr/local/bin/drawio /usr/local/bin/drawio-desktop \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app/input \
 && chown -R agent:agent /app \
 && rm -f /tmp/drawio.deb \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN chmod +x /usr/local/bin/drawio

COPY input /app/input

RUN chown -R agent:agent /app/input

USER agent
WORKDIR /app
