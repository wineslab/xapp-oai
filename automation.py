import subprocess
import time
import os

# Define commands to run as subprocesses
xapp_bs_connector_cmd = ["/root/xapp/run_xapp.sh"]
xapp_py_cmd = ["cd /root/xapp-oai-dev/base-xapp/; python influxdb_xapp_th.py"]

# Start subprocess 1 and redirect its output to /tmp/process1.log
log_file_path = "/tmp/xapp_bs_connector.log"
log_file = open(log_file_path, "w")
xapp_bs_connector_process = subprocess.Popen(xapp_bs_connector_cmd, stdout=log_file, stderr=log_file, shell=True)

# Monitor /tmp/process1.log for a specific string
specific_string = "Opened control socket server on port 7001"
process2 = None
while True:
    print("Waiting for complete initialization")
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as f:
            if specific_string in f.read():
                break
    time.sleep(5)  # Check every second

log_file_path_py = "/tmp/xapp_py.log"
log_file_py = open(log_file_path_py, "w")

xapp_py_process = subprocess.Popen(xapp_py_cmd, stdout=log_file_py, stderr=log_file_py, shell=True)

while True:
    xapp_status = xapp_py_process.poll()
    if xapp_status == None:
        time.sleep(5)
    else:
        print("xApp terminated via signal {0}\n".format(-1 * xapp_status))
        break
