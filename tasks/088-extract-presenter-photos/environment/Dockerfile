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
    default-jre \
    ffmpeg \
    file \
    gimp \
    gir1.2-atspi-2.0 \
    git \
    gnome-terminal \
    jq \
    libatk-adaptor \
    libreoffice \
    nautilus \
    procps \
    python3 \
    python3-gi \
    python3-pip \
    python3-pyatspi \
    python3-venv \
    socat \
    sqlite3 \
    sudo \
    tar \
    tesseract-ocr \
    thunderbird \
    tmux \
    unzip \
    wmctrl \
    x11-utils \
    xauth \
    xclip \
    xdg-utils \
    xdotool \
    xsel \
    xvfb \
    xz-utils \
    zip \
    imagemagick \
 && python3 -m venv --system-site-packages "$VIRTUAL_ENV" \
 && "$VIRTUAL_ENV/bin/pip" install --upgrade pip \
 && "$VIRTUAL_ENV/bin/pip" install \
beautifulsoup4==4.13.4 \
    borb==2.1.25 \
    cssselect==1.2.0 \
    fastdtw==0.3.4 \
    formulas==1.2.9 \
    imagehash==4.3.2 \
    librosa==0.10.2.post1 \
    lxml==5.3.0 \
    mutagen==1.47.0 \
    numpy==2.0.2 \
    odfpy==1.4.1 \
    opencv-python-headless==4.10.0.84 \
    openpyxl==3.1.5 \
    pandas==2.2.3 \
    pdfplumber==0.11.4 \
    pillow==10.4.0 \
    playwright==1.52.0 \
    PyMuPDF==1.25.1 \
    pypdf==5.0.1 \
    PyPDF2==3.0.1 \
    pygame==2.6.1 \
    pytest==8.4.1 \
    python-docx==1.1.2 \
    python-pptx==1.0.2 \
    pysrt==1.1.2 \
    pytesseract==0.3.13 \
    PyYAML==6.0.2 \
    rapidfuzz==3.10.1 \
    scikit-image==0.24.0 \
    scipy==1.14.1 \
    tldextract==5.1.2 \
    xmltodict==0.13.0 \
 && useradd -m -s /bin/bash agent \
 && mkdir -p /app /var/lib/tua-state /usr/local/share/tua \
 && ln -s /home/agent /home/user

COPY google-chrome-wrapper.sh /usr/local/bin/google-chrome
COPY code-shim.py /usr/local/bin/code
COPY gsettings-wrapper.py /usr/local/bin/gsettings
COPY task_state.py /usr/local/bin/task_state.py
COPY build_setup.py /usr/local/bin/build_setup.py
COPY task-entrypoint.sh /usr/local/bin/task-entrypoint.sh
COPY task_spec.json /usr/local/share/tua/task_spec.json

RUN chmod +x /usr/local/bin/google-chrome /usr/local/bin/code /usr/local/bin/gsettings /usr/local/bin/task_state.py /usr/local/bin/build_setup.py /usr/local/bin/task-entrypoint.sh \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/google-chrome-stable \
 && ln -sf /usr/local/bin/google-chrome /usr/local/bin/chromium \
 && chown -R agent:agent /app /home/agent /var/lib/tua-state /usr/local/share/tua

USER agent
WORKDIR /home/agent

RUN python3 /usr/local/bin/build_setup.py

# Start on the Desktop because the seeded photos and expected outputs both live there.
WORKDIR /home/user/Desktop
ENTRYPOINT ["/usr/local/bin/task-entrypoint.sh"]
