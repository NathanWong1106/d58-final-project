#!/bin/bash

# Create symbolic links for Open vSwitch controller
sudo ln /usr/bin/ovs-testcontroller /usr/bin/controller

# Start openswitch service
service openvswitch-switch start