# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM ubuntu:24.04

ARG OPENSTUDIO_URL="https://github.com/NatLabRockies/OpenStudio/releases/download/v3.10.0/OpenStudio-3.10.0%2B86d7e215a1-Ubuntu-24.04-x86_64.tar.gz"
ARG OPENSTUDIO_SHA256="9d4d469ec34d772e8e3803735470db9f94730a798d1cf9e61f8799a5e8663322"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      asciinema \
      ca-certificates \
      curl \
      libgomp1 \
      libx11-6 \
      libxau6 \
      libxcb1 \
      tmux \
 && curl -fsSL "$OPENSTUDIO_URL" -o /tmp/openstudio.tar.gz \
 && echo "$OPENSTUDIO_SHA256  /tmp/openstudio.tar.gz" | sha256sum -c - \
 && mkdir -p /opt/openstudio-root \
 && tar -xzf /tmp/openstudio.tar.gz -C /opt/openstudio-root \
 && mv /opt/openstudio-root/OpenStudio-3.10.0+86d7e215a1-Ubuntu-24.04-x86_64/usr/local/openstudio-3.10.0 /opt/openstudio \
 && printf '%s\n' '/opt/openstudio/lib' > /etc/ld.so.conf.d/openstudio.conf \
 && ldconfig \
 && ln -sf /opt/openstudio/bin/openstudio /usr/local/bin/openstudio \
 && openstudio openstudio_version \
 && openstudio energyplus_version \
 && test -x /opt/openstudio/EnergyPlus/energyplus \
 && tmux -V \
 && asciinema --version \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app/input \
 && rm -rf /opt/openstudio-root /tmp/openstudio.tar.gz \
 && rm -rf /var/lib/apt/lists/*

COPY input /app/input

RUN chown -R agent:agent /app

WORKDIR /app
USER agent
