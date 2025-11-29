import sys
from strategies.lb_strategy import LBStrategy
from strategies.round_robin_strategy import RoundRobinStrategy
from strategies.consistent_hash_strategy import ConsistentHashing
from strategies.weighted_round_robin_strategy import WeightedRoundRobinStrategy
from strategies.least_connections_strategy import LeastConnectionsStrategy
from strategies.least_response_time_strategy import LeastResponseTimeStrategy
from load_balancer import LoadBalancer, LBOpts
from load_shedder import LoadShedParams
from serv_obj import Server
import json
import typing


def get_strategy(strategy_name: str, servers: typing.List[Server], *, replica_count=10) -> LBStrategy:
    if strategy_name == "round_robin":
        return RoundRobinStrategy(servers)
    elif strategy_name == "hash":
        return ConsistentHashing(servers, replica_count)
    elif strategy_name == "weighted_round_robin":
        return WeightedRoundRobinStrategy(servers)
    elif strategy_name == "least_connections":
        return LeastConnectionsStrategy(servers)
    elif strategy_name == "least_response_time":
        return LeastResponseTimeStrategy(servers)
    else:
        return None


if __name__ == "__main__":

    print("Starting Load Balancer...")

    # Example servers
    if len(sys.argv) < 1:
        print("Usage: python run_load_balancer.py <path_to_config>.json")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        config = json.load(f)

        servers = []
        for serv in config["servers"]:
            server = Server(serv["name"], serv["ip"], serv["port"])
            # Set weight if specified in config
            if "weight" in serv:
                server.set_additional_info("weight", serv["weight"])
            servers.append(server)

        lb_strategy = get_strategy(config.get("strategy", "round_robin"), servers)
        if lb_strategy is None:
            print(f"Unknown strategy: {config.get('strategy')}")
            sys.exit(1)
        
        lb_opts = LBOpts(
            sticky_sessions=config.get("sticky_sessions", False),
            debug_mode=config.get("debug_mode", False),
            health_check_interval=config.get("health_check_interval", 3),
            health_check_path=config.get("health_check_path", "/health"),
            health_check_timeout=config.get("health_check_timeout", 2),
            load_shedding_enabled=config.get("load_shedding_enabled", False),
            load_shed_params=LoadShedParams(
                sim_conn_threshold=config.get("load_shed_params", {}).get("sim_conn_threshold", 5),
                strategy=config.get("load_shed_params", {}).get("strategy", "exponential")
            )
        )

        lb = LoadBalancer(config["load_balancer_ip"], config["load_balancer_port"], servers, lb_strategy, lb_opts)
        lb.start_lb()


    