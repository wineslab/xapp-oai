#!/bin/bash

# release previously opened sockets

# Function to handle SIGTERM signal
sigterm_handler() {
    echo "Received SIGTERM signal. Stopping processes..."
    # Kill the Python process named "influxdb_xapp_th.py"
    pkill -SIGINT -f "python slicing_ctrl_influxdb_xapp_kpm.py"
    # Kill the process named "/usr/local/bin/hw_xapp_main"
    pkill -SIGINT -f "/usr/local/bin/hw_xapp_main"
    exit 0
}

# Register SIGTERM signal handler
trap 'sigterm_handler' SIGTERM

cd /root/git/xapp-oranslice/xapp_bs_connector/init

sleep 5

python -u init_script.py $CONFIG_FILE 2>&1 | tee /tmp/xapp_bs_connector.log &

while [ ! -f "/tmp/xapp_bs_connector.log" ]; do
    echo "Log file not found. Waiting..."
    sleep 1  # Adjust sleep duration as needed
done

while ! grep -q "Opened control socket server on port 7001" "/tmp/xapp_bs_connector.log"; do
    echo "xApp connector is not ready. Waiting 1 second"
    sleep 1  # Adjust sleep duration as needed
done

echo "Log line found. Starting the Python logic..."
sleep 7
cd /root/git/xapp-oranslice/base-xapp/ && python slicing_ctrl_influxdb_xapp_kpm.py 2>&1 | tee /tmp/xapp_py.log &

# Main loop
echo "Waiting for SIGTERM signal..."
while true; do
    sleep 1
done
