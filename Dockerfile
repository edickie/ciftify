FROM jupyter/scipy-notebook

USER root

# Get connectome-workbench
RUN apt-get update && \
    apt-get install -y curl gnupg gnupg1 gnupg2 python3-pip 
    
RUN apt-get update && \
    curl -sSL http://neuro.debian.net/lists/xenial.us-ca.full >> /etc/apt/sources.list.d/neurodebian.sources.list && \
    apt-key adv --recv-keys --keyserver hkp://pool.sks-keyservers.net:80 0xA5D32F012649A5A9 && \
    apt-get update && \
    apt-get install -y connectome-workbench=1.3.1-1~nd16.04+1


# Get ciftify
RUN apt-get update && \
    sudo -H pip3 install ciftify datalad

CMD ["jupyter lab"]
