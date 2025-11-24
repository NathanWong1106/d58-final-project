import math
import random

K = 0.3 # heuristic constant for exponential shedding (allow for some load tolerance)

class LoadShedParams:
    def __init__(self, sim_conn_threshold=5, strategy="exponential"):
        self.sim_conn_threshold = sim_conn_threshold
        self.strategy = strategy
        
class LoadShedder:
    def __init__(self, opts:LoadShedParams=LoadShedParams()):
        self.opts = opts
        self.simultaneous_connections = 0

    def should_shed(self):
        if self.opts.strategy == "exponential": # Shedding probability increases exponentially with number of connections
            threshold = self.opts.sim_conn_threshold
            if self.simultaneous_connections < threshold:
                return False
            else:
                # Shedding probability increases exponentially with number of connections
                prob = 1 - math.exp(-K * (self.simultaneous_connections - threshold))
                return random.random() < prob

        else:
            return self.simultaneous_connections >= self.opts.sim_conn_threshold
    
    def increment_connections(self):
        self.simultaneous_connections += 1

    def decrement_connections(self):
        if self.simultaneous_connections > 0:
            self.simultaneous_connections -= 1
    