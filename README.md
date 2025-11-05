# d58-final-project
Use ./setup.sh to start up pox

Then do

docker exec -it mininet-pox bash -c "mn --topo=single,3 --controller=remote,ip=127.0.0.1 --mac --switch=ovsk --link=tc"

to start up simple mininet topo

POX support for python3 is experimental, might have to down grade if necessary