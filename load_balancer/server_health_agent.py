import http.server, socketserver
import json

PORT = 8001

class MonitorHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            response = json.dumps({"status": "healthy!"})
            self.wfile.write(bytes(response, "utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("", PORT), MonitorHandler) as httpd:
    print(f"Backend monitor serving at port {PORT}")
    httpd.serve_forever()