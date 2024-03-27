import logging
from os import lseek
from xapp_control import *
import importlib
ran_messages_pb2 = importlib.import_module("oai-oran-protolib.builds.ran_messages_pb2")
from time import sleep, time
import socket
from random import randint

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.query_api import QueryOptions
import datetime


## Variables
DUMMY_AI_CTRL = True    # Enable dummy AI control on the slicing
CTRL_FREQ = 15          # Frequency for the slicing control


def trigger_indication():
    print("encoding sub request")
    master_mess = ran_messages_pb2.RAN_message()
    master_mess.msg_type = ran_messages_pb2.RAN_message_type.INDICATION_REQUEST
    inner_mess = ran_messages_pb2.RAN_indication_request()
    inner_mess.target_params.extend([ran_messages_pb2.RAN_parameter.GNB_ID, ran_messages_pb2.RAN_parameter.UE_LIST])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    # print(buf)
    return buf

def trigger_slicing_control(sst = 1, have_sd = False, min_ration = 20, max_ration = 80):
    print("Encoding initial RIC Control request")
    slicing_mess = ran_messages_pb2.slicing_control_m()
    slicing_mess.sst = sst
    if have_sd:
        slicing_mess.sd  = 2
    else:
        pass
    slicing_mess.min_ratio = min_ration
    slicing_mess.max_ratio = max_ration

    ctrl_mess  = ran_messages_pb2.RAN_param_map_entry()
    ctrl_mess.key = ran_messages_pb2.RAN_parameter.SLICING_CONTROL
    ctrl_mess.slicing_ctrl.CopyFrom(slicing_mess)

    inner_mess = ran_messages_pb2.RAN_control_request()
    inner_mess.target_param_map.append(ctrl_mess)

    master_mess = ran_messages_pb2.RAN_message()
    master_mess.msg_type = ran_messages_pb2.RAN_message_type.CONTROL
    master_mess.ran_control_request.CopyFrom(inner_mess)

    buf = master_mess.SerializeToString()

    return buf

def execute_query(query_api, bucket, start_time, end_time, field, n):
    """Build, execute InfluxDB query, and return result"""

    # Convert times to string in RFC3339 format, which is required by Flux
    start_time_str = start_time + "Z"
    end_time_str = end_time + "Z"

    # Build the query
    query_latest_points = f"""
                    from(bucket: "{bucket}")
                    |> range(start: {start_time_str}, stop: {end_time_str})
                    |> filter(fn: (r) => r._measurement == "xapp-stats" and r._field == "{field}")
                    |> group(columns: ["rnti"])
                    |> sort(columns: ["_time"], desc: true)
                    |> limit(n:{n})
                    """

    # Execute the quetry
    return query_api.query(query_latest_points)


def query_rnti(query_api, bucket, start_time, end_time):
    """Query rnti and slices data from InfluxDB and returning a map of rnti with slices"""

    # Execute queries to get slice for each rnti and downlink throughput info
    sst_data = execute_query(query_api, bucket, start_time, end_time, "nssai_sst", 1)
    sd_data = execute_query(query_api, bucket, start_time, end_time, "nssai_sd", 1)

    # Map RNTI with sst and sd
    rnti_slice_mapping = {}
    for sst_table in sst_data:
        for sst_record in sst_table:
            rnti = sst_record.values['rnti']
            sst = sst_record.values['_value']
            rnti_slice_mapping[rnti] = {'sst': sst}


    for sd_table in sd_data:
        for sd_record in sd_table:
            rnti = sd_record.values['rnti']
            sd = sd_record.values['_value']
            if rnti in rnti_slice_mapping:
                rnti_slice_mapping[rnti]['sd'] = sd

    return rnti_slice_mapping


def query_dl_data(query_api, bucket, start_time, end_time, rnti_slice_mapping):
    """Query Downlink data from InfluxDB and returning a map of avg dl data with slices""" 

    dlth_data = execute_query(query_api, bucket, start_time, end_time, "dl_th", 10)

    # Map each slide with downlink throughput and compute average
    slice_dlth_mapping = {}
    for dlth_table in dlth_data:
        for dlth_record in dlth_table:
            rnti = dlth_record.values['rnti']
            dl_th = float(dlth_record.values['_value'])

            # Check rnti is in rnti_slice_mapping and both sst and sd are defined
            if rnti in rnti_slice_mapping and 'sst' in rnti_slice_mapping[rnti] and 'sd' in rnti_slice_mapping[rnti]:
                slice_id = (rnti_slice_mapping[rnti]['sst'], rnti_slice_mapping[rnti]['sd'])

                if slice_id not in slice_dlth_mapping:
                    slice_dlth_mapping[slice_id] = {'total_dl_th': 0, 'count': 0}

                slice_dlth_mapping[slice_id]['total_dl_th'] += dl_th
                slice_dlth_mapping[slice_id]['count'] += 1
            else:
                # rnti does not have defined sst and sd, skip processing
                continue

    for slice_id, data in slice_dlth_mapping.items():
        avg_dl_th = data['total_dl_th'] / data['count']
        slice_dlth_mapping[slice_id]['avg_dl_th'] = avg_dl_th

    return slice_dlth_mapping


def main():

    waittime = 1
    print("Will wait {} seconds for xapp-sm to start".format(waittime))
    sleep(waittime)

    buf = trigger_indication()

    UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketOut.sendto(buf, ("127.0.0.1",7001))

    print("request sent, now waiting for incoming answers")

    control_sck = open_control_socket(4200)

    bucket = "wineslab-xapp-demo"
    client = InfluxDBClient.from_config_file("influx-db-config.ini")
    print(client)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    query_api = client.query_api(query_options=QueryOptions())

    report_index = 0

    ue_data_dict = {}   # Initialize an empty dictionary to store UE data

    while True:
        #logging.info("loop again")
        data_sck = receive_from_socket(control_sck)
        if len(data_sck) <= 0:
            logging.info("leq 0 data")
            if len(data_sck) == 0:
                continue
            else:
                logging.info('Negative value for socket')
                break
        else:
            #logging.info('Received data: ' + repr(data_sck))
            #print(data_sck)
            print("RIC report received")
            resp = ran_messages_pb2.RAN_indication_response()
            resp.ParseFromString(data_sck)
            # print(resp)
            # print("report index " + str(report_index))
            report_index += 1

            ue_info_list = list()

            for entry in resp.param_map:
                if entry.key == ran_messages_pb2.RAN_parameter.UE_LIST:
                    if entry.ue_list.connected_ues > 0:
                        for ue_i in range(0, entry.ue_list.connected_ues):
                            ue_info_list.append(entry.ue_list.ue_info[ue_i])

            # check if there's any ue connected
            if len(ue_info_list) == 0:
                print("\t---------")
                print("\tNo ues connected, sleeping 1s")
                sleep(1)
                continue

            for idx, ue in enumerate(ue_info_list):
                # print(ue)
                try:

                    timestamp = time()
                    rnti = ue.rnti
                    avg_rsrp = ue.avg_rsrp
                    ph = ue.ph
                    pcmax = ue.pcmax
                    dl_total_bytes = ue.dl_total_bytes
                    dl_errors = ue.dl_errors
                    dl_bler = ue.dl_bler
                    dl_mcs = ue.dl_mcs
                    ul_total_bytes = ue.ul_total_bytes
                    ul_errors = ue.ul_errors
                    ul_bler = ue.ul_bler
                    ul_mcs = ue.ul_mcs

                    nssai_sst = ue.nssai_sST
                    nssai_sd  = ue.nssai_sD

                    # Compute throughput [Mbps] based on RNTI, timestamp, and dl_total_bytes
                    if rnti in ue_data_dict:
                        dl_th = ((dl_total_bytes - ue_data_dict[rnti]['dl_total_bytes'])/(timestamp - ue_data_dict[rnti]['timestamp']))*8
                        ul_th = ((ul_total_bytes - ue_data_dict[rnti]['ul_total_bytes'])/(timestamp - ue_data_dict[rnti]['timestamp']))*8
                        
                        if dl_th > 60000000:
                            dl_th = 60000000

                    else:
                        dl_th = 0.0
                        ul_th = 0.0

                    # Add or update rnti dictionary
                    ue_data_dict[rnti] = {
                        'timestamp': timestamp,
                        'dl_total_bytes': dl_total_bytes,
                        'ul_total_bytes': ul_total_bytes,
                        'nssai_sst':nssai_sst,
                        'nssai_sd':nssai_sd,
                        'dl_th':dl_th,
                        'ul_th':ul_th
                    }
                    # ue_data_dict[rnti]['dl_th_history'] 

                    p = Point("xapp-stats").tag("rnti", rnti).field("timestamp", timestamp).field("avg_rsrp", avg_rsrp).field("ph", ph).field("pcmax", pcmax)\
                            .field("dl_total_bytes", dl_total_bytes).field("dl_errors", dl_errors).field("dl_bler", dl_bler).field("dl_mcs", dl_mcs)\
                            .field("ul_total_bytes", ul_total_bytes).field("ul_errors", ul_errors).field("ul_bler", ul_bler).field("ul_mcs", ul_mcs)\
                            .field("nssai_sst", nssai_sst).field("nssai_sd", nssai_sd).field("dl_th", dl_th).field("ul_th", ul_th)
                    print(p)
                    # logging.info('Write to influxdb: ' + repr(p))
                    write_api.write(bucket=bucket, record=p)

                except Exception as e:
                    print("Skip log, influxdb error: " + str(e))
     
            if not (report_index % CTRL_FREQ):
                if DUMMY_AI_CTRL:
                    
                    # Get start and end datetime
                    start_time = datetime.datetime.now() - datetime.timedelta(seconds=60)
                    start_time = start_time.isoformat()
                    end_time = datetime.datetime.now() + datetime.timedelta(hours=16) # Delta for timezones
                    end_time = end_time.isoformat()

                    rnti_slice_mapping = query_rnti(query_api, bucket, start_time, end_time)
                    print(rnti_slice_mapping)
                    slice_dlth_mapping = query_dl_data(query_api, bucket, start_time, end_time, rnti_slice_mapping)
                    print(slice_dlth_mapping)

                    # Sending Control
                    dummy_data_driven_ctrl(slice_dlth_mapping, control_sck)
                else:
                    control_buf = trigger_slicing_control(min_ration=10, max_ration= 10 + (report_index % 90) )
                    send_socket(control_sck, control_buf)
                    print("Control Buff Sent!\n")


def dummy_data_driven_ctrl(slice_dlth_mapping, ctrl_sock):
    """Assume there are only two rnti
    """
    
    sst_list = []
    sd_list = []
    dlth_list = []

    # Remove slice (0,0) which is the N/A, and create lists
    for (sst,sd), data in slice_dlth_mapping.items():
        if sst == 0 and sd == 0:
            continue
        else:
            sst_list.append(sst)
            sd_list.append(sd)
            dlth_list.append(data['avg_dl_th'])
    
    # Check if slice control is needed when at least 2 slices are found
    if len(dlth_list) < 2:
        return

    # Condition for change and defining slice to be 5 and 90
    index10 = 1 if dlth_list[0] < dlth_list[1] else 0
    index90 = 0 if index10 == 1 else 1
    sst10, sd10 = sst_list[index10], sd_list[index10]
    sst90, sd90 = sst_list[index90], sd_list[index90]
    
    # Send control
    control_buf = trigger_slicing_control(sst=sst10, have_sd=sd10, min_ration=5, max_ration=5)
    send_socket(ctrl_sock, control_buf)
    print(f"Control Buff 5 for NSSAI SST {sst10} SD {sd10} Sent!\n")
    sleep(0.5)
    control_buf = trigger_slicing_control(sst=sst90, have_sd=sd90, min_ration=10, max_ration=95)
    send_socket(ctrl_sock, control_buf)
    print(f"Control Buff 95 for NSSAI SST {sst90} SD {sd90} Sent!\n")


if __name__ == '__main__':
    main()

