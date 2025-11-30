from test.setup.topos import MultiClientMultiServer
import time
import threading
from test.tests.req_result_obj import RequestResult, results_summary, plot_latency_over_time, plot_successful_requests_over_time, plot_errors_over_time
from load_balancer import STICKY_TIMEOUT
from mininet.log import lg
from mininet.cli import CLI

DURATION = 20


def send_requests(c, lock, results, lb, sid):
    end_time = time.time() + DURATION
    while time.time() < end_time:
        start_time = time.time()

        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(
            f'curl --max-time 5 -i -H \'SID: {sid}\' http://{lb.IP()}')
        with lock:
            results.append(RequestResult(resp, start_time, time.time()))

        # tiny pause to create a stream of requests
        time.sleep(0.2)

# used for sticky session expiry, sends for n seconds, sleeps until sticky session expires, then sends again if there is enough time


def send_reconnect(c, lock, results, lb, sid):
    init_time = time.time()
    end_time = init_time + DURATION
    n = 7
    test_sticky = True
    while time.time() < end_time:
        start_time = time.time()

        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(
            f'curl --max-time 5 -i -H \'SID: {sid}\' http://{lb.IP()}')
        with lock:
            results.append(RequestResult(resp, start_time, time.time()))

        # tiny pause to create a stream of requests
        if (test_sticky and time.time() > init_time + n):
            test_sticky = False
            time.sleep(STICKY_TIMEOUT+1)
        else:
            time.sleep(0.2)

# Change value of "sticky_sessions" in setup file to view difference
def test_sticky():
    topo = MultiClientMultiServer(
        num_clients=5, num_servers=5, lb_json='test/setup/sticky_session_lb.json')
    topo.start_backend()
    topo.net.start()

    time.sleep(10)

    clients = topo.get_clients()
    lb = topo.get_load_balancer()
    servers = topo.get_servers()
    sids = topo.get_sids()

    time.sleep(2)  # Wait for setup

    # Shared results and counters
    lock = threading.Lock()
    results = []

    print("Starting sticky test")
    threads = []
    for client in clients[:3]:
        t = threading.Thread(target=send_requests, args=(
            client, lock, results, topo.get_load_balancer(), sids[str(client)]))
        t.start()
        threads.append(t)

    for client in clients[3:]:
        t = threading.Thread(target=send_reconnect, args=(
            client, lock, results, topo.get_load_balancer(), sids[str(client)]))
        t.start()
        threads.append(t)

    time.sleep(5)  # Let some requests go through

    # check that sticky does not stick to unhealthy servers
    topo.net.get('s1').cmd('ifconfig s1-eth0 down')
    topo.net.get('s2').cmd('ifconfig s2-eth0 down')
    print("Stopped server 1 & 2")

    time.sleep(6)

    topo.net.get('s1').cmd('ifconfig s1-eth0 up')
    topo.net.get('s2').cmd('ifconfig s2-eth0 up')
    print("Started server 1 & 2")

    time.sleep(15)

    for t in threads:
        t.join()

    topo.net.stop()
    print("Test completed.")

    return results


if __name__ == "__main__":
    lg.setLogLevel('info')
    results = test_sticky()
    results_summary(results)

    plot_latency_over_time('test/results/sticky_latency_over_time.png', [
                           'Sticky Session'], results)
    plot_successful_requests_over_time('test/results/sticky_status_over_time.png', [
        'Sticky Session'], results)
    plot_errors_over_time('test/results/sticky_errors_over_time.png', [
        'Sticky Session'], results)
