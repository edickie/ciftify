FROM jupyter/scipy-notebook

USER root

# Get connectome-workbench
RUN apt-get update && \
    apt-get install -y curl gnupg gnupg1 gnupg2 python3-pip

# Set up Bioconda
RUN conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda install -c bioconda connectome-workbench

# Get ciftify
RUN apt-get update && \
    sudo -H pip3 install ciftify datalad

CMD ["jupyter lab"]
