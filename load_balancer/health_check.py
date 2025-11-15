import threading
import typing
import time
import socket
from serv_obj import Server

HEALTH_CHECK_PATH = "/health"
HEALTH_CHECK_PORT = 8001

class HealthCheckInfo:
    WINDOW_SIZE = 10

    def __init__ (self):
        self.rtts = []
        self.sum_rtt = 0.0
        self.count = 0

    def add_rtt(self, rtt: float):
        if self.count < self.WINDOW_SIZE:
            self.rtts.append(rtt)
            self.sum_rtt += rtt
            self.count += 1
        else:
            oldest_rtt = self.rtts.pop(0)
            self.sum_rtt -= oldest_rtt
            self.rtts.append(rtt)
            self.sum_rtt += rtt

    def get_average_rtt(self) -> float:
        if self.count == 0:
            return float('inf')
        return self.sum_rtt / self.count

class HealthCheckService:
    def __init__(self, servers: typing.List[Server], server_lock: threading.Lock, interval=5):
        self.servers = servers
        self.server_lock = server_lock
        self.interval = interval

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
        for server in self.servers:
            try:
                start = time.time()

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                request = self.GET_request_string(HEALTH_CHECK_PATH, server.ip)
                sock.settimeout(2)
                sock.connect((server.ip, HEALTH_CHECK_PORT))
                sock.sendall(request.encode())
                response = sock.recv(1024).decode()
                sock.close()

                end = time.time()

                # Get RTT
                rtt = end - start

                # Update server health status
                # We need to obtain the lock before modifying shared server state
                with self.server_lock:
                    if "200 OK" in response:
                        server.set_healthy(True)

                        if not server.get_additional_info("health_check_info"):
                            server.set_additional_info("health_check_info", HealthCheckInfo())

                        health_info = server.get_additional_info("health_check_info")
                        health_info.add_rtt(rtt)
                        server.set_additional_info("health_check_info", health_info)
                    else:
                        server.set_healthy(False)

            except Exception as e:
                with self.server_lock:
                    server.set_healthy(False)