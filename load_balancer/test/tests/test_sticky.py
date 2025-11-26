from test.setup.topos import MultiClientMultiServer
import time
import json
from mininet.log import lg
from mininet.cli import CLI


# Change value of "sticky_sessions" in setup file to view difference
def test_sticky():
    topo = MultiClientMultiServer(M=5, N=3)
    topo.start_backend()
    topo.net.start()

    time.sleep(2)

    clients = topo.get_clients()
    lb = topo.get_load_balancer()
    servers = topo.get_servers()
    sids = topo.get_sids()

    time.sleep(2)  # Wait for setup

    # Client sends requests every second for 20 seconds
    print("Sending reuqests to LB")
    for client in clients:
        client.cmd(
            f'timeout 30s bash -c "while true; do curl -s -H \'SID: {sids[str(client)]}\' http://{lb.IP()}; sleep 3; done" &')

    time.sleep(5)  # Let some requests go through

    # Now stop one server to test rerouting
    topo.net.get('c1').cmd('ifconfig c1-eth0 down')
    topo.net.get('c2').cmd('ifconfig c2-eth0 down')
    print("Stopped client 1 & 2 to test sticky session")

    # make sleep shorter/longer than STICKY_TIMEOUT to see mapping expiry
    time.sleep(15)  # Let more requests go through

    topo.net.get('c1').cmd('ifconfig c1-eth0 up')
    topo.net.get('c2').cmd('ifconfig c2-eth0 up')
    print("Started client 1 & 2 to test sticky session")

    time.sleep(11)

    topo.net.stop()


if __name__ == "__main__":
    lg.setLogLevel('info')
    test_sticky()
