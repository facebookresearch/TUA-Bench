# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

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
    ffmpeg \
    file \
    python3 \
    python3-pip \
    tmux \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app/input \
 && chown -R agent:agent /app \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY input /app/input

RUN chown -R agent:agent /app \
 && python3 --version \
 && ffmpeg -version \
 && ffprobe -version \
 && tmux -V \
 && asciinema --version

USER agent
WORKDIR /app
