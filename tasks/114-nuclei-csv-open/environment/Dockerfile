# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

FROM docker.io/cellprofiler/cellprofiler:4.2.8 AS cellprofiler_source

FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:${PATH}"

RUN printf '%s\n' \
    'Acquire::Queue-Mode "access";' \
    'Acquire::http::Pipeline-Depth "0";' \
    'Acquire::https::Pipeline-Depth "0";' \
    'Acquire::Retries "5";' \
    'Acquire::http::Timeout "30";' \
    'Acquire::https::Timeout "30";' \
    > /etc/apt/apt.conf.d/99tua-network

RUN set -eux; \
    apt_retry() { \
        for attempt in 1 2 3 4 5; do \
            if apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=120 -o Acquire::https::Timeout=120 "$@"; then \
                return 0; \
            fi; \
            if [ "$attempt" -eq 5 ]; then \
                return 1; \
            fi; \
            rm -rf /var/lib/apt/lists/*; \
            sleep $((attempt * 5)); \
        done; \
    }; \
    apt_retry update; \
    apt_retry install -y --no-install-recommends \
        asciinema \
        ca-certificates \
        curl \
        git \
        libfreetype6 \
        libgdk-pixbuf2.0-0 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libjpeg-turbo8 \
        libsm6 \
        libtiff5 \
        libxext6 \
        libxrender1 \
        openjdk-11-jre-headless \
        python3.8 \
        ripgrep \
        tmux \
        xz-utils; \
    useradd -m -s /bin/bash agent; \
    mkdir -p /app/input /app/artifacts /logs/artifacts /logs/agent /logs/verifier; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

COPY --from=cellprofiler_source /opt/venv /opt/venv
COPY input /app/input

RUN set -eux; \
    python3.8 --version; \
    java -version; \
    /opt/venv/bin/python3.8 -c "import cellprofiler, cellprofiler_core, javabridge, numpy, scipy, skimage; print('cellprofiler headless imports ok')"; \
    cd /app; \
    cellprofiler -c -r -p /app/input/config/ExampleSpeckles.cppipe -i /app/input/images -o /tmp/cellprofiler-smoke; \
    test -s /tmp/cellprofiler-smoke/Nuclei.csv; \
    rm -rf /tmp/cellprofiler-smoke; \
    rg --version; \
    tmux -V; \
    asciinema --version; \
    chown -R agent:agent /app /logs /home/agent /opt/venv

ENTRYPOINT []

WORKDIR /app
USER agent
