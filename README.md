# d58-final-project


## Setup
You'll want to have the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension installed on VSCode to make your life easier.

After installing the extension, you can run the `> Dev Containers: Reopen in Container` command to open up `/load_balancer` in a VSCode instance attached to the container. This will also run `setup.sh` for you.

To run the test topology, use `python3 test_topo.py` in the `/load_balancer` directory

To test load balancer, use `python3 lb_test_topo.py` in the `/load_balancer` directory
Choose Mininet topology inside `lb_test_topo.py`
Choose LB algorithm inside `load_balancer.py`
Search for the word `choose`