from strategies.lb_strategy import LBStrategy
from serv_obj import Server
import typing
import hashlib
import bisect


class ConsistentHashing(LBStrategy):
    """
    Source IP hashing using hash ring to prevent remapping when servers change
    """

    def __init__(self, servers: typing.List[Server], replica_count=10):
        super().__init__(servers)
        self.hash_ring = dict()
        self.sorted_hash = []
        self.replica_count = replica_count
        for server in servers:
            self._hash_server(server)

    def _hash_server(self, server: Server):
        for i in range(self.replica_count):
            replica_hash = self._hash(f"{server.ip}replica{i}")
            self.hash_ring[replica_hash] = server
            bisect.insort(self.sorted_hash, replica_hash)

    def get_server(self, **kwargs):
        if (not self.sorted_hash or "source_ip" not in kwargs or not
                kwargs.get("source_ip")):
            return None

        source_ip = kwargs.get("source_ip")
        source_hash = self._hash(source_ip)
        closest_server = bisect.bisect_left(self.sorted_hash, source_hash)

        if closest_server == len(self.sorted_hash):
            closest_server = 0

        for i in range(len(self.sorted_hash)):
            server_hash = self.sorted_hash[(
                closest_server + i) % len(self.sorted_hash)]
            server = self.hash_ring[server_hash]

            if server.healthy:
                print("forwarded ", source_ip, "to ", server.ip)
                return server

        print("returned none")
        return None

    def _hash(self, key):
        if key is None:
            return None
        return abs(int(hashlib.md5(bytes(key, "UTF-8")).hexdigest(), 16))
