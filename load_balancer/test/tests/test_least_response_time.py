from test.setup.topos import MultiClientMultiServer
import time
import threading
from test.tests.test_baseline import test_baseline
from test.tests.req_result_obj import results_summary, plot_latency_over_time, plot_successful_requests_over_time
from test.tests.send_request_helper import send_requests
from test.setup.topos import SERVER_SINGLE_CPU, CLIENT_CPU_TOT

# Sample test output:
# --- Baseline Test Results ---
# Total requests sent: 192
# Total successful responses (200): 188
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 0
# Total server errors (502/500): 4
# Average latency of successful requests: 0.964 seconds

# --- Least Response Time Test Results ---
# Total requests sent: 471
# Total successful responses (200): 471
# Total timeouts (504 or curl timeout): 0
# Total shed responses (503): 0
# Total server errors (502/500): 0
# Average latency of successful requests: 0.404 seconds

def test_least_response_time():
    """
    In this least response time test, we set up multiple servers behind the load balancer and have multiple clients send requests.
    We expect the load balancer to distribute requests to servers with the lowest average response time, resulting in improved performance.
    """
    topo = MultiClientMultiServer(
        num_clients=10, 
        num_servers=3, 
        client_cpu=CLIENT_CPU_TOT, 
        server_cpus=[SERVER_SINGLE_CPU]*3,
        lb_json='test/setup/least_response_time_lb.json'
    )
    topo.start_backend()
    topo.net.start()

    time.sleep(6)  # wait for LB and servers to stabilize

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    results = []
    lock = threading.Lock()

    print("Starting least response time test")
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
    least_response_time_results = test_least_response_time()

    print("\n--- Baseline Test Results ---")
    results_summary(baseline_results)

    print("\n--- Least Response Time Test Results ---")
    results_summary(least_response_time_results)

    plot_latency_over_time('test/results/least_response_time_latency_over_time.png', ['Baseline', 'Least Response Time'], baseline_results, least_response_time_results)
    plot_successful_requests_over_time('test/results/least_response_time_throughput.png', ['Baseline', 'Least Response Time'], baseline_results, least_response_time_results)

