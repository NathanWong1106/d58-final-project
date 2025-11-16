import threading
import time
from test.setup.topos import MultiClientMultiServer
from mininet.log import lg

def test_basic_multiclient():
    topo = MultiClientMultiServer()
    topo.start_backend()
    topo.net.start()

    time.sleep(5)  # Wait for health checks to stabilize

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    results = {client.name: [] for client in clients}
    # Send requests for 20 seconds simultaneously from all clients
    end_time = time.time() + 20

    send_threads = []

    for client in clients:
        def send_requests(c):
            while time.time() < end_time:
                response = c.cmd(f'curl http://{lb.IP()}')
                results[c.name].append(response.strip())
        
        t = threading.Thread(target=send_requests, args=(client,))
        send_threads.append(t)
        t.start()

    time.sleep(25)  # Ensure all threads complete
    for t in send_threads:
        t.join()

    topo.net.stop()
    print(results)

if __name__ == "__main__":
    lg.setLogLevel('info')
    test_basic_multiclient()