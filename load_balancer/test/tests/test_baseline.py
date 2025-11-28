from test.setup.topos import MultiClientSingleServer
import time
import threading
from test.tests.send_request_helper import send_requests


def test_baseline():
    """
    In this baseline test, we set up a single server behind the load balancer and have multiple clients send requests.
    """

    topo = MultiClientSingleServer()
    topo.start_backend()
    topo.net.start()

    time.sleep(6)  # wait for LB and servers to stabilize

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    results = []
    lock = threading.Lock()

    print("Starting baseline test without load shedding")
    threads = []
    end_time = time.time() + 20  # Run for 20 seconds
    for client in clients:
        t = threading.Thread(target=send_requests, args=(client, lock, results, lb, end_time))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    topo.net.stop()
    print("Test completed.")
    return results