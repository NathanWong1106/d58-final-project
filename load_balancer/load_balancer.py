import random
import socket
import select
from serv_obj import Server
from strategies.lb_strategy import LBStrategy
import typing
import threading
from health_check import HealthCheckService
from load_shedder import LoadShedder, LoadShedParams
from http_helper import HTTPResponse
import time

SERVERS = []
BUF_SIZE = 4096
TIMEOUT = 5
session_map = {}
STICKY_TIMEOUT = 15

SHED_RESPONSE = (
    503, "The server is currently experiencing high load, please try again later.")
OVERLOADED_RESPONSE = (
    503, "No healthy servers available, please try again later.")
INTERNAL_SERVER_ERROR_RESPONSE = (500, "Internal Server Error")


class LBOpts:
    def __init__(self,
                 sticky_sessions=False,
                 debug_mode=False,
                 health_check_interval=3,
                 health_check_path="/health",
                 health_check_timeout=2,
                 load_shedding_enabled=False,
                 load_shed_params: LoadShedParams = LoadShedParams()):

        self.sticky_sessions = sticky_sessions
        self.debug_mode = debug_mode
        self.health_check_interval = health_check_interval
        self.health_check_path = health_check_path
        self.health_check_timeout = health_check_timeout
        self.load_shedding_enabled = load_shedding_enabled
        self.load_shed_params = load_shed_params


class LoadBalancer(object):

    def __init__(self, ip, port, servers: typing.List[Server], lb_strategy: LBStrategy, opts: LBOpts = LBOpts()):
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
        self.health_check_service = HealthCheckService(
            self.servers, self.server_lock, self.opts.health_check_interval, self.opts.health_check_path, self.opts.health_check_timeout)
        self.health_check_service.start()

        # Load shedding parameters
        self.load_shedder = LoadShedder(self.opts.load_shed_params)

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
            read_sockets, _, _ = select.select([self.lb_socket], [], [])
            for sock in read_sockets:
                if sock == self.lb_socket:
                    # Create thread to handle new connection
                    self.accept_connection()

    def get_sid(self, req):
        for header in req.split('\r\n'):
            if 'SID:' in header:
                return header.split(' ')[1]
        return None

    def accept_connection(self):
        client_sock, client_addr = self.lb_socket.accept()
        req = client_sock.recv(BUF_SIZE, socket.MSG_PEEK).decode()

        # Get the server to forward to - acquire lock since health check may modify server states
        server = None

        # If client does not sent SID, use their IP instead for sticky
        sid = self.get_sid(req) or client_addr[0]
        with self.server_lock:
            self.print_debug(
                f"Servers status: {[{'name': s.name, 'healthy': s.healthy, 'avg_rtt': s.get_additional_info('health_check_info').get_average_rtt()} for s in self.servers]}")
            if self.opts.load_shedding_enabled and self.load_shedder.should_shed():
                self.print_debug(
                    f"Shedding load, rejecting connection from {client_addr}")
                self.try_send_error(
                    client_sock, SHED_RESPONSE[0], SHED_RESPONSE[1])
                client_sock.close()
                return

            # Check if sid is in sticky session mapping
            if (self.opts.sticky_sessions):
                (server, last_used) = session_map.get(sid, (None, 0))
                if (time.time() - last_used >= STICKY_TIMEOUT):
                    server = None
            if server is None:
                server = self.lb_strategy.get_server(source_ip=client_addr[0])

            if server is not None:
                # print(f'{client_addr[0]} to {server.ip}')
                self.update_connection_count(server, is_connection=True)
                session_map[sid] = (server, time.time())
                server.additional_info['active_connections'] = server.additional_info.get(
                    'active_connections', 0) + 1
                server.additional_info['errors'] = 0

        if server is None:
            self.print_debug(
                "No healthy servers available, closing client connection")
            self.try_send_error(
                client_sock, OVERLOADED_RESPONSE[0], OVERLOADED_RESPONSE[1])
            client_sock.close()
            return

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread(target=self.handle_connection, args=(
            client_sock, server_sock, server)).start()

    def handle_connection(self, client_sock: socket.socket, server_sock: socket.socket, server: Server):
        try:
            server_sock.connect((server.ip, server.port))
        except Exception as e:
            self.print_debug(
                f"Failed to connect to server {server.name} at {server.ip}:{server.port}, closing client connection")
            self.try_send_error(
                client_sock, INTERNAL_SERVER_ERROR_RESPONSE[0], INTERNAL_SERVER_ERROR_RESPONSE[1])
            client_sock.close()
            with self.server_lock:
                self.update_connection_count(server, is_connection=False)
                server.additional_info['errors'] += 1
            return

        self.print_debug(
            f"Accepted connection from {client_sock.getpeername()}, forwarding to server {server.name}")

        while True:
            try:
                read_sockets, _, _ = select.select(
                    [client_sock, server_sock], [], [])
                for sock in read_sockets:
                    data = sock.recv(BUF_SIZE)
                    self.print_debug(
                        f"Received {len(data)} bytes from {'client' if sock == client_sock else 'server'}")
                    if data:
                        if sock == client_sock:
                            dest_sock = server_sock
                        else:
                            dest_sock = client_sock

                        dest_sock.sendall(data)
                    else:
                        self.print_debug(
                            "No data received, closing connection")
                        self.close_connection(sock, server)
                        return
            except Exception as e:
                self.print_debug(
                    f"Exception during forwarding: {e}. Closing connection.")
                self.try_send_error(
                    client_sock, INTERNAL_SERVER_ERROR_RESPONSE[0], INTERNAL_SERVER_ERROR_RESPONSE[1])
                self.close_connection(sock, server, is_error=True)
                return

    def close_connection(self, sock: socket.socket, server: Server, is_error=False):
        sock.close()
        with self.server_lock:
            self.update_connection_count(server, is_connection=False)

            if is_error:
                server.additional_info['errors'] += 1

            self.print_debug(
                f"Closed connection for server {server.name} who has active connections: {server.additional_info.get('active_connections', 0)}")

    def update_connection_count(self, server: Server, is_connection: bool):
        if is_connection:
            server.additional_info['active_connections'] = server.additional_info.get(
                'active_connections', 0) + 1
            self.load_shedder.increment_connections()

        else:
            server.additional_info['active_connections'] = server.additional_info.get(
                'active_connections', 0) - 1
            self.load_shedder.decrement_connections()

    def try_send_error(self, client_sock: socket.socket, status_code: int, msg: str):
        try:
            http_response = HTTPResponse(
                status_code, msg).get_response_string()
            client_sock.sendall(http_response.encode())
        except Exception as e:
            self.print_debug(f"Error sending {status_code} response: {e}")
