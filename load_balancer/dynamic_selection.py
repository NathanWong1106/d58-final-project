import threading
import hashlib
import bisect

class DynamicSelectionAlgo:
    """
    Base class for dynamic selection algorithms. 
    """
    def __init__(self):
        self.candidates_lock = threading.Lock()

    def add_server(self, server):
        pass

    def remove_server(self, server):
        pass

    def select_server(self, **kwargs):
        raise NotImplementedError

class PreFilter:
    """
    Base class for filters that dynamically add and remove candidate servers.
    """

    def __init__(self, servers, selectionAlgo: DynamicSelectionAlgo):
        self.servers = servers
        self.selectionAlgo = selectionAlgo
        self.prev_candidates = set()
        self.candidates = set()

    def update_candidates(self, new_candidates):
        for server in new_candidates - self.prev_candidates:
            self.selectionAlgo.add_server(server)
        for server in self.prev_candidates - new_candidates:
            self.selectionAlgo.remove_server(server)
        self.prev_candidates = new_candidates

class DynamicRoundRobin(DynamicSelectionAlgo):
    """
    Round robin dynamic selection algorithm.
    """

    def __init__(self):
        super().__init__()
        self.index = 0
        self.candidates = []

    def add_server(self, server):
        if server not in self.candidates:
            with self.candidates_lock:
                self.candidates.append(server)
    
    def remove_server(self, server):
        if server in self.candidates:
            with self.candidates_lock:
                self.candidates.remove(server)
                
                if self.index >= len(self.candidates):
                    self.index = 0

    def select_server(self):
        with self.candidates_lock:
            # print(f'[LB] Current candidates: {self.candidates}')
            if not self.candidates:
                return None
            server = self.candidates[self.index]
            self.index = (self.index + 1) % len(self.candidates)
            return server
        
class ConsistentHashing(DynamicSelectionAlgo):
    """
    Source IP hashing using hash ring to prevent remapping when servers change
    """
    def __init__(self, servers, replica_count=10):
        super().__init__()
        self.hash_ring = dict()
        self.sorted_hash = []
        self.replica_count = replica_count
        for server in servers:
            self.add_server(server)
    
    def add_server(self, server):
        print("added server: ", server)
        with self.candidates_lock:
            for i in range(self.replica_count):
                replica_hash = self._hash(f"{server.ip}replica{i}")
                self.hash_ring[replica_hash] = server
                bisect.insort(self.sorted_hash, replica_hash)

    def remove_server(self, server):
        print("removed server: ", server)
        with self.candidates_lock:
            for i in range(self.replica_count):
                replica_hash = self._hash(f"{server.ip}replica{i}")
                self.hash_ring.pop(replica_hash)
                self.sorted_hash.remove(replica_hash)

    def select_server(self, **kwargs):
        with self.candidates_lock:
            if (not self.sorted_hash or "source_ip" not in kwargs or not kwargs["source_ip"]):
                return None
            
            source_hash = self._hash(kwargs.get("source_ip"))
            closest_server = bisect.bisect_left(self.sorted_hash, source_hash)
            
            if closest_server == len(self.sorted_hash):
                closest_server = 0
            
            server_hash = self.sorted_hash[closest_server]
            server = self.hash_ring[server_hash]
            return server
    
    def _hash(self, key):
        return abs(int(hashlib.md5(bytes(key, "UTF-8")).hexdigest(), 16))