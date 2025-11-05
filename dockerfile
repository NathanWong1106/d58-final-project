FROM ubuntu:20.04

WORKDIR /D58-FINAL-PROJECT

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
  openvswitch-switch
RUN service openvswitch-switch start
# RUN git clone https://github.com/noxrepo/pox.git /D58-FINAL-PROJECT/pox
# COPY ./pox-ext /D58-FINAL-PROJECT/pox/ext

# EXPOSE 6633 6653

# ENTRYPOINT ["bash", "/D58-FINAL-PROJECT/start.sh"]
CMD [ "/bin/bash" ]