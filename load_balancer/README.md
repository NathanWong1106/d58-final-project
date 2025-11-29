### Setup
This folder should be mounted as a volume (or copied) into the Mininet Virtual Machine. They can be found here: https://github.com/mininet/mininet/releases/

Once mounted or copied, install the necessary dependencies using `sudo ./setup.sh`

### Running tests
You should be in the root directory of the project (`load_balancer`)

To run tests: `sudo python3 -m test.tests.{test_name}`
- For example: `sudo python3 -m test.tests.test_round_robin`
- A result summary of the test will be shown in the command line
- Relevant plots will be written to `load_balancer/test/results` 

To try different parameters (e.g. load shed threshold), you can edit the corresponding parameter value in the associated config JSON located at `load_balancer/test/setup` (e.g. change to `"sim_conn_threshold": 10` in `load_balancer/test/setup/load_shed_test_lb.json`)