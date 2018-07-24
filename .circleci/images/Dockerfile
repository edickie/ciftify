FROM ubuntu:xenial-20161213

# Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bc \
        ca-certificates \
        curl \
        dpkg \
        gcc \
        gcc-5 \
        git \
        libncurses5-dev \
        libstdc++6 \
        python3.5 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-venv \
        tar \
        unzip \
        wget

# Get connectome-workbench
RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.2.3-1~nd14.04+1

  # Get bids-validator
  RUN apt-get update && \
      curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
      apt-get install -y nodejs && \
      apt-get update && \
      npm install -g bids-validator

CMD ["/bin/bash"]
