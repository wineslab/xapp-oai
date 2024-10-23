# ORANSlice xApp Branch 

The branch includes the code for RAN Slicing Ctrl and KPM report functions for ORANSlice.

## How to run

### xApp BS Connector
In one terminal, run
```
cd xapp_bs_connector
./run_xapp.sh
```

### base xApp
In another terminal, run
```
cd base-xapp
python slicing_ctrl_influxdb_xapp_kpm.py
```
