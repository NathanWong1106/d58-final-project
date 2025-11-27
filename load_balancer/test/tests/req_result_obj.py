import typing
import matplotlib.pyplot as plt

class RequestResult:
    def __init__(self, response: str, start: float, end: float):
        self.response = response
        self.start = start
        self.end = end
        self.latency = end - start

    def is_successful(self):
        return "200" in self.response

    def is_timeout(self):
        return "504" in self.response or "timed out" in self.response.lower()

    def was_shed(self):
        return "503" in self.response and "high load" in self.response

    def was_server_error(self):
        return "502" in self.response or "500" in self.response or ("503" in self.response and "No healthy servers" in self.response)


def results_summary(results: typing.List[RequestResult]):
    total_requests = len(results)
    total_successful_requests = sum(1 for r in results if r.is_successful())
    total_timeouts = sum(1 for r in results if r.is_timeout())
    total_shed = sum(1 for r in results if r.was_shed())
    total_server_errors = sum(1 for r in results if r.was_server_error())
    avg_successful_latency = sum(r.latency for r in results if r.is_successful(
    )) / total_successful_requests if total_successful_requests > 0 else 0.0

    print(f"Total requests sent: {total_requests}"
          f"\nTotal successful responses (200): {total_successful_requests}"
          f"\nTotal timeouts (504 or curl timeout): {total_timeouts}"
          f"\nTotal shed responses (503): {total_shed}"
          f"\nTotal server errors (502/500): {total_server_errors}"
          f"\nAverage latency of successful requests: {avg_successful_latency:.3f} seconds")
    
def plot_latency_over_time(filename: str, test_names: typing.List[str], *results: typing.List[RequestResult]):
    """ For each result list, overlay the latency over time plot. """

    plt.figure()
    for i, res in enumerate(results):
        start_time = min(r.start for r in res)
        times = [r.start - start_time for r in res if r.is_successful()]
        latencies = [r.latency for r in res if r.is_successful()]
        plt.scatter(times, latencies, s=1, label=f'Test {test_names[i]}')
        
    plt.xlabel('Time (s)')
    plt.ylabel('Latency (s)')
    plt.title('Latency Over Time')
    plt.legend()
    plt.savefig(filename)
    plt.close()

def plot_successful_requests_over_time(filename: str, test_names: typing.List[str], *results: typing.List[RequestResult]):
    """ For each result list, overlay the successful requests over time plot. """

    plt.figure()
    for i, res in enumerate(results):
        start_time = min(r.start for r in res)
        times = [r.start - start_time for r in res if r.is_successful()]
        plt.hist(times, bins=50, alpha=0.5, label=f'Test {test_names[i]}', histtype='step')
        
    plt.xlabel('Time (s)')
    plt.ylabel('Number of Successful Requests')
    plt.title('Successful Requests Over Time')
    plt.legend()
    plt.savefig(filename)
    plt.close()

def plot_errors_over_time(filename: str, test_names: typing.List[str], *results: typing.List[RequestResult]):
    """ For each result list, overlay the error requests over time plot. """

    plt.figure()
    for i, res in enumerate(results):
        start_time = min(r.start for r in res)
        times = [r.start - start_time for r in res if r.was_server_error() or r.is_timeout()]
        plt.hist(times, bins=50, alpha=0.5, label=f'Test {test_names[i]}', histtype='step')
        
    plt.xlabel('Time (s)')
    plt.ylabel('Number of Error Requests')
    plt.title('Error Requests Over Time')
    plt.legend()
    plt.savefig(filename)
    plt.close()