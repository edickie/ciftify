FROM poldracklab/fmriprep:1.0.15

COPY license.txt /opt/freesurfer/license.txt

# Prepare environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        bc \
        tar \
        dpkg \
        wget \
        unzip \
        gcc \
        libstdc++6

ENV FSLPARALLEL=1 \
    SGE_ON=true

RUN mkdir /opt/msm && \
    curl -sSL https://github.com/ecr05/MSM_HOCR_macOSX/releases/download/1.0/msm_ubuntu > /opt/msm/msm && \
    chmod 770 /opt/msm/msm

ENV PATH=/opt/msm:$PATH

RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.2.3-1~nd14.04+1

RUN apt-get update && \
    curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
    apt-get install -y nodejs && \
    apt-get update && \
    npm install -g bids-validator

COPY fmriprep_cifti_requirements.txt fmriprep_cifti_requirements.txt

RUN apt-get update && \
    pip install -r fmriprep_cifti_requirements.txt

RUN mkdir /home/code && \
    git clone -b master https://github.com/edickie/ciftify.git /home/code/ciftify

ENV PATH=/home/code/ciftify/ciftify/bin:${PATH} \
    PYTHONPATH=/home/code/ciftify:${PYTHONPATH} \
    CIFTIFY_TEMPLATES=/home/code/ciftify/ciftify/data

WORKDIR /tmp/

ENTRYPOINT ["/home/code/ciftify/ciftify/bidsapp/run.py"]
