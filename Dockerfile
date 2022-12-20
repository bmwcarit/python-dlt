ARG BASE_IMAGE=alpine:3.17
FROM ${BASE_IMAGE}

ARG LIBDLT_VERSION=v2.18.8

RUN set -ex \
    && apk add --no-cache build-base musl-dev linux-headers git cmake ninja \
      wget curl dbus zlib \
      python3 python3-dev py3-pip py3-tox \
    && git clone https://github.com/GENIVI/dlt-daemon \
    && cd /dlt-daemon \
    && git checkout ${LIBDLT_VERSION} \
    && cd /dlt-daemon \
    && cmake CMakeLists.txt \
    && make -j \
    && make install \
    && ldconfig /usr/local/lib

RUN mkdir -p /workspace

WORKDIR /workspace

# vim: set ft=dockerfile :
