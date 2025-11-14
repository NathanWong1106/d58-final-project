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

pip install --upgrade pip
pip install --no-cache-dir requests
pip install --no-cache-dir psutil

# Start openswitch service
service openvswitch-switch start

# sudo apt-get install gcc python-dev?

# pip install --upgrade-pip?