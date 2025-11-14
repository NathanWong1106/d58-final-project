sudo apt update && sudo apt install -y \
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

sudo pip install --upgrade pip
sudo pip install requests
sudo pip install psutil

# Start openswitch service
service openvswitch-switch start

# Other stuff to try:

# sudo apt-get install gcc python-dev?

# sudo pip install --upgrade pip

# sudo apt-get --purge autoremove python3-pip

#  sudo apt install python3-pip

# python3.8 -m pip install psutil

# Might need to do SUDO pip install instead of pip install