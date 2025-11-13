import psutil
import http.server, socketserver
import json

HEALTH_METRICS = {
    "cpu_usage": lambda: psutil.cpu_percent(interval=1),
    "memory_usage": lambda: psutil.virtual_memory().percent
}

def get_system_health():
    health_data = {}
    for metric, func in HEALTH_METRICS.items():
        try:
            health_data[metric] = func()
        except Exception as e:
            health_data[metric] = f"Error: {e}"
    return health_data

PORT = 8001

class MonitorHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            response = json.dumps(get_system_health())
            self.wfile.write(bytes(response, "utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("", PORT), MonitorHandler) as httpd:
    print(f"Backend monitor serving at port {PORT}")
    httpd.serve_forever()