import socket
import select
from serv_obj import Server
from strategies.lb_strategy import LBStrategy
import typing
import threading
from health_check import HealthCheckService

SERVERS = []
BUF_SIZE = 4096
TIMEOUT = 5

class LBOpts:
    def __init__ (self, sticky_sessions=False, debug_mode=False, health_check_interval=5):
        self.sticky_sessions = sticky_sessions
        self.debug_mode = debug_mode
        self.health_check_interval = health_check_interval

class LoadBalancer(object):


    def __init__(self, ip, port, servers: typing.List[Server], lb_strategy:LBStrategy, opts:LBOpts=LBOpts()):
        self.ip = ip
        self.port = port
        self.servers = servers
        self.lb_strategy = lb_strategy
        self.opts = opts

        self.client_to_server = {}
        self.server_to_client = {}
        self.active_sockets = set()

        self.server_lock = threading.Lock()
        
        # Initialize the load balancer socket - TCP
        self.lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lb_socket.setblocking(False)
        self.lb_socket.bind((self.ip, self.port))

        # Initialize Health Check Service
        self.health_check_service = HealthCheckService(self.servers, self.server_lock, self.opts.health_check_interval)
        self.health_check_service.start()

        # Start listening for incoming connections - max 5 queued connections
        self.lb_socket.listen(5)

        self.active_sockets.add(self.lb_socket)

    def print_debug(self, msg):
        if self.opts.debug_mode:
            print(f"[LB] {msg}")

            with open("lb.log", "a") as f:
                f.write(f"[LB] {msg}\n")


    def start_lb(self):
        self.print_debug("Load Balancer started, waiting for connections...")
        while True:
            # Blocks until one or more sockets (fd) are ready for IO - need this for non-blocking sockets
            read_sockets, write_sockets, x_sockets = select.select(self.active_sockets, [], [])
            for sock in read_sockets:
                if sock == self.lb_socket:
                    self.accept_connection()
                else:
                    self.handle_data_forwarding(sock)
            
            for sock in write_sockets:
                self.handle_data_forwarding(sock)

            for sock in x_sockets:
                self.print_debug(f"Exception on socket {sock}, closing connection")
                self.close_connection(sock)
            

    def accept_connection(self):
        client_sock, client_addr = self.lb_socket.accept()
        client_sock.settimeout(TIMEOUT)
        client_sock.setblocking(False)

        # Get the server to forward to - acquire lock since health check may modify server states
        server = None
        with self.server_lock:
            server = self.lb_strategy.get_server()

        if server is None:
            self.print_debug("No healthy servers available, closing client connection")
            client_sock.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nService Unavailable")
            client_sock.close()
            return

        forward_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        forward_sock.settimeout(TIMEOUT)
        forward_sock.setblocking(False)

        conn_res = forward_sock.connect_ex((server.ip, server.port))

        # Since connect_ex is non-blocking, it may return EINPROGRESS which is acceptable
        if conn_res != 0 and conn_res != socket.errno.EINPROGRESS:
            self.print_debug(f"Failed to connect to server {server.name} at {server.ip}:{server.port}, closing client connection")
            client_sock.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nService Unavailable")
            client_sock.close()
            forward_sock.close()
            return
        
        self.active_sockets.add(client_sock)
        self.active_sockets.add(forward_sock)

        self.client_to_server[client_sock] = forward_sock
        self.server_to_client[forward_sock] = client_sock

        self.print_debug(f"Accepted connection from {client_addr}, forwarding to server {server.name}")

    def handle_data_forwarding(self, sock):
        try:
            data = sock.recv(BUF_SIZE)
            self.print_debug(f"Received data: {data}")
            if data:
                # Determine where to forward
                if sock in self.client_to_server:
                    dest_sock = self.client_to_server[sock]
                elif sock in self.server_to_client:
                    dest_sock = self.server_to_client[sock]
                else:
                    self.print_debug("Could not find destination socket for forwarding")
                    return

                dest_sock.sendall(data)
            else:
                self.print_debug("No data received, closing connection")
                # No data --> close connection
                self.close_connection(sock)
        except Exception as e:
            self.print_debug(f"Exception during forwarding: {e}. Closing connection.")
            self.close_connection(sock)

    def close_connection(self, sock):
        # Find the socket pairs
        client_sock = None
        server_sock = None

        if sock in self.client_to_server:
            client_sock = sock
            server_sock = self.client_to_server.pop(client_sock, None)
            if server_sock:
                self.server_to_client.pop(server_sock, None)
        elif sock in self.server_to_client:
            server_sock = sock
            client_sock = self.server_to_client.pop(server_sock, None)
            if client_sock:
                self.client_to_server.pop(client_sock, None)

        # Remove from active sockets and close connections
        if client_sock:
            self.active_sockets.discard(client_sock)
            try:
                client_sock.close()
            except Exception:
                pass

        if server_sock:
            self.active_sockets.discard(server_sock)
            try:
                server_sock.close()
            except Exception:
                pass

        self.print_debug("Closed connection between client and server")
