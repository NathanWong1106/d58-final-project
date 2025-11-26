from strategies.lb_strategy import LBStrategy
from serv_obj import Server
import typing


class WeightedRoundRobinStrategy(LBStrategy):
    """
    Round robin algorithm that gives more turns to servers with higher weight.
    Use weight from additional_info if available(default to 1 otherwise).
    """

    def __init__(self, servers: typing.List[Server]):
        super().__init__(servers)
        self.current_index = 0
        self.weighted_list = []

        for s in servers:
            weight = s.additional_info.get('weight', 1)
            self.weighted_list.extend([s] * weight)

    def get_server(self, **kwargs):
        if not self.weighted_list:
            return None

        for _ in range(len(self.weighted_list)):
            server = self.weighted_list[self.current_index % len(self.weighted_list)]
            self.current_index = (self.current_index + 1) % len(self.weighted_list)

            if server.healthy:
                return server

        return None
