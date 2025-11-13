from dynamic_selection import PreFilter, DynamicSelectionAlgo
import requests
import threading
import time

class ResourceBased(PreFilter):

    def __init__(self, servers, selectionAlgo:DynamicSelectionAlgo, endpoint='/health', poll_interval=5, health_port=8001, staleness=30, timeout=2.0, weights={'cpu': 1, 'memory': 0.2}):
        super().__init__(servers, selectionAlgo)

        self.endpoint = endpoint
        self.poll_interval = poll_interval
        self.health_port = health_port
        self.staleness = staleness
        self.timeout = timeout
        self.weights = weights

        # Initialize a dictionary to store the latest resource usage data for each server
        self.resource_data = {}

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while True:
            for server in self.servers:
                self._poll_server(server)
                self.update_candidates(self.get_new_candidates())
            time.sleep(self.poll_interval)

    def _get_health_url(self, server):
        return f"http://{server}:{self.health_port}{self.endpoint}"
    
    def _compute_score(self, cpu, mem):
        return self.weights['cpu'] * cpu + self.weights['memory'] * mem
    
    def _poll_server(self, server):
        now = time.time()

        try:
            r = requests.get(self._get_health_url(server), timeout=self.timeout)
            data = r.json() if r.text else {}

            cpu = float(data.get('cpu_usage', 0))
            mem = float(data.get('memory_usage', 0))
            
            if r.status_code == 200:
                score = self._compute_score(cpu, mem)

                # Process the response to update resource data
                self.resource_data[server] = {
                    'score': score,
                    'healthy': True if score < 90 else False,
                    'last_update': now
                }

                print(f'[LB] Polled {server}: CPU={cpu}%, MEM={mem}%, SCORE={score}, HEALTHY={self.resource_data[server]["healthy"]}')
            else:
                self.resource_data[server] = { 'healthy': False, 'last_update': now }

        except Exception as e:
            self.resource_data[server] = { 'healthy': False, 'last_update': now }
        

    def get_new_candidates(self):
        now = time.time()
        candidates = set()

        for server in self.servers:
            rd = self.resource_data.get(server, None)

            if rd and rd['healthy'] and (now - rd['last_update'] <= self.staleness):
                candidates.add(server)
            else:
                continue
        
        return candidates