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

class SingleClientMultiServer( Topo ):
    """"Topology for 1 client and N server all connected through LB encapsulated by switches.
    
    C1 - S1 - LB - S2 - S1...SN
    
    """

    DEFAULT_LB_JSON = 'test/setup/default_test_lb.json'

    def __init__( self ):
        Topo.__init__( self )
        self.net = Mininet(topo=self, switch=OVSKernelSwitch,
                       controller=Controller, link=TCLink)

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

    def get_client(self):
        return self.net.get('c1')
    
    def get_servers(self):
        servers = []
        for host in self.net.hosts:
            if host.name.startswith('s'):
                servers.append(host)
        return servers
    
    def get_load_balancer(self):
        return self.net.get('lb')
    
    def start_backend(self):
        """
        Start simple HTTP servers on all backend servers and load balancer.
        """

        lb = self.get_load_balancer()
        lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')

        servers = self.get_servers()
        for server in servers:
            print (f"Starting server on {server.name} at IP {server.IP()}")
            server.cmd(f'python3 test/setup/test_server.py 80 "hello from {server.name}" &')
            server.cmd(f'python3 server_health_agent.py &')

        lb.cmd(f'python3 run_load_balancer.py {self.DEFAULT_LB_JSON} > lb.log 2>&1 &')

    
        
