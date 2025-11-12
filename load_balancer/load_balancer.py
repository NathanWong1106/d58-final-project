import http.server, socketserver, threading, requests, random
import time
import hashlib


#TODO: support dynamic setup
servers = [
    {"http": "http://10.0.1.1:8080",
     "connections": 0},
    {"http": "http://10.0.1.2:8081",
     "connections": 0},
    {"http": "http://10.0.1.3:8082",
     "connections": 0}]

#TODO: support the dynamic switching of algorithms?
class SelectionAlgo:
    def select_server(self, servers, **kwargs):
        raise NotImplementedError
    
class RoundRobin(SelectionAlgo):
    def __init__(self):
        self.index = -1
        
    def select_server(self, servers, **kwargs):
        self.index += 1
        return servers[self.index % len(servers)]

class RandomSelection(SelectionAlgo):
    def select_server(self, servers, **kwargs):
        return random.choice(servers)
    
class LeastConnection(SelectionAlgo):
    def select_server(self, servers, **kwargs):
        least = min(servers, key=lambda server: server["connections"])
        return least
    
#TODO: for dynamic server connections, requires consistent hashing using hash rings, also python hash intentionally randomizes so might need different hash
class SimpleSourceIPHash(SelectionAlgo):
    def select_server(self, servers, **kwargs):
        h = hashlib.md5(bytes(kwargs.get("source_ip"), "UTF-8"))
        return servers[abs(int(h.hexdigest(), 16)) % len(servers)]

#Choose algo
algo = SimpleSourceIPHash()

# TODO: replace with actual
class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        server = algo.select_server(servers, source_ip=self.client_address[0])
        server["connections"] += 1
        backend = server["http"]
        print(f'[LB] Forwarding request for to {backend}')
        
        r = requests.get(backend + self.path)
        self.send_response(r.status_code)
        for k, v in r.headers.items():
            if k.lower() not in ["content-encoding", "transfer-encoding"]:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(r.content)

PORT = 80
print(f"Layer7 load balancer listening on {PORT} ...")
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
    httpd.serve_forever()