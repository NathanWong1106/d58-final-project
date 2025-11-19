import threading
import time
from test.setup.topos import MultiClientSingleServer
from mininet.log import lg

def test_baseline():
    topo = MultiClientSingleServer()
    topo.start_backend()
    topo.net.start()

    clients = topo.get_clients()
    lb = topo.get_load_balancer()
    results = {client.name: [] for client in clients}
    rtts = {client.name: [] for client in clients}

    # Send requests for 20 seconds simultaneously from all clients
    end_time = time.time() + 20
    send_threads = []
    for client in clients:
        def send_requests(c):
            while time.time() < end_time:
                start = time.time()
                response = c.cmd(f'curl --max-time 5 http://{lb.IP()}')
                rtt = time.time() - start
                rtts[c.name].append(rtt)
                results[c.name].append(response.strip())
        
        t = threading.Thread(target=send_requests, args=(client,))
        send_threads.append(t)
        t.start()

    time.sleep(21)  # Ensure all threads complete
    for t in send_threads:
        t.join()

    topo.net.stop()

    for client_name in results:
        print(f"{client_name} sent {len(results[client_name])} requests with average RTT {sum(rtts[client_name])/len(rtts[client_name]):.4f} seconds")

if __name__ == "__main__":
    lg.setLogLevel('info')
    test_baseline()

