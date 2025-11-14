import http.server, socketserver, threading, requests, random
import time
import sys

class SimpleServer(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    # Do something computationally intensive to simulate load
    lst = []
    for i in range(1000000):
        lst.append('x')
    
    body = f"Server: {self.server.server_address}\n"

    self.send_response(200)
    self.send_header("Content-Type", "text/plain")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body.encode())
    
PORT = 8080
if len(sys.argv) > 1:
  PORT = int(sys.argv[1]) 
with socketserver.TCPServer(("", PORT), SimpleServer) as httpd:
    httpd.serve_forever()