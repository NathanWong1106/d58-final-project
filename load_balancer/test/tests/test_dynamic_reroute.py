from test.setup.topos import MultiClientMultiServer
import time
import threading
from test.tests.req_result_obj import RequestResult, results_summary
from mininet.log import lg
from mininet.cli import CLI

DURATION = 20


def send_requests(c, lock, results, lb):
    end_time = time.time() + DURATION
    while time.time() < end_time:
        start_time = time.time()

        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(
            f'curl --max-time 5 -i http://{lb.IP()}')
        with lock:
            results.append(RequestResult(resp, start_time, time.time()))

        # tiny pause to create a stream of requests
        time.sleep(0.4)

def test_reroute():
    topo = MultiClientMultiServer(num_clients=3, num_servers=3,
                                  lb_json='test/setup/hashing_test_lb.json')
    topo.start_backend()
    topo.net.start()

    time.sleep(10)

    clients = topo.get_clients()
    lb = topo.get_load_balancer()
    servers = topo.get_servers()

    time.sleep(2)  # Wait for setup

    # Shared results and counters
    lock = threading.Lock()
    results = []

    print("Starting reroute test")
    threads = []
    for client in clients:
        t = threading.Thread(target=send_requests, args=(
            client, lock, results, topo.get_load_balancer()))
        t.start()
        threads.append(t)

    time.sleep(5)  # Let some requests go through

    # Now stop one server to test rerouting
    topo.net.get('s3').cmd('ifconfig s3-eth0 down')
    print("Stopped server 3 to test rerouting")

    time.sleep(10)  # Let more requests go through

    topo.net.get('s3').cmd('ifconfig s3-eth0 up')
    print("Started server 3 to test rerouting")

    time.sleep(6)

    for t in threads:
        t.join()

    topo.net.stop()
    print("Test completed.")

    return results


if __name__ == "__main__":
    lg.setLogLevel('info')
    results_summary(test_reroute())
