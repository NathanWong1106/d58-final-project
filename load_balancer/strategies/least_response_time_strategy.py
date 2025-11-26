from strategies.lb_strategy import LBStrategy
from serv_obj import Server
import typing

class LeastResponseTimeStrategy(LBStrategy):
    """
    Select a healthy server with the lowest average response time.
    Use weight from additional_info if available (default to 1 otherwise).
    """

    def __init__(self, servers: typing.List[Server]):
        super().__init__(servers)

    def get_server(self, **kwargs):
        return min(
            [s for s in self.servers if s.healthy],
            key=lambda s: (
                s.get_additional_info('health_check_info').get_average_rtt() 
                if s.get_additional_info('health_check_info') else float('inf')
            ) / s.additional_info.get('weight', 1),
            default=None
        )
