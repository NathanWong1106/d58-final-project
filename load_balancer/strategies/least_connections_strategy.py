from strategies.lb_strategy import LBStrategy
from serv_obj import Server
import typing

class LeastConnectionsStrategy(LBStrategy):
    """
    Select a healthy server with the fewest active connections.
    Use weight from additional_info if available (default to 1 otherwise).
    """

    def __init__(self, servers: typing.List[Server]):
        super().__init__(servers)

    def get_server(self, **kwargs):
        return min(
            [s for s in self.servers if s.healthy],
            key=lambda s: s.additional_info.get('active_connections', 0) / s.additional_info.get('weight', 1),
            default=None
        )
