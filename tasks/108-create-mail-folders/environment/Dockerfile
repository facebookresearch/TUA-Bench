# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV DISPLAY=:99
ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"
ENV THUNDERBIRD_START_MODE="default"

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
    at-spi2-core \
    ca-certificates \
    curl \
    dbus-x11 \
    gir1.2-atspi-2.0 \
    libatk-adaptor \
    procps \
    python3 \
    python3-gi \
    python3-pyatspi \
    python3-venv \
    sqlite3 \
    thunderbird \
    tmux \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv --system-site-packages "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    cssselect==1.2.0 \
    lxml==5.3.0 \
    pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads

COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh
COPY thunderbird_state.py /usr/local/bin/thunderbird_state.py
COPY thunderbird_live_helper.py /usr/local/bin/thunderbird_live_helper.py

RUN chmod +x /usr/local/bin/task-entrypoint.sh /usr/local/bin/thunderbird_state.py /usr/local/bin/thunderbird_live_helper.py \
 && curl -L --fail --retry 3 -o /tmp/thunderbird-profile.tar.gz https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/thunderbird/dd84e895-72fd-4023-a336-97689ded257c/thunderbird-profile.tar.gz \
 && tar -xzf /tmp/thunderbird-profile.tar.gz -C /home/agent \
 && rm -f /tmp/thunderbird-profile.tar.gz \
 && chown -R agent:agent /app /home/agent \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
