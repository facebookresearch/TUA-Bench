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
    curl \
    dbus-x11 \
    procps \
    python3 \
    python3-venv \
    tmux \
    unzip \
    x11-utils \
    xauth \
    xdotool \
    xvfb \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
    pytest==8.4.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /home/agent/Desktop /home/agent/.config/google-chrome/Default \
 && curl -L --retry 3 --output /home/agent/Desktop/helloExtension.zip \
    "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/chrome/6766f2b8-8a72-417f-a9e5-56fcaa735837/helloExtension.zip"

COPY google-chrome-wrapper.sh /usr/local/bin/google-chrome
COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh

RUN cat > /home/agent/.config/user-dirs.dirs <<'EOF'
XDG_DESKTOP_DIR="$HOME/Desktop"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
XDG_TEMPLATES_DIR="$HOME/Templates"
XDG_PUBLICSHARE_DIR="$HOME/Public"
XDG_DOCUMENTS_DIR="$HOME/Documents"
XDG_MUSIC_DIR="$HOME/Music"
XDG_PICTURES_DIR="$HOME/Pictures"
XDG_VIDEOS_DIR="$HOME/Videos"
EOF

RUN chmod +x /usr/local/bin/google-chrome /usr/local/bin/task-entrypoint.sh \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && chown -R agent:agent /app /home/agent/Desktop /home/agent/.config \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER agent
WORKDIR /app
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
