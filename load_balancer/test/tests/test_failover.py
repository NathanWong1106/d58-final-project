from test.setup.topos import SingleClientMultiServer
import time
import threading
from test.tests.req_result_obj import results_summary, plot_successful_requests_over_time, plot_errors_over_time
from test.tests.send_request_helper import send_requests

def test_failover():
    """ Test that requests are failovered when a server goes down for round-robin LB strategy. We expect some requests to fail when one server is down until the health check marks it unhealthy. """

    topo = SingleClientMultiServer()
    topo.start_backend()
    topo.net.start()

    client = topo.get_client()
    lb = topo.get_load_balancer()

    time.sleep(2)  # Wait for setup
    
    print("Starting failover test")
    start_time = time.time()
    end_time = start_time + 20  # Run the test for 20 seconds
    results = []

    lock = threading.Lock()
    thread = threading.Thread(target=send_requests, args=(client, lock, results, lb, end_time))
    thread.start()

    time.sleep(5)  # Let some requests go through

    # Now stop one server to test failover
    topo.net.get('s1').cmd('ifconfig s1-eth0 down')
    print("Stopped server 1 to test failover")

    thread.join()  # Wait for the request-sending thread to finish

    topo.net.stop()
    return results


if __name__ == "__main__":
    results = test_failover()
    results_summary(results)

    plot_successful_requests_over_time("test/results/failover_successful_requests.png", ["Failover"], results)
    plot_errors_over_time("test/results/failover_errors.png", ["Failover"], results)