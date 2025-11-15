class LBStrategy:
    def __init__(self, servers):
        self.servers = servers

    def get_server(self):
        raise NotImplementedError("This method should be overridden by subclasses")