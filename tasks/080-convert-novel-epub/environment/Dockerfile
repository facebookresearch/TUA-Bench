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
at-spi2-core \
    ca-certificates \
    chromium \
    curl \
    dbus-x11 \
    gir1.2-atspi-2.0 \
    libatk-adaptor \
    python3 \
    python3-pip \
    python3-pyatspi \
    python3-venv \
    tar \
    tmux \
    x11-utils \
    xauth \
    xdg-utils \
    xvfb \
    xz-utils \
 && python3 -m venv --system-site-packages "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
cssselect==1.2.0 \
    formulas==1.2.9 \
    lxml==5.3.0 \
    mutagen==1.47.0 \
    openpyxl==3.1.5 \
    pandas==2.2.3 \
    pdfplumber==0.11.4 \
    playwright==1.52.0 \
    python-docx==1.1.2 \
    pytesseract==0.3.13 \
    PyYAML==6.0.2 \
    rapidfuzz==3.10.1 \
    tldextract==5.1.2 \
    xmltodict==0.13.0 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /usr/local/share/tua \
 && ln -s /home/agent /home/user

COPY google-chrome-wrapper.sh /usr/local/bin/google-chrome
COPY task_state.py /usr/local/bin/task_state.py
COPY build_setup.py /usr/local/bin/build_setup.py
COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh
COPY task_spec.json /usr/local/share/tua/task_spec.json

RUN chmod +x /usr/local/bin/google-chrome /usr/local/bin/task_state.py /usr/local/bin/build_setup.py /usr/local/bin/task-entrypoint.sh \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && chown -R agent:agent /app /home/agent /usr/local/share/tua

USER agent
WORKDIR /home/agent

RUN python3 /usr/local/bin/build_setup.py

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
