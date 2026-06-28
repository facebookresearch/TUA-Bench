# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM debian:bookworm

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
    chromium \
    dbus-x11 \
    procps \
    python3 \
    python3-venv \
    asciinema \
    tmux \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    pytest==8.4.1 \
 && printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    'PROFILE_DIR="${CHROME_USER_DATA_DIR:-$HOME/.config/google-chrome}"' \
    'mkdir -p "$PROFILE_DIR"' \
    'exec dbus-run-session -- xvfb-run -a /usr/bin/chromium --user-data-dir="$PROFILE_DIR" --profile-directory=Default --no-first-run --no-default-browser-check --password-store=basic --disable-dev-shm-usage --no-sandbox "$@"' \
    > /usr/local/bin/google-chrome \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/.config/google-chrome/Default /home/agent/.config/asciinema \
 && chmod +x /usr/local/bin/google-chrome \
 && chown -R agent:agent /app /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
