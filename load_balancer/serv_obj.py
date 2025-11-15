class Server:
    def __init__(self, name, ip, port, healthy=True):
        self.name = name
        self.ip = ip
        self.port = port
        self.healthy = healthy
        self.additional_info = {}

    def set_additional_info(self, info):
        self.additional_info = info