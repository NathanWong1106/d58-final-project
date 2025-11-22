from test.setup.topos import MultiClientSingleServer
import time
import threading
from mininet.log import lg

def test_no_load_shedding():
    """
    In this test we simulate heavy load without shedding.

    We expect the server to fail under this load.
    """
    
    topo = MultiClientSingleServer(num_clients=100, client_cpu=0.4, server_cpu=0.1)
    topo.start_backend()
    topo.net.start()

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    # Shared results and counters
    lock = threading.Lock()
    results = {client.name: [] for client in clients}
    failures_per_client = {client.name: 0 for client in clients}

    duration = 30
    end_time = time.time() + duration

    def send_requests(c):
        while time.time() < end_time:
            # send a simple HTTP request to the LB and capture headers+body
            resp = c.cmd(f'curl --max-time 3 -s -i http://{lb.IP()}')
            with lock:
                results[c.name].append(resp)
                if "503" in resp and "Service Unavailable" in resp:
                    failures_per_client[c.name] += 1
            # tiny pause to create a stream of requests
            time.sleep(0.02)

    print("Starting heavy load test with no load shedding: server failure is expected")
    threads = []
    for client in clients:
        t = threading.Thread(target=send_requests, args=(client,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    topo.net.stop()

    total_sent = sum(len(v) for v in results.values())
    total_failures = sum(failures_per_client.values())

    print(f"Total requests sent: {total_sent}")
    print(f"Total failure responses: {total_failures}")

    assert total_failures > 0, "Expected server to fail but it did not."


def test_load_shedding():
    """
    In this test we simulate load shedding behavior of the load balancer.

    We first ensure that under light load, no requests are rejected.

    Then we simulate heavy load with 100 clients sending requests concurrently.
    We test that some requests are rejected due to the LB shedding load from the sudden increase in traffic.
    """

    # Realistically, the server below is under-provisioned WRT clients. We set quite aggressive shedding parameters in this JSON to respond to that.
    # If it wasn't aggressive, the server would fail (and since the point of this test to gracefully shed load, we should expect the server to remain stable)
    LB_JSON = 'test/setup/load_shed_test_lb.json'

    # We increase the number of clients to 100 to simulate heavy load and give more cpu allocation to clients and less to the server
    # to simulate a realistic overload scenario
    topo = MultiClientSingleServer(num_clients=100, client_cpu=0.4, server_cpu=0.1, lb_json=LB_JSON)
    topo.start_backend()
    topo.net.start()

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    time.sleep(6)
    
    # First sanity check: ensure that under light load (single client sending requests slowly), no requests are rejected
    c1 = clients[0]
    duration = 5
    end_time = time.time() + duration

    print("Starting light load test with load shedding: no rejections expected")
    while time.time() < end_time:
        resp = c1.cmd(f'curl --max-time 3 -s -i http://{lb.IP()}')
        assert ("503" not in resp)
        time.sleep(0.5)


    # Shared results and counters
    lock = threading.Lock()
    results = {client.name: [] for client in clients}
    rejected_per_client = {client.name: 0 for client in clients}
    failures_per_client = {client.name: 0 for client in clients}

    # Run a heavy load for a short period to trigger shedding
    duration = 30
    end_time = time.time() + duration

    def send_requests(c):
        while time.time() < end_time:
            # send a simple HTTP request to the LB and capture headers+body
            resp = c.cmd(f'curl --max-time 3 -s -i http://{lb.IP()}')
            with lock:
                results[c.name].append(resp)
                if "503" in resp and "The server is currently experiencing high load" in resp:
                    rejected_per_client[c.name] += 1
                elif "503" in resp and "Service Unavailable" in resp:
                    failures_per_client[c.name] += 1
            # tiny pause to create a stream of requests
            time.sleep(0.02)

    print("Starting heavy load test with load shedding: some rejections expected but no failures expected")
    threads = []
    for client in clients:
        t = threading.Thread(target=send_requests, args=(client,))
        t.start()
        threads.append(t)

    # Wait for load phase to complete
    for t in threads:
        t.join()

    topo.net.stop()

    total_sent = sum(len(v) for v in results.values())
    total_rejected = sum(rejected_per_client.values())
    total_failures = sum(failures_per_client.values())

    print(f"Total requests sent: {total_sent}")
    print(f"Total rejected responses: {total_rejected}")
    print(f"Total failure responses: {total_failures}")
    print(f"Percentage of rejected responses: {100 * total_rejected / total_sent:.2f}%")
    print(f"Percentage of failure responses: {100 * total_failures / total_sent:.2f}%")

    # We should have sent requests and seen at least some rejections
    assert total_sent > 0, "No requests were sent in the test"
    assert total_rejected > 0, "Expected some rejected responses (load shedding) but none were observed"
    assert total_failures == 0, "Expected no failure responses but some were observed"

if __name__ == "__main__":
    lg.setLogLevel('info')
    test_no_load_shedding()
    test_load_shedding()