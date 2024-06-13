FROM ubuntu:18.04
ARG STAGE_DIR=/tmp/xapp MDC_VER=0.0.4-1 RMR_VER=4.4.6 ASN1C_VER=0.1.0 RNIB_VER=1.0.0

WORKDIR ${STAGE_DIR}
RUN apt-get update && apt-get install -y \
    cmake \
    git \
    build-essential \
    automake \
    autoconf-archive \
    autoconf \
    pkg-config \
    gawk \
    libtool \
    wget \
    zlib1g-dev \
    libffi-dev \
    libcurl4-openssl-dev \
    vim \
    cpputest \
    libboost-all-dev \
    software-properties-common \
    libhiredis-dev \
    valgrind \
    curl \
    netcat \
    tmux \
    jq \
    nano \
    # Install Python3.8
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get -qq remove --purge -y python* \
    && apt-get update && apt-get install -y \
        python3.8 \
        python3.8-distutils \
    && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python3.8 get-pip.py \
    && python3.8 -m pip --no-cache-dir install -U pip \
    && python3.8 -m pip install --no-cache-dir \
        requests \
        setuptools \
        protobuf==3.20.0  \
    && ln -s /usr/bin/python3.8 /usr/bin/python \
    && rm get-pip.py \
    && rm -rf /var/lib/apt/lists/* \
    # Install mdclog using debian package hosted at packagecloud.io
    && wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/mdclog_${MDC_VER}_amd64.deb/download.deb \
    && wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/mdclog-dev_${MDC_VER}_amd64.deb/download.deb \
    && dpkg -i mdclog_${MDC_VER}_amd64.deb \
    && dpkg -i mdclog-dev_${MDC_VER}_amd64.deb \
    # Install RMR using debian package hosted at packagecloud.io
    && wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/rmr_${RMR_VER}_amd64.deb/download.deb \
    && wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/rmr-dev_${RMR_VER}_amd64.deb/download.deb \
    && dpkg -i rmr_${RMR_VER}_amd64.deb \
    && dpkg -i rmr-dev_${RMR_VER}_amd64.deb \
    # Install ASN1C library package hosted at packagecloud.io
    && wget --content-disposition https://packagecloud.io/o-ran-sc/staging/packages/debian/stretch/riclibe2ap_${ASN1C_VER}_amd64.deb/download.deb \
    && wget --content-disposition https://packagecloud.io/o-ran-sc/staging/packages/debian/stretch/riclibe2ap-dev_${ASN1C_VER}_amd64.deb/download.deb \
    && dpkg -i riclibe2ap_${ASN1C_VER}_amd64.deb \
    && dpkg -i riclibe2ap-dev_${ASN1C_VER}_amd64.deb \
    # Install RNIB libraries
    && wget -nv --content-disposition https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/rnib_${RNIB_VER}_all.deb/download.deb \
    && dpkg -i rnib_${RNIB_VER}_all.deb \
    && git clone https://gerrit.o-ran-sc.org/r/ric-plt/dbaas \
    && cd dbaas/redismodule \
    && ./autogen.sh \
    && ./configure \
    && make -j ${nproc} all \
    && make install \
    # Install sdl
    && cd ${STAGE_DIR} \
    && git clone https://gerrit.o-ran-sc.org/r/ric-plt/sdl \
    && cd sdl \
    && ./autogen.sh \
    && ./configure \
    && make -j ${nproc} all \
    && make install \
    # Install rapidjson
    && cd ${STAGE_DIR} \
    && git clone https://github.com/Tencent/rapidjson \
    && cd rapidjson \
    && mkdir build \
    && cd build \
    && cmake -DCMAKE_INSTALL_PREFIX=/usr/local .. \
    && make -j ${nproc} \
    && make install \
    && ldconfig \
    # Install Nlohmann JSON library
    && cd ${STAGE_DIR} \
    && git clone https://github.com/nlohmann/json.git \
    && cd json/ \
    && mkdir build \
    && cd build/ \
    && cmake .. \
    && make -j ${nproc} \
    && make install \
    && ldconfig \
    && cd ${STAGE_DIR} \
    && rm -Rf json/

WORKDIR /root/
RUN   git clone --branch kpm-xapp --single-branch https://github.com/wineslab/xapp-oai.git  \
      && cd xapp-oai/xapp-bs-connector \
      && sed -i 's/bool using_protobuf = false;/bool using_protobuf = true;/' src/hw_xapp_main.cc \
      && cd src && make clean \
      && make -j ${nproc} \
      && make install \
      && ldconfig \
      # this fixes some subscription errors in this RIC release - TO BE FIXED
      && sed -i 's/rte|12010|service-ricplt-e2term-rmr-alpha.ricplt:38000/rte|12010|service-ricplt-submgr-rmr.ricplt:4560/g' /root/xapp-oai/xapp-bs-connector/init/routes.txt
     

ENV  RMR_RTG_SVC="9999" \
     RMR_SEED_RT="/root/xapp-oai/xapp_bs_connector/init/routes.txt" \
     LD_LIBRARY_PATH="/usr/local/lib:/usr/local/libexec" \
     VERBOSE=0 \
     CONFIG_FILE="/opt/ric/config/config-file.json"

CMD /bin/sleep infinity
