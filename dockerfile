FROM ubuntu:22.04

WORKDIR /load_balancer

# Install dependencies
RUN apt update && apt install -y \
    mininet \
    iproute2 \
    iputils-ping \
    net-tools \
    traceroute \
    wget \
    build-essential \
    git \
    sudo \
    gcc \
    python3 python3-pip \
    python-setuptools \
    curl \
    openvswitch-switch openvswitch-testcontroller

RUN pip3 install --no-cache-dir requests

CMD [ "/bin/bash" ]
