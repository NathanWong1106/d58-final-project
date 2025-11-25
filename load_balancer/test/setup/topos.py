import time
import uuid

from mininet.net import Mininet
from mininet.node import UserSwitch, OVSKernelSwitch, Controller
from mininet.topo import Topo
from mininet.log import lg, info
from mininet.util import irange, quietRun
from mininet.link import TCLink
from mininet.cli import CLI

from mininet.node import CPULimitedHost

# ----------------------------------------------------------------------------#
# CPU allocation constants
# Important notes:
# - When comparing topologies, ensure that the total number of clients is the same.
#   For example, if testing with 10 clients in multi-client-single-server topology, use 10 clients in multi-client-multi-server topology as well.
# - With SERVER_SINGLE_CPU set to 0.1, each server in multi-server topologies will have 10% CPU allocation. Since we don't have physical hardware
#   with dedicated resources, we can only add up to 4 servers before the next server becomes a bottleneck on the simulation.

CLIENT_CPU_TOT = 0.1  # TOTAL CPU allocation for all clients in multi-client topos
LB_CPU_TOT = 0.5  # CPU allocation for load balancer host
# Per-server CPU allocation in single server topo (up to 4 servers possible with this setting)
SERVER_SINGLE_CPU = 0.1
# --------------------------------------------------------------------------- #


class SingleClientMultiServer(Topo):
    """"Topology for 1 client and N server all connected through LB encapsulated by switches.

    C1 - S1 - LB - S2 - S1...SN

    """

    DEFAULT_LB_JSON = 'test/setup/default_test_lb.json'
    sid = {}

    def __init__(self, N=3):
        self.N = 3
        Topo.__init__(self)
        self.net = Mininet(topo=self, switch=OVSKernelSwitch,
                           controller=Controller, link=TCLink)

    # pylint: disable=arguments-differ

    def build(self):
        # Create switches and hosts
        servers = [self.addHost('s%s' % h, ip='10.0.1.%s/24' % h)
                   for h in irange(1, self.N)]
        client = self.addHost('c1', ip='10.0.0.1/24')
        lb = self.addHost('lb', ip='10.0.0.254/24')
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        self.addLink(client, client_switch)

        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)

        for server in servers:
            self.addLink(server, server_switch)

        self.sid['c1'] = str(uuid.uuid4())

    def get_client(self):
        return self.net.get('c1')

    def get_sid(self):
        return self.sid['c1']

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
            print(f"Starting server on {server.name} at IP {server.IP()}")
            server.cmd('ifconfig %s-eth0 %s/24 up' %
                       (server.name, server.IP()))
            server.cmd(
                f'python3 test/setup/test_server.py 80 "hello from {server.name}" &')

        # to make sure servers finish starting
        time.sleep(1)

        print("Starting LB")
        lb.cmd(
            f'python3 -u run_load_balancer.py {self.DEFAULT_LB_JSON} > lb.log 2>&1 &')


class MultiClientMultiServer(Topo):
    """
    Topology for M clients and N server all connected through LB encapsulated by switches.
    """

    DEFAULT_LB_JSON = 'test/setup/default_test_lb.json'
    sid = {}

    def __init__(self, num_clients=10, num_servers=3, client_cpu=CLIENT_CPU_TOT, server_cpus=None, lb_json=DEFAULT_LB_JSON):
        self.num_clients = num_clients
        self.num_servers = num_servers
        self.client_cpu = client_cpu
        self.server_cpus = server_cpus
        self.lb_json = lb_json

        if self.server_cpus is None:
            self.server_cpus = [SERVER_SINGLE_CPU for _ in range(num_servers)]

        Topo.__init__(self)
        self.net = Mininet(topo=self, switch=OVSKernelSwitch,
                           controller=Controller, link=TCLink)

    # pylint: disable=arguments-differ
    def build(self, M=10, N=3, **params):
        # Create switches and hosts
        servers = [self.addHost('s%s' % h, ip='10.0.1.%s/24' % h, cls=CPULimitedHost, cpu=self.server_cpus[h-1])
                   for h in irange(1, self.num_servers)]
        clients = [self.addHost('c%s' % h, ip='10.0.0.%s/24' % h, cls=CPULimitedHost, cpu=self.client_cpu/self.num_clients)
                   for h in irange(1, self.num_clients)]
        lb = self.addHost('lb', ip='10.0.0.254/24',
                          cls=CPULimitedHost, cpu=LB_CPU_TOT)
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        for client in clients:
            self.addLink(client, client_switch)

        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)

        for server in servers:
            self.addLink(server, server_switch)

        for client in clients:
            self.sid[client] = str(uuid.uuid4())

    def get_clients(self):
        clients = []
        for host in self.net.hosts:
            if host.name.startswith('c'):
                clients.append(host)
        return clients

    def get_sids(self):
        return self.sid

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
            print(f"Starting server on {server.name} at IP {server.IP()}")
            server.cmd('ifconfig %s-eth0 %s/24 up' %
                       (server.name, server.IP()))
            server.cmd(
                f'python3 test/setup/test_server.py 80 "hello from {server.name}" &')

        # to make sure servers finish starting
        time.sleep(2)

        print("Starting LB")
        lb.cmd(
            f'python3 -u run_load_balancer.py {self.lb_json} > lb.log 2>&1 &')

        # LB init time
        time.sleep(6)


class MultiClientSingleServer(Topo):
    """ 
    Topology for M clients and 1 server all connected through LB encapsulated by switches. 
    """

    DEFAULT_LB_JSON = 'test/setup/single_server_lb.json'
    sid = {}

    def __init__(self, num_clients=10, client_cpu=CLIENT_CPU_TOT, server_cpu=SERVER_SINGLE_CPU, lb_json=DEFAULT_LB_JSON):
        self.num_clients = num_clients
        self.client_cpu = client_cpu
        self.server_cpu = server_cpu
        self.lb_json = lb_json
        Topo.__init__(self)
        self.net = Mininet(topo=self, switch=OVSKernelSwitch,
                           controller=Controller, link=TCLink)

    def build(self, **params):
        # Create switches and hosts
        server = self.addHost('s1', ip='10.0.1.1/24',
                              cls=CPULimitedHost, cpu=self.server_cpu)
        clients = [self.addHost('c%s' % h, ip='10.0.0.%s/24' % h, cls=CPULimitedHost, cpu=self.client_cpu/self.num_clients)
                   for h in irange(1, self.num_clients)]
        lb = self.addHost('lb', ip='10.0.0.254/24',
                          cls=CPULimitedHost, cpu=LB_CPU_TOT)
        client_switch = self.addSwitch('sw1')
        server_switch = self.addSwitch('sw2')

        for client in clients:
            self.sid[client] = str(uuid.uuid4())
            self.addLink(client, client_switch)
        self.addLink(lb, client_switch)
        self.addLink(server_switch, lb)
        self.addLink(server, server_switch)

    def get_clients(self):
        clients = []
        for host in self.net.hosts:
            if host.name.startswith('c'):
                clients.append(host)
        return clients

    def get_server(self):
        return self.net.get('s1')

    def get_sids(self):
        return self.sid

    def get_load_balancer(self):
        return self.net.get('lb')

    def start_backend(self):
        """
        Start simple HTTP servers on all backend servers and load balancer.
        """

        lb = self.get_load_balancer()
        lb.cmd('ifconfig lb-eth1 10.0.1.254/24 up')

        server = self.get_server()
        print(f"Starting server on {server.name} at IP {server.IP()}")
        server.cmd('ifconfig %s-eth0 %s/24 up' % (server.name, server.IP()))
        server.cmd(
            f'python3 test/setup/test_server.py 80 "hello from {server.name}" &')

        # to make sure servers finish starting
        time.sleep(1)

        print("Starting LB")
        lb.cmd(
            f'python3 -u run_load_balancer.py {self.lb_json} > lb.log 2>&1 &')

        # LB init time
        time.sleep(6)
