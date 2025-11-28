from test.setup.topos import MultiClientMultiServer
import time
import threading
from test.tests.req_result_obj import RequestResult, results_summary, plot_latency_over_time, plot_successful_requests_over_time, plot_errors_over_time

# Note that this test is fairly flaky due to the nature of timing and load shedding.
# Results may vary between runs. Taking the average between runs is recommended.
# Sample output from one run:
# --- No Load Shedding Test Results ---
# Total requests sent: 437
# Total successful responses (200): 136
# Total timeouts (504 or curl timeout): 23
# Total shed responses (503): 0
# Total server errors (502/500): 277
# Average latency of successful requests: 3.361 seconds

# --- Load Shedding Test Results ---
# Total requests sent: 2429
# Total successful responses (200): 145
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 2256
# Total server errors (502/500): 0
# Average latency of successful requests: 1.228 seconds

# --- Exponential Load Shedding Test Results ---
# Total requests sent: 2118
# Total successful responses (200): 139
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 1951
# Total server errors (502/500): 2
# Average latency of successful requests: 2.483 seconds


LOAD_DURATION = 20 # seconds
NUM_CLIENTS = 60 # number of clients to simulate
CLIENT_CPU = 0.4 # CPU allocation for all clients
NUM_SERVERS = 3
SERVER_CPUS = [0.03, 0.03, 0.03] # CPU allocation for each server (in this config, servers are under-provisioned and can handle at most 5-7 connections total simultaneously)

def send_requests(c, lock, results, lb):
    end_time = time.time() + LOAD_DURATION
    while time.time() < end_time:
        start_time = time.time()
        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(f'curl --max-time 6 -i http://{lb.IP()}')
        with lock:
            results.append(RequestResult(resp, start_time, time.time()))
        
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
    The load balancer will reject requests when the number of simultaneous connections exceeds a certain threshold (5). 

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

def test_load_shed_exponential():
    """
    In this test, we simulate a scenario where the load balancer employs exponential load shedding to prevent server overload. 
    The load balancer will reject requests with increasing probability as the number of simultaneous connections exceeds a certain threshold (6). 

    We expect fewer timeouts and failed requests compared to the no load shedding scenario, as well as lower latencies.
    """

    topo = MultiClientMultiServer(num_clients=NUM_CLIENTS, num_servers=NUM_SERVERS, client_cpu=CLIENT_CPU, server_cpus=SERVER_CPUS, lb_json='test/setup/load_shed_test_exp_lb.json')
    topo.start_backend()
    topo.net.start()

    time.sleep(6) # wait for LB and servers to stabilize

    clients = topo.get_clients()
    
    # Shared results and counters
    lock = threading.Lock()
    results = []

    print("Starting exponential load shedding test")
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
    exp_shed_test_results = test_load_shed_exponential()

    print("\n--- No Load Shedding Test Results ---")
    results_summary(no_shed_test_results)

    print("\n--- Load Shedding Test Results ---")
    results_summary(shed_test_results)

    print("\n--- Exponential Load Shedding Test Results ---")
    results_summary(exp_shed_test_results)

    plot_latency_over_time('test/results/load_shedding_latency_over_time.png', ['No Shedding', 'Load Shedding (Hard)', 'Load Shedding (Exponential)'], no_shed_test_results, shed_test_results, exp_shed_test_results)
    plot_successful_requests_over_time('test/results/load_shedding_status_over_time.png', ['No Shedding', 'Load Shedding (Hard)', 'Load Shedding (Exponential)'], no_shed_test_results, shed_test_results, exp_shed_test_results)
    plot_errors_over_time('test/results/load_shedding_errors_over_time.png', ['No Shedding', 'Load Shedding (Hard)', 'Load Shedding (Exponential)'], no_shed_test_results, shed_test_results, exp_shed_test_results)