from lb_test_topo import MultiClientMultiServer, ResourceLimitedMultiClientMultiServer

import sys
import time
import random

from functools import partial

from mininet.net import Mininet
from mininet.node import UserSwitch, OVSKernelSwitch, Controller, CPULimitedHost
from mininet.topo import Topo
from mininet.log import lg, info
from mininet.util import irange, quietRun
from mininet.link import TCLink
from mininet.cli import CLI

def test_server_down():
    topo = MultiClientMultiServer(N=3)
    net = Mininet(topo=topo, switch=OVSKernelSwitch, controller=Controller, link=TCLink)

    net.start()

    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')

    net.get('s1').cmd('python3 fake_server.py 8000 &')
    net.get('s1').cmd('python3 health_agent.py &')
    net.get('s2').cmd('python3 fake_server.py 8000 &')
    net.get('s2').cmd('python3 health_agent.py &')
    net.get('s3').cmd('python3 fake_server.py 8000 &')
    net.get('s3').cmd('python3 health_agent.py &')

    lb.cmd('python3 -u dynamic_load_balancer.py > lb.log 2>&1 &')
    
    time.sleep(2)

    clients = [net.get('c1'), net.get('c2'), net.get('c3')]
    
    # Start clients: 30s of requests
    start_cmd = 'timeout 30s bash -c "while true; do curl -sS http://10.0.0.254/ > /dev/null; done" &'
    info('Starting clients to send simultaneously for 30s\n')
    for c in clients:
        c.cmd(start_cmd)

    # Wait 15s (halfway), then take down hosts s1 and s3
    time.sleep(15)
    info('Taking down hosts s1 and s3 (halfway through) by disabling links to sw2\n')
    # This simulates the entire host going offline in Mininet
    net.get('s1').cmd('ifconfig s1-eth0 down')
    net.get('s3').cmd('ifconfig s3-eth0 down')

    # Allow remaining time for clients to finish
    time.sleep(16)

    info('Clients finished; stopping network\n')
    net.stop()

def test_server_busy():
    topo = ResourceLimitedMultiClientMultiServer(server_cpu=[0.4, 0.1, 0.1], lb_cpu=0.5)
    net = Mininet(topo=topo, host=CPULimitedHost, switch=OVSKernelSwitch, controller=Controller, link=TCLink, autoPinCpus=True)

    net.start()

    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')

    net.get('s1').cmd('python3 fake_server.py 8000 &')
    net.get('s1').cmd('python3 health_agent.py &')
    net.get('s2').cmd('python3 fake_server.py 8000 &')
    net.get('s2').cmd('python3 health_agent.py &')
    net.get('s3').cmd('python3 fake_server.py 8000 &')
    net.get('s3').cmd('python3 health_agent.py &')

    lb.cmd('python3 -u dynamic_load_balancer.py > lb.log 2>&1 &')

    time.sleep(2)

    clients = [net.get('c1'), net.get('c2'), net.get('c3')]

    # Start clients: 30s of requests
    start_cmd = 'timeout 30s bash -c "while true; do curl -sS http://10.0.0.254/ > /dev/null; done" &'
    info('Starting clients to send simultaneously for 30s\n')
    for c in clients:
        c.cmd(start_cmd)

    # Wait 5s, then overload host s2
    time.sleep(15)
    info('Overloading host s2 (halfway through) by starting CPU-intensive process\n')
    # This simulates high CPU load on the host in Mininet
    net.get('s2').cmd('yes > /dev/null &')

    # Allow remaining time for clients to finish
    time.sleep(16)
    info('Clients finished; stopping network\n')
    net.stop()

def load_test():
    topo = ResourceLimitedMultiClientMultiServer(N_serv=3, N_clients=1, server_cpu=[0.8, 0.1, 0.1], lb_cpu=1)
    net = Mininet(topo=topo, host=CPULimitedHost, switch=OVSKernelSwitch, controller=Controller, link=TCLink)
    net.start()

    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')
    for i in range(1,4):
        server = net.get(f's{i}')
        server.cmd('python3 fake_server.py 8000 &')
        server.cmd('python3 health_agent.py &')
    lb.cmd('python3 -u dynamic_load_balancer.py > lb.log 2>&1 &')

    # time.sleep(5)

    # client = net.get('c1')
    # output = client.cmd('locust --headless --users 10 --spawn-rate 2 --host http://10.0.0.254 &')

    # time.sleep(60)

    CLI(net)
    net.stop()



if __name__ == '__main__':
    lg.setLogLevel('info')
    load_test()


