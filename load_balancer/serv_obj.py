class Server:
    def __init__(self, name, ip, port, healthy=True):
        self.name = name
        self.ip = ip
        self.port = port
        self.healthy = healthy
        self.additional_info = {}

    def set_additional_info(self, key, info):
        self.additional_info[key] = info

    def get_additional_info(self, key):
        return self.additional_info.get(key, None)

    def set_healthy(self, status: bool):
        self.healthy = status

    def is_healthy(self) -> bool:
        return self.healthy