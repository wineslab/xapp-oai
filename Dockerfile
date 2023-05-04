FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    git \
    python3.8 \
    python3-pip \
    protobuf-compiler

# install protobuf python module
RUN python3 -m pip install protobuf==3.20.*

# clone repo
ARG CACHEBUST=1
RUN git clone https://github.com/ANTLab-polimi/xapp-oai.git /xapp-oai
WORKDIR /xapp-oai

# checkout mrn-base
RUN git checkout mrn-base

# synch submodules
RUN chmod +x submodule-sync.sh
RUN ./submodule-sync.sh

ENTRYPOINT ["/bin/bash"]
