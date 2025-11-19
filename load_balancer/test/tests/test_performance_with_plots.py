import threading
import time
import statistics
import os
import matplotlib.pyplot as plt
from test.setup.topos import MultiClientMultiServer
from mininet.log import lg

def test_performance_with_plots(num_clients=5, num_servers=3, duration=30, output_dir='test/results'):
    os.makedirs(output_dir, exist_ok=True)
    
    topo = MultiClientMultiServer()
    topo.build(M=num_clients, N=num_servers)
    topo.start_backend()
    topo.net.start()

    clients = topo.get_clients()
    lb = topo.get_load_balancer()

    rtts = {client.name: [] for client in clients}
    timestamps = {client.name: [] for client in clients}
    all_rtts = []
    all_timestamps = []

    time.sleep(2)

    end_time = time.time() + duration
    send_threads = []

    for client in clients:
        def send_requests(c):
            while time.time() < end_time:
                start = time.time()
                try:
                    response = c.cmd(f'curl --max-time 5 -s http://{lb.IP()}')
                    rtt = time.time() - start
                    timestamp = time.time()
                    rtts[c.name].append(rtt)
                    timestamps[c.name].append(timestamp)
                    all_rtts.append(rtt)
                    all_timestamps.append(timestamp)
                except Exception as e:
                    print(f"Error from {c.name}: {e}")
        
        t = threading.Thread(target=send_requests, args=(client,))
        send_threads.append(t)
        t.start()

    for t in send_threads:
        t.join()

    topo.net.stop()

    total_requests = len(all_rtts)
    requests_per_second = total_requests / duration if duration > 0 else 0
    
    avg_rtt = statistics.mean(all_rtts) if all_rtts else 0
    median_rtt = statistics.median(all_rtts) if all_rtts else 0
    min_rtt = min(all_rtts) if all_rtts else 0
    max_rtt = max(all_rtts) if all_rtts else 0
    
    print("\n" + "="*60)
    print("PERFORMANCE TEST RESULTS")
    print("="*60)
    print(f"Test Duration: {duration} seconds")
    print(f"Number of Clients: {num_clients}")
    print(f"Number of Servers: {num_servers}")
    print(f"Total Requests: {total_requests}")
    print(f"Requests per Second: {requests_per_second:.2f}")
    print(f"\nRTT Statistics:")
    print(f"  Average RTT: {avg_rtt:.4f} seconds")
    print(f"  Median RTT: {median_rtt:.4f} seconds")
    print(f"  Min RTT: {min_rtt:.4f} seconds")
    print(f"  Max RTT: {max_rtt:.4f} seconds")
    if len(all_rtts) > 1:
        print(f"  Std Dev RTT: {statistics.stdev(all_rtts):.4f} seconds")
    print("="*60)

    create_performance_plots(
        all_rtts, all_timestamps, rtts, timestamps,
        num_clients, num_servers, duration, output_dir
    )

    return {
        'total_requests': total_requests,
        'requests_per_second': requests_per_second,
        'avg_rtt': avg_rtt,
        'median_rtt': median_rtt,
        'min_rtt': min_rtt,
        'max_rtt': max_rtt,
        'all_rtts': all_rtts,
        'all_timestamps': all_timestamps
    }

def create_performance_plots(all_rtts, all_timestamps, rtts_by_client, 
                            timestamps_by_client, num_clients, num_servers, 
                            duration, output_dir):
    start_time = min(all_timestamps) if all_timestamps else 0
    relative_times = [(t - start_time) for t in all_timestamps]
    
    plt.figure(figsize=(12, 6))
    plt.scatter(relative_times, all_rtts, alpha=0.5, s=10)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Response Time (seconds)')
    plt.title(f'Response Time Over Time (Clients: {num_clients}, Servers: {num_servers})')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/rtt_over_time.png', dpi=150)
    plt.close()
    
    plt.figure(figsize=(10, 6))
    plt.hist(all_rtts, bins=50, edgecolor='black', alpha=0.7)
    plt.xlabel('Response Time (seconds)')
    plt.ylabel('Frequency')
    plt.title(f'Response Time Distribution (Clients: {num_clients}, Servers: {num_servers})')
    plt.axvline(statistics.mean(all_rtts), color='r', linestyle='--', 
                label=f'Mean: {statistics.mean(all_rtts):.4f}s')
    plt.axvline(statistics.median(all_rtts), color='g', linestyle='--', 
                label=f'Median: {statistics.median(all_rtts):.4f}s')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/rtt_distribution.png', dpi=150)
    plt.close()
    
    if len(relative_times) > 10:
        window_size = max(5, len(relative_times) // 20)
        rps_times = []
        rps_values = []
        
        for i in range(0, len(relative_times), window_size):
            window_times = relative_times[i:i+window_size]
            if len(window_times) > 1:
                time_span = max(window_times) - min(window_times)
                if time_span > 0:
                    rps = len(window_times) / time_span
                    rps_times.append(statistics.mean(window_times))
                    rps_values.append(rps)
        
        plt.figure(figsize=(12, 6))
        plt.plot(rps_times, rps_values, marker='o', linestyle='-', linewidth=2)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Requests per Second')
        plt.title(f'Throughput Over Time (Clients: {num_clients}, Servers: {num_servers})')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/throughput_over_time.png', dpi=150)
        plt.close()
    
    if len(rtts_by_client) > 1:
        plt.figure(figsize=(12, 6))
        for client_name, client_rtts in rtts_by_client.items():
            if client_rtts:
                client_relative_times = [
                    (t - start_time) for t in timestamps_by_client[client_name]
                ]
                plt.scatter(client_relative_times, client_rtts, 
                           alpha=0.5, s=10, label=client_name)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Response Time (seconds)')
        plt.title(f'Response Time by Client (Clients: {num_clients}, Servers: {num_servers})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/rtt_by_client.png', dpi=150)
        plt.close()
    
    print(f"\nPlots saved to {output_dir}/")
    print("  - rtt_over_time.png")
    print("  - rtt_distribution.png")
    print("  - throughput_over_time.png")
    if len(rtts_by_client) > 1:
        print("  - rtt_by_client.png")

if __name__ == "__main__":
    lg.setLogLevel('info')
    test_performance_with_plots(num_clients=5, num_servers=3, duration=30)
