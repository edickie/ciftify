FROM jupyter/scipy-notebook

# Get connectome-workbench
RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/trusty.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.2.3-1~nd14.04+1

# Get ciftify
RUN apt-get update && \
    pip3 install -r ciftify


CMD ["jupyter-notebook"]
