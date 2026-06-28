# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM docker.io/openfoam/openfoam11-paraview510

ENV HOME=/home/agent

USER root

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network

RUN id -u agent >/dev/null 2>&1 || useradd -m -s /bin/bash agent
RUN mkdir -p /app/input /logs/artifacts /logs/agent /logs/verifier /var/lib/apt/lists/partial \
    && DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        asciinema \
        libutempter0 \
        tmux \
    && ldconfig \
    && tmux -V \
    && asciinema --version \
    && chown -R agent:agent /app /logs /home/agent \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY input /app/input

RUN chown -R agent:agent /app/input

ENTRYPOINT []

WORKDIR /app
USER agent
