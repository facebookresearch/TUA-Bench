# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV DISPLAY=:99
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
    file \
    git \
    jq \
    procps \
    python-is-python3 \
    python3 \
    python3-venv \
    socat \
    sudo \
    tar \
    tmux \
    unzip \
    x11-utils \
    xauth \
    xvfb \
    xz-utils \
    zip \
 && python3 -m venv --system-site-packages "$VIRTUAL_ENV" \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /var/lib/tua-state /usr/local/share/tua \
 && ln -s /home/agent /home/user

COPY google-chrome-wrapper.sh /usr/local/bin/google-chrome
COPY code-shim.py /usr/local/bin/code
COPY gsettings-wrapper.py /usr/local/bin/gsettings
COPY task_state.py /usr/local/bin/task_state.py
COPY build_setup.py /usr/local/bin/build_setup.py
COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh
COPY task_spec.json /usr/local/share/tua/task_spec.json

RUN chmod +x /usr/local/bin/google-chrome /usr/local/bin/code /usr/local/bin/gsettings /usr/local/bin/task_state.py /usr/local/bin/build_setup.py /usr/local/bin/task-entrypoint.sh \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && chown -R agent:agent /app /home/agent /var/lib/tua-state /usr/local/share/tua

USER agent
WORKDIR /home/agent

RUN python3 /usr/local/bin/build_setup.py

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
