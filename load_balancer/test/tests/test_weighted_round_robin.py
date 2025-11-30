from test.setup.topos import MultiClientMultiServer
import time
import threading
from test.tests.test_baseline import test_baseline
from test.tests.req_result_obj import results_summary, plot_latency_over_time, plot_successful_requests_over_time, plot_errors_over_time
from test.tests.send_request_helper import send_requests
from test.setup.topos import SERVER_SINGLE_CPU, CLIENT_CPU_TOT

# Sample test output:
# --- Baseline Test Results ---
# Total requests sent: 298
# Total successful responses (200): 168
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 0
# Total server errors (502/500): 130
# Average latency of successful requests: 1.026 seconds

# --- Unweighted Round Robin Test Results ---
# Total requests sent: 217
# Total successful responses (200): 217
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 0
# Total server errors (502/500): 0
# Average latency of successful requests: 0.934 seconds

# --- Weighted Round Robin Test Results ---
# Total requests sent: 265
# Total successful responses (200): 264
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 0
# Total server errors (502/500): 1
# Average latency of successful requests: 0.729 seconds

SERVER_CPUS = [SERVER_SINGLE_CPU, SERVER_SINGLE_CPU / 2, SERVER_SINGLE_CPU / 3]

def test_unweighted_round_robin():
    """
    In this unweighted round robin test, we set up multiple servers (with different CPU capacities) behind the load balancer and have multiple clients send requests.
    We expect the load balancer to distribute requests evenly across all servers.
    """
    topo = MultiClientMultiServer(
        num_clients=10, 
        num_servers=3, 
        client_cpu=CLIENT_CPU_TOT, 
        server_cpus=SERVER_CPUS,
        lb_json='test/setup/default_test_lb.json'
    )
    topo.start_backend()
    topo.net.start()

    time.sleep(6)  # wait for LB and servers to stabilize

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    results = []
    lock = threading.Lock()

    print("Starting unweighted round robin test")
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

def test_weighted_round_robin():
    """
    In this weighted round robin test, we set up multiple servers behind the load balancer and have multiple clients send requests.
    We expect the load balancer to distribute requests according to server weights, resulting in improved performance.
    """
    topo = MultiClientMultiServer(
        num_clients=10, 
        num_servers=3, 
        client_cpu=CLIENT_CPU_TOT, 
        server_cpus=SERVER_CPUS,
        lb_json='test/setup/weighted_round_robin_lb.json'
    )
    topo.start_backend()
    topo.net.start()

    time.sleep(6)  # wait for LB and servers to stabilize

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    results = []
    lock = threading.Lock()

    print("Starting weighted round robin test")
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

if __name__ == "__main__":
    baseline_results = test_baseline()
    unweighted_round_robin_results = test_unweighted_round_robin()
    weighted_round_robin_results = test_weighted_round_robin()

    print("\n--- Baseline Test Results ---")
    results_summary(baseline_results)

    print("\n--- Unweighted Round Robin Test Results ---")
    results_summary(unweighted_round_robin_results)

    print("\n--- Weighted Round Robin Test Results ---")
    results_summary(weighted_round_robin_results)

    plot_latency_over_time('test/results/weighted_round_robin_latency_over_time.png', ['Baseline', 'Unweighted Round Robin', 'Weighted Round Robin'], baseline_results, unweighted_round_robin_results, weighted_round_robin_results)
    plot_errors_over_time('test/results/weighted_round_robin_errors_over_time.png', ['Baseline', 'Unweighted Round Robin', 'Weighted Round Robin'], baseline_results, unweighted_round_robin_results, weighted_round_robin_results)
    plot_successful_requests_over_time('test/results/weighted_round_robin_throughput.png', ['Baseline', 'Unweighted Round Robin', 'Weighted Round Robin'], baseline_results, unweighted_round_robin_results, weighted_round_robin_results)
