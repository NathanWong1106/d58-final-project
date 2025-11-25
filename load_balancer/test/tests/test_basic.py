import time

from test.setup.topos import SingleClientMultiServer
from mininet.log import lg

def testBasic():
    topo = SingleClientMultiServer()
    topo.start_backend()
    topo.net.start()

    client = topo.get_client()
    sid = topo.get_sid()
    lb = topo.get_load_balancer()

    time.sleep(2)

    results = []
    # Send requests for 20 seconds
    end_time = time.time() + 5
    while time.time() < end_time:
        response = client.cmd(f'curl -s -H "SID: {sid}" http://{lb.IP()}')
        results.append(response.strip())

    topo.net.stop()
    print(results)

if __name__ == "__main__":
    lg.setLogLevel('info')
    testBasic()