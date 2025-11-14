import http.server, socketserver, threading, requests, random
import time
import hashlib


#TODO: support dynamic setup
servers = [
    {"http": "http://10.0.1.1:8080",
     "connections": 0,
     "weight": 3},
    {"http": "http://10.0.1.2:8081",
     "connections": 0,
     "weight": 2},
    {"http": "http://10.0.1.3:8082",
     "connections": 0,
     "weight": 1}]

#TODO: support the dynamic switching of algorithms?
class StaticSelectionAlgo:
    def select_server(self, servers, **kwargs):
        raise NotImplementedError
    
class RoundRobin(StaticSelectionAlgo):
    def __init__(self):
        self.index = -1
        self.server_list = []
        
    def select_server(self, servers, **kwargs):
        # Build weighted server list
        # Each server appears in list as many times as its
        # Example: weights [3, 2, 1] -> [server1, server1, server1, server2, server2, server3]
        if not self.server_list:
            self.server_list = [server for server in servers 
                               for _ in range(server.get("weight", 1))]
        
        # Cycle through the weighted list for each request
        self.index = (self.index + 1) % len(self.server_list)
        return self.server_list[self.index]

class RandomSelection(StaticSelectionAlgo):
    def select_server(self, servers, **kwargs):
        return random.choice(servers)
    
class LeastConnection(StaticSelectionAlgo):
    def select_server(self, servers, **kwargs):
        # Select server with lowest connections/weight ratio
        def connection_ratio(server):
            connections = server.get("connections", 0)
            weight = server.get("weight", 1)
            
            # Return infinite ratio for invalid weights, or connections/weight otherwise
            return float('inf') if weight <= 0 else connections / weight
        
        return min(servers, key=connection_ratio)
    
#TODO: for dynamic server connections, requires consistent hashing using hash rings, also python hash intentionally randomizes so might need different hash
class SimpleSourceIPHash(StaticSelectionAlgo):
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
