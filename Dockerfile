FROM debian:buster as builder

ARG LIBDLT_VERSION=2.18.4

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y build-essential git cmake libdbus-1-dev cmake-data \
            libdbus-1-dev systemd libsystemd-dev wget curl zlib1g-dev

# Install libdlt
RUN git clone https://github.com/GENIVI/dlt-daemon \
    && cd /dlt-daemon \
    && git checkout v${LIBDLT_VERSION} \
    && cd /dlt-daemon \
    && cmake CMakeLists.txt \
    && make \
    && make install

FROM debian:buster

# Install libdlt.so
COPY --from=builder /usr/local/lib /usr/local/lib

RUN ldconfig

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y python3 python3-pip python2 python2-dev git \
    && pip3 install --no-cache-dir setuptools tox \
    && apt-get clean all \
    && rm -rf \
           /var/cache/debconf/* \
           /var/lib/apt/lists/* \
           /var/log/* \
           /tmp/* \
           /var/tmp/*

# vim: set ft=dockerfile :
