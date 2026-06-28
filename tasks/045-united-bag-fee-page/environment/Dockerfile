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
RUN apt-get update && apt-get install -y \
    asciinema \
    ca-certificates \
    chromium \
    dbus-x11 \
    procps \
    python3 \
    python3-venv \
    tmux \
    xclip \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    playwright==1.54.0 \
    pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/.config/google-chrome/Default /home/agent/.config/asciinema

COPY google-chrome-wrapper.sh /usr/local/bin/google-chrome
COPY chrome_state.py /usr/local/bin/chrome_state.py
COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh

RUN chmod +x /usr/local/bin/google-chrome /usr/local/bin/chrome_state.py /usr/local/bin/task-entrypoint.sh \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && chown -R agent:agent /app /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
