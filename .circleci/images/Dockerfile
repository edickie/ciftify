FROM ubuntu:xenial-20161213

# Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bc \
        tar \
        dpkg \
        wget \
        curl \
        unzip \
        gcc \
        libstdc++6 \
        git \
        ca-certificates

RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.2.3-1~nd14.04+1

COPY cifti_requirements.txt cifti_requirements.txt

RUN apt-get update && \
    apt-get install -y python3.5 python3-pip python3-dev python3-setuptools gcc-5 libncurses5-dev && \
    pip3 install -r cifti_requirements.txt && \
    rm -r cifti_requirements.txt && \
    cp -s /usr/bin/python3 /usr/bin/python

CMD ["/bin/sh"]
