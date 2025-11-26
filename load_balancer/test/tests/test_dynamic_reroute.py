from test.setup.topos import MultiClientMultiServer
import time
from mininet.log import lg
from mininet.cli import CLI


def test_reroute():
    topo = MultiClientMultiServer()
    topo.start_backend()
    topo.net.start()

    time.sleep(2)

    clients = topo.get_clients()
    lb = topo.get_load_balancer()
    servers = topo.get_servers()

    time.sleep(2)  # Wait for setup

    # Client sends requests every second for 20 seconds
    print("Sending reuqests to LB")
    for client in clients:
        client.cmd(
            f'timeout 30s bash -c "while true; do curl http://{lb.IP()}; sleep 3; done" &')

    time.sleep(5)  # Let some requests go through

    # Now stop one server to test rerouting
    topo.net.get('s3').cmd('ifconfig s3-eth0 down')
    print("Stopped server 3 to test rerouting")

    time.sleep(15)  # Let more requests go through

    topo.net.get('s3').cmd('ifconfig s3-eth0 up')
    print("Started server 3 to test rerouting")

    time.sleep(11)

    topo.net.stop()


if __name__ == "__main__":
    lg.setLogLevel('info')
    test_reroute()
