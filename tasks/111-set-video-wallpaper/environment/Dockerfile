# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

       FROM ubuntu:24.04

       ENV DEBIAN_FRONTEND=noninteractive
       ENV VIRTUAL_ENV=/opt/venv
       ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

       COPY vlcshim.py /usr/local/lib/tua-vlcshim.py

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network
       RUN apt-get update && apt-get install -y \
           build-essential \
           ca-certificates \
           curl \
           ffmpeg \
           libglib2.0-0 \
           libsndfile1 \
           python3 \
           python3-venv \
           tmux \
           vlc \
           file \
        && python3 -m venv "$VIRTUAL_ENV" \
        && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
        && "$VIRTUAL_ENV/bin/pip" install \
           fastdtw==0.3.4 \
           ImageHash==4.3.2 \
           librosa==0.11.0 \
           numpy==2.3.3 \
           opencv-python-headless==4.11.0.86 \
           pillow==11.2.1 \
           scikit-image==0.25.2 \
           scipy==1.16.2 \
        && useradd -m -s /bin/bash agent \
        && mkdir -p /app /home/agent/Desktop /home/agent/Documents /home/agent/Downloads /home/agent/Videos /home/agent/.config/vlc /home/agent/.local/state/tua-vlc \
        && touch /home/agent/.config/vlc/vlcrc \
        && ln -sfn /home/agent /home/user \
        && ln -sfn /home/agent/Desktop /app/Desktop \
        && printf '%s\n' \
           '#!/usr/bin/env bash' \
           'set -euo pipefail' \
           'exec /usr/bin/env python3 /usr/local/lib/tua-vlcshim.py "$@"' \
           > /usr/local/bin/vlc \
        && ln -sf /usr/local/bin/vlc /usr/local/bin/cvlc \
        && chmod +x /usr/local/bin/vlc /usr/local/bin/cvlc /usr/local/lib/tua-vlcshim.py \
&& mkdir -p /home/agent/Desktop \
&& curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/vlc/efcf0d81-0835-4880-b2fd-d866e8bc2294/Interstellar%20Movie%20-%20Official%20Trailer.mp4 -o '/home/agent/Desktop/Interstellar Movie - Official Trailer.mp4' \
        && chown -R agent:agent /app /home/agent \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

       USER agent
       WORKDIR /app
