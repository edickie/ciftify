FROM jupyter/scipy-notebook

USER root

# Get connectome-workbench
RUN apt-get update && \
    apt-get install -y curl gnupg gnupg1 gnupg2 python3-pip

# Set up Bioconda
RUN conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda install -c bioconda/label/cf201901 connectome-workbench

# Get ciftify
RUN apt-get update && \
    apt-get install -y git-annex && \
    pip install ciftify datalad

CMD ["jupyter lab"]
