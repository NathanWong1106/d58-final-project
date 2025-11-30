#!/bin/bash

# Install necessary packages
apt update && apt install -y \
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

pip3 install --upgrade pip
pip3 install matplotlib