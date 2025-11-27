import typing


class RequestResult:
    def __init__(self, response: str, latency: float):
        self.response = response
        self.latency = latency

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
