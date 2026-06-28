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
RUN apt-get update && apt-get install -y --no-install-recommends \
    asciinema \
    ca-certificates \
    curl \
    python3 \
    python3-venv \
    tmux \
 && python3 -m venv "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir \
    PyMuPDF==1.25.1 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /usr/local/share/tua \
 && ln -s /home/agent /home/user \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY build_setup.py /usr/local/bin/build_setup.py
COPY task_spec.json /usr/local/share/tua/task_spec.json

RUN chmod +x /usr/local/bin/build_setup.py \
 && chown -R agent:agent /app /home/agent /usr/local/share/tua

USER agent
WORKDIR /home/agent

RUN python3 /usr/local/bin/build_setup.py

WORKDIR /app
