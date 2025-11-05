#!/bin/bash

echo "pox/*" > .dockerignore

# work around for wsl
if [ ! -d "pox" ]; then
  mkdir temp
  cd temp/
  git clone https://github.com/noxrepo/pox.git
  mv pox ..
  cd ..
  rm -rf temp
fi
cp pox-ext/load_balancer.py pox/ext/

docker compose build
docker compose up -d
docker exec -it mininet-pox bash -c "service openvswitch-switch start"

# starts pox controller with debug msgs, openflow to connect to mininet, and prebuilt ethernet forwarding, and use custome load balancer
docker exec -it mininet-pox bash -c "cd /D58-FINAL-PROJECT/pox && python3 pox.py log.level --DEBUG openflow.of_01 --port=6653 forwarding.l2_learning load_balancer"

# ext.load_balancer 
# sleep 3

#starts mininet with a simple topo
# docker exec -it mininet-pox bash -c "mn --topo=single,3 --controller=remote,ip=127.0.0.1 --mac --switch=ovsk --link=tc"