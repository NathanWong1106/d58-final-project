import http.server, socketserver, threading, requests, random
import time
import hashlib

from dynamic_selection import DynamicRoundRobin
from resource_based_selection import ResourceBased


#TODO: support dynamic setup
servers = ['10.0.1.1', '10.0.1.2', '10.0.1.3']

# Choose selection algorithm
algo = DynamicRoundRobin()

# Choose dynamic filter
ResourceBased(servers=servers, selectionAlgo=algo)

# TODO: replace with actual
class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        server = algo.select_server()
        # print(f'[LB] Forwarding request to {server}')

        if server is None:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'Service Unavailable')
            return
        

        try:
            r = requests.get('http://' + server + ':8000' + self.path, timeout=2.5)
        except requests.exceptions.RequestException as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b'Bad Gateway')
            print(f'[LB] Error forwarding to {server}: {e}')
            return
        
        
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
