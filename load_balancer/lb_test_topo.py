import sys
import time
import random

from functools import partial

from mininet.net import Mininet
from mininet.node import UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info
from mininet.util import irange, quietRun
from mininet.link import TCLink
from mininet.cli import CLI

from mininet.node import CPULimitedHost


flush = sys.stdout.flush

# test layers: 
# single client, single server
# single client, multi server
# multi cleint, multi server
# realistically, there would be switches between client and LB, and LB and server
class SingleClientMultiServer( Topo ):
    """"Topology for 1 client and N server all connected through LB encapsulated by switches.
    
    C1 - S1 - LB - S2 - S1...SN
    
    """

    # pylint: disable=arguments-differ
    def build( self, N=3, **params ):
        # Create switches and hosts 
        servers = [ self.addHost( 's%s' % h, ip='10.0.1.%s/24' % h )
                  for h in irange( 1, N ) ]
        client = self.addHost('c1', ip='10.0.0.1/24')
        lb = self.addHost('lb', ip='10.0.0.254/24')
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        self.addLink(client, client_switch)
        
        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)

        for server in servers:
          self.addLink( server, server_switch )
          
class MultiClientMultiServer( Topo ):
    """"Topology for N client and server all connected through LB encapsulated by switches.
    
    C1..CN - S1 - LB - S2 - S1...SN
    
    """

    # pylint: disable=arguments-differ
    def build( self, N=3, **params ):
        # Create switches and hosts 
        servers = [ self.addHost( 's%s' % h, ip='10.0.1.%s/24' % h )
                  for h in irange( 1, N ) ]
        clients = [ self.addHost( 'c%s' % h, ip='10.0.0.%s/24' % h )
                  for h in irange( 1, N ) ]
        lb = self.addHost('lb', ip='10.0.0.254/24')
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        for client in clients:
          self.addLink( client, client_switch )
        
        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)

        for server in servers:
          self.addLink( server, server_switch )

class ResourceBasedMultiServer( Topo ):
    """"Topology for N client and server all connected through LB encapsulated by switches.
    
    C1..CN - S1 - LB - S2 - S1...SN
    
    """

    # pylint: disable=arguments-differ
    def build( self, N=3, **params ):
        # Create switches and hosts 
        cpu_limits = [0.05, 0.5, 0.8]
        servers = [ self.addHost( 's%s' % h, ip='10.0.1.%s/24' % h, cpu=cpu_limits[(h-1)%3] )
                  for h in irange( 1, N ) ]

        clients = [ self.addHost( 'c%s' % h, ip='10.0.0.%s/24' % h )
                  for h in irange( 1, N ) ]
        
        lb = self.addHost('lb', ip='10.0.0.254/24')
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        for client in clients:
          self.addLink( client, client_switch )
        
        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)

        for server in servers:
          self.addLink( server, server_switch )
          
topos = {"SCMS" : SingleClientMultiServer}

def testSingleClient():
    topo = SingleClientMultiServer( 3 )
    net = Mininet( topo=topo, switch=OVSKernelSwitch,
                       controller=Controller, host=CPULimitedHost)
    net.start()
    
    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')
    
    net.get('s1').cmd('python3 fake_server.py 8080 &')
    net.get('s2').cmd('python3 fake_server.py 8081 &')
    net.get('s3').cmd('python3 fake_server.py 8082 &')

    
    lb.cmd('python3 -u dynamic_load_balancer.py > lb.log 2>&1 &')
    
    time.sleep(2)
    
    c1 = net.get('c1')
    
    for i in range(10):
        c1.cmd('curl -i http://10.0.0.254')
    
    net.stop()
    
def testMultiClient():
    topo = MultiClientMultiServer( 3 )
    net = Mininet( topo=topo, switch=OVSKernelSwitch,
                       controller=Controller)
    net.start()
    
    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')
    
    net.get('s1').cmd('python3 fake_server.py 8080 &')
    net.get('s2').cmd('python3 fake_server.py 8081 &')
    net.get('s3').cmd('python3 fake_server.py 8082 &')
    
    lb.cmd('python3 -u load_balancer.py > lb.log 2>&1 &')
    
    time.sleep(2)
    
    clients = []
    clients.append(net.get('c1'))
    clients.append(net.get('c2'))
    clients.append(net.get('c3'))
    
    
    procs = []
    for i in range(10):
        c = random.choice(clients)
        p = c.popen('curl -s http://10.0.0.254')
        procs.append((c, p))
    
    for c, p in procs:
        out, err = p.communicate()
        print(c.name, out.decode().strip(), err.decode().strip())
    
    net.stop()

def testDynamic():
    topo = ResourceBasedMultiServer( 3 )
    net = Mininet( topo=topo, switch=OVSKernelSwitch,
                       controller=Controller)
    net.start()
    
    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')
    
    net.get('s1').cmd('python3 fake_server.py 8000 &')
    net.get('s1').cmd('python3 health_agent.py &')
    net.get('s2').cmd('python3 fake_server.py 8000 &')
    net.get('s2').cmd('python3 health_agent.py &')
    net.get('s3').cmd('python3 fake_server.py 8000 &')
    net.get('s3').cmd('python3 health_agent.py &')

    # servers = [net.get('s1'), net.get('s2'), net.get('s3')]
    # for server in servers:
    #     server.setCPUFrac(0.5)

    lb.cmd('python3 -u dynamic_load_balancer.py > lb.log 2>&1 &')
    
    time.sleep(2)
    
    clients = []
    clients.append(net.get('c1'))
    clients.append(net.get('c2'))
    clients.append(net.get('c3'))
    
    # Clients send in parallel
    

    
    
    net.stop()


def testDynamicParallel():
    """Start topology and issue many concurrent requests from multiple clients."""
    topo = ResourceBasedMultiServer(3)
    net = Mininet(topo=topo, switch=OVSKernelSwitch, controller=Controller, host=CPULimitedHost)
    net.start()

    lb = net.get('lb')
    lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')

    # Start application servers and health agents on each server host
    net.get('s1').cmd('python3 fake_server.py 8000 &')
    net.get('s1').cmd('python3 health_agent.py &')
    net.get('s2').cmd('python3 fake_server.py 8000 &')
    net.get('s2').cmd('python3 health_agent.py &')
    net.get('s3').cmd('python3 fake_server.py 8000 &')
    net.get('s3').cmd('python3 health_agent.py &')

    # start the dynamic load balancer on the lb host
    lb.cmd('python3 -u dynamic_load_balancer.py > /tmp/lb.log 2>&1 &')

    time.sleep(3)  # give LB and agents time to start and initial polls to happen

    clients = [net.get('c1'), net.get('c2'), net.get('c3')]

    # Spawn many requests in parallel from the clients
    num_requests = 60
    procs = []
    for i in range(num_requests):
        c = random.choice(clients)
        # use popen so requests run concurrently
        p = c.popen(['curl', '-s', 'http://10.0.0.254'])
        procs.append((c, p))

    # Collect results
    success = 0
    for c, p in procs:
        try:
            out, err = p.communicate(timeout=10)
            if out:
                success += 1
            print(f"{c.name}: {out.decode().strip()}")
        except Exception as e:
            print(f"{c.name}: request failed: {e}")

    print(f"Completed {len(procs)} requests, {success} successful responses")

    net.stop()

#Choose topo
if __name__ == '__main__':
    testDynamicParallel()