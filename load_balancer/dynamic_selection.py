import threading


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

    def select_server(self):
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
            print(f'[LB] Current candidates: {self.candidates}')
            if not self.candidates:
                return None
            server = self.candidates[self.index]
            self.index = (self.index + 1) % len(self.candidates)
            return server