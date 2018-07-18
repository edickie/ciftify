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

#? ENV LD_LIBRARY_PATH=$FREESURFER_HOME/lib:$LD_LIBRARY_PATH
ENV FSLPARALLEL=1 \
    SGE_ON=true
#    PATH=/usr/local/fsleyes/usr/bin:/usr/local/fsl/bin:/usr/local/fsl/lib:$PATH

RUN mkdir /opt/msm && \
    curl -sSL https://github.com/ecr05/MSM_HOCR_macOSX/releases/download/1.0/msm_ubuntu > /opt/msm/msm && \
    chmod 770 /opt/msm/msm

ENV PATH=/opt/msm:$PATH

RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.2.3-1~nd14.04+1


COPY cifti_requirements.txt cifti_requirements.txt

RUN apt-get update && \
    pip install https://github.com/edickie/ciftify/archive/2.0.5-alpha.tar.gz

ENTRYPOINT ["/bin/bash"]
