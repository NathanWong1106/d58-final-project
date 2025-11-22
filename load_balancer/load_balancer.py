import random
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
    def __init__ (self, 
                  sticky_sessions=False, 
                  debug_mode=False, 
                  health_check_interval=5, 
                  load_shedding_enabled=False,
                  min_shed_threshold=5, 
                  max_shed_threshold=10, 
                  max_shed_prob=0.5, 
                  shed_weight=0.8):
        
        self.sticky_sessions = sticky_sessions
        self.debug_mode = debug_mode
        self.health_check_interval = health_check_interval
        self.load_shedding_enabled = load_shedding_enabled

        # RED-like thresholds for load shedding
        self.min_shed_threshold = min_shed_threshold
        self.max_shed_threshold = max_shed_threshold
        self.max_shed_prob = max_shed_prob
        self.shed_weight = shed_weight

class LoadBalancer(object):


    def __init__(self, ip, port, servers: typing.List[Server], lb_strategy:LBStrategy, opts:LBOpts=LBOpts()):
        self.ip = ip
        self.port = port
        self.servers = servers
        self.lb_strategy = lb_strategy
        self.opts = opts

        self.server_lock = threading.Lock()
        
        # Initialize the load balancer socket - TCP
        socket.setdefaulttimeout(TIMEOUT)
        self.lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lb_socket.bind((self.ip, self.port))

        # Initialize Health Check Service
        self.health_check_service = HealthCheckService(self.servers, self.server_lock, self.opts.health_check_interval)
        self.health_check_service.start()

        # Load shedding parameters
        self.num_simultaneous_connections = 0
        self.avg_num_simultaneous_connections = 0
        self.count = 0 # RED-like count (number of undropped connections since entering the sheddable state)

        # Start listening for incoming connections - max 5 queued connections
        self.lb_socket.listen(5)

    def print_debug(self, msg):
        if self.opts.debug_mode:
            print(f"[LB] {msg}")

            with open("lb.log", "a") as f:
                f.write(f"[LB] {msg}\n")


    def start_lb(self):
        self.print_debug("Load Balancer started, waiting for connections...")
        while True:
            # Blocks until one or more sockets (fd) are ready for IO
            read_sockets, _, _= select.select([self.lb_socket], [], [])
            for sock in read_sockets:
                if sock == self.lb_socket:
                    # Create thread to handle new connection
                    self.accept_connection()
                else:
                    self.handle_data_forwarding(sock)

    def accept_connection(self):
        client_sock, client_addr = self.lb_socket.accept()

        if self.shouldShed():
            self.print_debug(f"Shedding load, rejecting connection from {client_addr}")
            
            # Send 503 service unavailable with message: The server is currently experiencing high load, please try again later.
            client_sock.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 56\r\n\r\nThe server is currently experiencing high load, please try again later.")
            client_sock.close()
            return

        # Get the server to forward to - acquire lock since health check may modify server states
        server = None
        with self.server_lock:
            server = self.lb_strategy.get_server(source_ip=client_addr[0])

            if server is not None:
                self.update_connection_count(server, is_connection=True)
                server.additional_info['errors'] = 0

        if server is None:
            self.print_debug("No healthy servers available, closing client connection")
            client_sock.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 19\r\n\r\nService Unavailable")
            client_sock.close()
            return
        
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            server_sock.connect((server.ip, server.port))
        except Exception as e:
            self.print_debug(f"Failed to connect to server {server.name} at {server.ip}:{server.port}, closing client connection")
            client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 11\r\n\r\nBad Gateway")
            client_sock.close()
            with self.server_lock:
                self.update_connection_count(server, is_connection=False)
                server.additional_info['errors'] += 1
            return

        self.print_debug(f"Accepted connection from {client_addr}, forwarding to server {server.name}")
        threading.Thread(target=self.handle_connection, args=(client_sock, server_sock, server)).start()
    
    def handle_connection(self, client_sock:socket.socket, server_sock:socket.socket, server:Server):
        
        while True:
            try:
                read_sockets, _, _= select.select([client_sock, server_sock], [], [])
                for sock in read_sockets:
                    data = sock.recv(BUF_SIZE)
                    self.print_debug(f"Received {len(data)} bytes from {'client' if sock == client_sock else 'server'}")
                    if data:
                        if sock == client_sock:
                            dest_sock = server_sock
                        else:
                            dest_sock = client_sock
   
                        dest_sock.sendall(data)
                    else:
                        self.print_debug("No data received, closing connection")
                        self.close_connection(sock, server)
                        return
            except Exception as e:
                self.print_debug(f"Exception during forwarding: {e}. Closing connection.")
                self.close_connection(sock, server, is_error=True)
                return
            
    def close_connection(self, sock:socket.socket, server:Server, is_error=False):
        sock.close()
        with self.server_lock:
            self.update_connection_count(server, is_connection=False)

            if is_error:
                server.additional_info['errors'] += 1

            self.print_debug(f"Closed connection for server {server.name} who has active connections: {server.additional_info.get('active_connections', 0)}")

    def update_connection_count(self, server:Server, is_connection: bool):
        if is_connection:
            server.additional_info['active_connections'] = server.additional_info.get('active_connections', 0) + 1
            self.num_simultaneous_connections += 1

        else:
            server.additional_info['active_connections'] = server.additional_info.get('active_connections', 0) - 1
            self.num_simultaneous_connections -= 1

        self.avg_num_simultaneous_connections = (1 - self.opts.shed_weight) * self.avg_num_simultaneous_connections + self.opts.shed_weight * self.num_simultaneous_connections


    def shouldShed(self):
        if not self.opts.load_shedding_enabled:
            return False
        
        if self.avg_num_simultaneous_connections < self.opts.min_shed_threshold:
            self.count = 0
            return False

        tempP = self.opts.max_shed_prob * (self.avg_num_simultaneous_connections - self.opts.min_shed_threshold) / (self.opts.max_shed_threshold - self.opts.min_shed_threshold)
        p = tempP / (1 - self.count * tempP)

        print(f"Shedding probability: {p}, count: {self.count}, avg connections: {self.avg_num_simultaneous_connections}")

        if random.random() < p:
            self.count = 0
            return True
        
        if self.opts.min_shed_threshold < self.avg_num_simultaneous_connections and self.avg_num_simultaneous_connections < self.opts.max_shed_threshold:
            self.count += 1
        
        return False