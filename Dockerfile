FROM mmanogaran/ciftify_ci:0.1

# Set ciftify environment variables
ENV PATH=/home/code/ciftify/ciftify/bin:${PATH} \
    PYTHONPATH=/home/code/ciftify:${PYTHONPATH} \
    CIFTIFY_TEMPLATES=/home/code/ciftify/ciftify/data

# Get ciftify
RUN mkdir /home/code && \
    git clone -b devel https://github.com/edickie/ciftify.git /home/code/ciftify

# Get python requirments
COPY cifti_requirements.txt cifti_requirements.txt

RUN apt-get update && \
    pip3 install -r cifti_requirements.txt

# Setting workdir to /tmp for singularity
WORKDIR /tmp/

CMD ["/bin/bash"]
