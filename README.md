# D58 Final Project - Application Load Balancer

Video Demo: https://www.youtube.com/watch?v=mKwDuPkUvUU

## Group Members
- Nathan Wong
- Shivam Bhatt
- Billy Zhou

## Overview
We implement a simple application load balancer, a set of load balancing strategies, and tests used for experimentation and evaluation of our implementation. The load balancer forwards client connections to backend servers, performs health checks, supports sticky sessions, load-shedding, and can be configured with different selection strategies.

## Main Features
- **Server Selection Strategies:** Round-robin, Weighted Round-Robin, Least Connections, Least Response Time (uses moving-average RTT from health checks), and Consistent Hashing (source-IP hashing).
- **Health checks:** Periodic HTTP GET checks (default path `/health` on port 80) that update per-server health status and average RTT.
- **Load shedding:** Configurable shedding behavior (exponential probability-based or hard threshold) to reject clients when overall simultaneous connections exceed safe (configured) limits.
- **Sticky sessions:** Optional sticky session support idenitified by a `SID` header or client IP with a timeout.
- **Load Balancer/Distributed Application Test Harness:** Configurable test scenarios, pre-made configuration JSON, plot generation from result data

## Repository Structure
- `load_balancer/load_balancer.py` -- main accept loop, connection forwarding, session mapping, and starts health check and load shed services.
- `load_balancer/health_check.py` -- background service performing health checks and recording average RTT per server.
- `load_balancer/load_shedder.py` -- decides when to shed connections (exponential/hard threshold).
- `load_balancer/serv_obj.py` -- `Server` object storing `ip`, `port`, `healthy` flag, and `additional_info` used by strategies.
- `load_balancer/http_helper.py` -- small helper for constructing HTTP error responses.
- `load_balancer/strategies/` -- pluggable selection strategies (see files in the folder).
- `load_balancer/test/` -- tests, test setups (JSON config files), and result plotting helpers.
- `load_balancer/test/setup/` -- configurable mininet topographies, JSON configuration files, test application server instance

## Configuration/Options
We define the following JSON configuration format:
```js
{
  "load_balancer_ip": "10.0.0.254", /* IP of the LB host */
  "load_balancer_port": 80, /* What port the LB is served on */
  
  /* How often health checks trigger (seconds) */
  "health_check_interval": 3, 
  
  /* How long a health check should wait before marking the server unhealthy */
  "health_check_timeout": 2,


  /* For each server, dedicated health check endpoint path */
  "health_check_path": "/health",


  /* Each usable server name, IP, port, and optional weight (for weighted RR) */
  "servers": [
    { "name": "s1", "ip": "10.0.1.1", "port": 80, "weight": 1 },
    { "name": "s2", "ip": "10.0.1.2", "port": 80 },
    { "name": "s3", "ip": "10.0.1.3", "port": 80 }
  ],


  "strategy": "round_robin", /* round_robin, hash, weighted_round_robin, least_connections, least_response_time*/
  "sticky_sessions": false, /* enable sticky sessions? */
  "debug_mode": true, /* print to lb.log? */
  "load_shedding_enabled": true, /* load shedding enabled? */
  "load_shed_params": {
    "sim_conn_threshold": 5, /*how many simultaneous connections before shed*/
    
    /*hard - shed all above thresh, exponential - probability based*/
    "strategy": "hard"
  }
}
```

## Running / Testing

### Running the Load Balancer
- For convenience, `run_load_balancer.py` takes as an argument the path to the load balancer JSON config file to start the load balancer.
    - For example `python3 -u run_load_balancer.py /test/setup/default_test_lb.json`

### Testing
- The `load_balancer/test` package contains tests and small scripts for running different scenarios. Test configuration JSON files live in `load_balancer/test/setup/`.
- Example test invocation (from the `load_balancer` directory):

```bash
sudo python3 -m test.tests.test_round_robin
```

Result summaries will be printed to console and generated plots will be written to `load_balancer/test/results/`.

### Development Notes
- The project was designed to work in a Mininet VM environment - see `load_balancer/README.md` for VM mounting and setup instructions.
- Test results are highly dependent on VM and host resources. Parameters (e.g. load shed threshold, health check intervals, timeouts, etc) may need to change to accomodate the host system.
