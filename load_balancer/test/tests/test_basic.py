import os
import sys

from test.setup.topos import SingleClientMultiServer
from mininet.log import lg

def testBasic():
    topo = SingleClientMultiServer()
    topo.start_backend()
    topo.net.start()

    client = topo.get_client()
    lb = topo.get_load_balancer()

    results = []
    for _ in range(10):
        result = client.cmd(f'curl http://{lb.IP()}')
        results.append(result.strip())

    topo.net.stop()
    print(results)

if __name__ == "__main__":
    lg.setLogLevel('info')
    testBasic()