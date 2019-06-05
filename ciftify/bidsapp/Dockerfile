FROM poldracklab/fmriprep:1.3.2

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

RUN mkdir /opt/msm && \
    curl -sSL https://github.com/ecr05/MSM_HOCR_macOSX/releases/download/1.0/msm_ubuntu > /opt/msm/msm && \
    chmod 777 /opt/msm/msm

ENV PATH=/opt/msm:$PATH

# neuro debian install of connectome-workbench and getting the fsl mni templates
# note that fmriprep is getting templates from template flow but they don't match in dimensions
RUN apt-get update && \
    apt-get install -y connectome-workbench=1.3.2-2~nd16.04+1 \
      fsl-mni152-templates=5.0.7-2

# this was the bids validator step but this should be in the fmriprep base..
# RUN apt-get update && \
#    curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
#    apt-get install -y nodejs && \
#    apt-get update && \
#    npm install -g bids-validator

# setting up an install of ciftify (manual version) inside the container
ADD https://api.github.com/repos/edickie/ciftify/git/refs/heads/master version.json
RUN mkdir /home/code && git clone -b master https://github.com/edickie/ciftify.git /home/code/ciftify

ENV PATH=/home/code/ciftify/ciftify/bin:${PATH} \
    PYTHONPATH=/home/code/ciftify:${PYTHONPATH} \
    CIFTIFY_TEMPLATES=/home/code/ciftify/ciftify/data

WORKDIR /tmp/

ENTRYPOINT ["/home/code/ciftify/ciftify/bidsapp/fmriprep_ciftify.py"]
