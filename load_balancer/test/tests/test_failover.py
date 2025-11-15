from test.setup.topos import SingleClientMultiServer
import time
from mininet.log import lg
from mininet.cli import CLI

def test_failover():
    topo = SingleClientMultiServer()
    topo.start_backend()
    topo.net.start()

    client = topo.get_client()
    lb = topo.get_load_balancer()
    s1 = topo.get_servers()[0]

    time.sleep(2)  # Wait for setup
    
    # Client sends requests every second for 20 seconds
    client.cmd(f'timeout 20s bash -c "while true; do curl http://{lb.IP()}; sleep 1; done &"')

    time.sleep(5)  # Let some requests go through

    # Now stop one server to test failover
    topo.net.get('s1').cmd('ifconfig s1-eth0 down')
    print("Stopped server 1 to test failover")

    time.sleep(15)  # Let more requests go through

    topo.net.stop()

if __name__ == "__main__":
    lg.setLogLevel('info')
    test_failover()