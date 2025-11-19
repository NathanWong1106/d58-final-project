import socket
import http.server, socketserver
import sys

MSG = "Hello from server!"

class SimpleServer(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    # Do something computationally intensive to simulate load
    lst = []
    for _ in range(1000000):
        lst.append('x')
    
    body = f"{MSG}\n"

    self.send_response(200)
    self.send_header("Content-Type", "text/plain")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body.encode())
    
PORT = 8080
if len(sys.argv) > 2:
  PORT = int(sys.argv[1]) 
  MSG = sys.argv[2]

# Serve on own IP address
with socketserver.TCPServer(("", PORT), SimpleServer) as httpd:
    httpd.serve_forever()