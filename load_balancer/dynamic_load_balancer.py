import http.server, socketserver, threading, requests, random, socket
import time
import hashlib
from enum import Enum

from dynamic_selection import DynamicRoundRobin, ConsistentHashing
from resource_based_selection import ResourceBased

servers = []
downed_servers = []
algo = None

class Status(Enum):
    UP = 1
    DOWN = 0
    UNKNOWN = -1

class Server():
    def __init__(self, ip, port = 8080):
        self.ip = ip
        self.port = port
        self.status = Status.UNKNOWN
    
    def __str__(self):
        return f"Server: {self.ip}:{self.port}, status={self.status}"
        
    def __hash__(self):
        return abs(int(hashlib.md5(bytes(self.ip + ":" + self.port, "UTF-8")).hexdigest(), 16))

    def __eq__(self, value):
        return isinstance(value, Server) and self.ip == value.ip and self.port == value.port

def init_servers():
    ips = ["10.0.1.1", "10.0.1.2", "10.0.1.3"]
    for ip in ips:
        servers.append(Server(ip=ip))
    for s in servers:
        check_server_status(s)

#TODO: consider using ping? closer to course material
def check_server_status(s):
    try:
        r = requests.get(f"http://{s.ip}:{s.port}", timeout=2.5)
        if (r.status_code == 200):
            s.status = Status.UP
        else:
            s.status = Status.DOWN
    except requests.exceptions.RequestException:
        s.status = Status.DOWN

# TODO: maybe check server status periodically instead of when req comes
# TODO: offload status check to another thread
# TODO: maybe not repeated remove server from ring, could just be busy instead of down
class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        while True:
            for s in downed_servers[:]:
                check_server_status(s)
                if s.status == Status.UP:
                    print("added server back")
                    algo.add_server(s)
                    downed_servers.remove(s)
            
            server = algo.select_server(source_ip=self.client_address[0])
            if server is None:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'Service Unavailable')
                return
            check_server_status(server)
            if (server.status == Status.UP):
                break
            algo.remove_server(server)
            downed_servers.append(server)

        try:
            print(f"LB forward to server {server.ip}:{server.port}")
            r = requests.get(f"http://{server.ip}:{server.port}{self.path}", timeout=2.5)
        except requests.exceptions.RequestException as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b'Bad Gateway')
            print(f'Error forwarding to {server}: {e}')
            return
        
        self.send_response(r.status_code)
        for k, v in r.headers.items():
            if k.lower() not in ["content-encoding", "transfer-encoding"]:
                self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(r.content)
        except BrokenPipeError:
            print("client closed before response finished")

PORT = 80
init_servers()

# Choose selection algorithm
algo = ConsistentHashing(servers)

# Choose dynamic filter
# ResourceBased(servers=servers, selectionAlgo=algo)


print(f"Load balancer listening on {PORT} ...")
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    httpd.serve_forever()
