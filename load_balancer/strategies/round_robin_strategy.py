from strategies.lb_strategy import LBStrategy
from serv_obj import Server
import typing

class RoundRobinStrategy(LBStrategy):
    def __init__(self, servers: typing.List[Server]):
        self.servers = servers
        self.current_index = 0

    def get_server(self):
        if not self.servers:
            return None
        
        starting_index = self.current_index
        while self.servers[self.current_index].healthy is False:
            self.current_index = (self.current_index + 1) % len(self.servers)
            if self.current_index == starting_index:
                return None  # All servers are unhealthy
        
        selected_server = self.servers[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.servers)
        return selected_server