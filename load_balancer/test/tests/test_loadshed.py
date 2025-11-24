from test.setup.topos import MultiClientMultiServer
import time
import threading
import typing

# Note that this test is fairly flaky due to the nature of timing and load shedding.
# Results may vary between runs. Taking the average between runs is recommended.

LOAD_DURATION = 20 # seconds
NUM_CLIENTS = 60 # number of clients to simulate
CLIENT_CPU = 0.4 # CPU allocation for all clients
NUM_SERVERS = 3
SERVER_CPUS = [0.03, 0.01, 0.01] # CPU allocation for each server (in this config, servers are under-provisioned and can handle at most 10 connections total simultaneously)

class RequestResult:
    def __init__(self, response: str, latency: float):
        self.response = response
        self.latency = latency

    def is_successful(self):
        return "200" in self.response
    
    def is_timeout(self):
        return "504" in self.response or "timed out" in self.response.lower()
    
    def was_shed(self):
        return "503" in self.response and "Service Unavailable" in self.response
    
    def was_server_error(self):
        return "502" in self.response or "500" in self.response
    
def results_summary(results: typing.List[RequestResult]):
    total_requests = len(results)
    total_successful_requests = sum(1 for r in results if r.is_successful())
    total_timeouts = sum(1 for r in results if r.is_timeout())
    total_shed = sum(1 for r in results if r.was_shed())
    total_server_errors = sum(1 for r in results if r.was_server_error())
    avg_non_shed_latency = sum(r.latency for r in results if not r.was_shed()) / max(1, sum(1 for r in results if not r.was_shed()))

    print(f"Total requests sent: {total_requests}"
          f"\nTotal successful responses (200): {total_successful_requests}"
            f"\nTotal timeouts (504 or curl timeout): {total_timeouts}"
            f"\nTotal shed responses (503): {total_shed}"
            f"\nTotal server errors (502/500): {total_server_errors}"
            f"\nAverage latency (excluding shed requests): {avg_non_shed_latency:.3f} seconds")

def send_requests(c, lock, results, lb):
    end_time = time.time() + LOAD_DURATION
    while time.time() < end_time:
        start_time = time.time()
        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(f'curl --max-time 6 -i http://{lb.IP()}')
        latency = time.time() - start_time
        with lock:
            results.append(RequestResult(resp, latency))
        
        # tiny pause to create a stream of requests
        time.sleep(0.02)

def test_no_load_shedding():
    """
    In this test, we simulate a scenario where the load balancer does not shed load, leading to server overload. Other clients continue to pile on requests,
    resulting in degraded performance for all.

    We expect request timeouts, increased latencies, and failed requests as the server becomes overwhelmed.
    """

    topo = MultiClientMultiServer(num_clients=NUM_CLIENTS, num_servers=NUM_SERVERS, client_cpu=CLIENT_CPU, server_cpus=SERVER_CPUS, lb_json='test/setup/default_test_lb.json')
    topo.start_backend()
    topo.net.start()

    time.sleep(6) # wait for LB and servers to stabilize

    clients = topo.get_clients()
    
    # Shared results and counters
    lock = threading.Lock()
    results = []

    print("Starting no load shedding test")
    threads = []
    for client in clients:
        t = threading.Thread(target=send_requests, args=(client, lock, results, topo.get_load_balancer()))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    topo.net.stop()
    print("Test completed.")

    return results

    
def test_load_shedding():
    """
    In this test, we simulate a scenario where the load balancer employs load shedding to prevent server overload. 
    The load balancer will reject requests when the number of simultaneous connections exceeds a certain threshold (10). 

    We expect fewer timeouts and failed requests compared to the no load shedding scenario, as well as lower latencies.
    """

    topo = MultiClientMultiServer(num_clients=NUM_CLIENTS, num_servers=NUM_SERVERS, client_cpu=CLIENT_CPU, server_cpus=SERVER_CPUS, lb_json='test/setup/load_shed_test_lb.json')
    topo.start_backend()
    topo.net.start()

    time.sleep(6) # wait for LB and servers to stabilize

    clients = topo.get_clients()
    
    # Shared results and counters
    lock = threading.Lock()
    results = []

    print("Starting load shedding test")
    threads = []
    for client in clients:
        t = threading.Thread(target=send_requests, args=(client, lock, results, topo.get_load_balancer()))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    topo.net.stop()
    print("Test completed.")

    return results


if __name__ == "__main__":
    no_shed_test_results = test_no_load_shedding()
    shed_test_results = test_load_shedding()

    print("\n--- No Load Shedding Test Results ---")
    results_summary(no_shed_test_results)

    print("\n--- Load Shedding Test Results ---")
    results_summary(shed_test_results)