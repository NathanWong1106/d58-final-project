import threading
import typing
import time
import socket
from serv_obj import Server

HTTP_PORT = 80

class HealthCheckInfo:
    WEIGHT = 0.8  # weight for moving average

    def __init__ (self):
        self.avg_rtt = 0.0
        

    def add_rtt(self, rtt: float):
        self.avg_rtt = (self.WEIGHT * self.avg_rtt) + ((1 - self.WEIGHT) * rtt)

    def get_average_rtt(self) -> float:
        return self.avg_rtt
        

class HealthCheckService:
    """ Service that periodically performs health checks on a list of servers. """

    def __init__(self, servers: typing.List[Server], server_lock: threading.Lock, interval=3, health_check_path="/health", timeout=1):
        self.servers = servers
        self.server_lock = server_lock
        self.interval = interval
        self.health_check_path = health_check_path
        self.timeout = timeout

    def start(self):
        def run():
            while True:
                self.check_health()
                time.sleep(self.interval)

        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()

    def GET_request_string(self, path: str, host_ip: str) -> str:
        return f"GET {path} HTTP/1.1\r\nHost: {host_ip}\r\nConnection: close\r\n\r\n"

    def check_health(self):
        """ Perform health checks on all servers by sending GET requests to the configured health check path. Updates each server's health status based on the response (or lack thereof). """

        for server in self.servers:
            try:
                start = time.time()

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                request = self.GET_request_string(self.health_check_path, server.ip)
                sock.settimeout(self.timeout)
                sock.connect((server.ip, HTTP_PORT))
                sock.sendall(request.encode())
                response = sock.recv(1024).decode()
                sock.close()

                end = time.time()

                # Get RTT
                rtt = end - start

                # Update server health status
                # We need to obtain the lock before modifying shared server state
                with self.server_lock:
                    if not server.get_additional_info("health_check_info"):
                        server.set_additional_info("health_check_info", HealthCheckInfo())
                    
                    health_info:HealthCheckInfo = server.get_additional_info("health_check_info")
                    health_info.add_rtt(rtt)
                    
                    if "200 OK" in response:
                        server.set_healthy(True)
                    else:
                        server.set_healthy(False)

            except Exception as e:
                with self.server_lock:
                    server.set_healthy(False)