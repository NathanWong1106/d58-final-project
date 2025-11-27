import time
from test.tests.req_result_obj import RequestResult

def send_requests(c, lock, results, lb, end_time):
    while time.time() < end_time:
        start_time = time.time()
        # send a simple HTTP request to the LB and capture headers+body
        resp = c.cmd(f'curl --max-time 6 -i http://{lb.IP()}')
        with lock:
            results.append(RequestResult(resp, start_time, time.time()))
        
        # tiny pause to create a stream of requests
        time.sleep(0.02)