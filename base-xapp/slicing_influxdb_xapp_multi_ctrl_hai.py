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

def trigger_indication():
    print("encoding sub request")
    master_mess = ran_messages_pb2.RAN_message()
    master_mess.msg_type = ran_messages_pb2.RAN_message_type.INDICATION_REQUEST
    inner_mess = ran_messages_pb2.RAN_indication_request()
    inner_mess.target_params.extend([ran_messages_pb2.RAN_parameter.GNB_ID, ran_messages_pb2.RAN_parameter.UE_LIST])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    print(buf)
    return buf

def trigger_slicing_control(sst = 1, have_sd = True, min_ration = 20, max_ration = 80):
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
            print(resp)
            print("report index " + str(report_index))
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
                            .field("dl_th", dl_th).field("ul_th", ul_th)
                    print(p)
                    logging.info('Write to influxdb: ' + repr(p))
                    write_api.write(bucket=bucket, record=p)

                except Exception as e:
                    print("Skip log, influxdb error: " + str(e))
     
            if not (report_index % 5):
                if dummy_ai_ctrl:
                    # Read of data
                    # ue1 = read_dl_thruput()
                    # ue2 = read_dl_thruput()
                    # Simple AI Control Check
                    
                    # Sending Control
                    dummy_data_driven_ctrl(ue_data_dict, control_sck)
                else:
                    control_buf = trigger_slicing_control(min_ration=10, max_ration= 10 + (report_index % 90) )
                    send_socket(control_sck, control_buf)
                    print("Control Buff Sent!\n")

def dummy_data_driven_ctrl(ue_dict, ctrl_sock):
    """Assume there are only two rnti
    """
    
    rnti_list = list(ue_dict.keys())

    sst_1 = ue_dict[rnti_list[0]]['nssai_sst']
    sd_1  = ue_dict[rnti_list[0]]['nssai_sd']

    sst_2 = ue_dict[rnti_list[1]]['nssai_sst']
    sd_2  = ue_dict[rnti_list[1]]['nssai_sd']

    if ue_dict[rnti_list[0]]['dl_th'] > ue_dict[rnti_list[1]]['dl_th']:

        control_buf = trigger_slicing_control(sst=sst_1, have_sd=sd_1, min_ration=10, max_ration= 10 )
        send_socket(ctrl_sock, control_buf)
        print(f"Control Buff for NSSAI SST {sst_1} SD {sd_1} Sent!\n")
        control_buf = trigger_slicing_control(sst=sst_2, have_sd=sd_2, min_ration=10, max_ration= 90 )
        send_socket(ctrl_sock, control_buf)
        print(f"Control Buff for NSSAI SST {sst_2} SD {sd_2} Sent!\n")

    else:

        control_buf = trigger_slicing_control(sst=sst_1, have_sd=sd_1, min_ration=10, max_ration= 90 )
        send_socket(ctrl_sock, control_buf)
        print(f"Control Buff for NSSAI SST {sst_1} SD {sd_1} Sent!\n")
        control_buf = trigger_slicing_control(sst=sst_2, have_sd=sd_2, min_ration=10, max_ration= 10 )
        send_socket(ctrl_sock, control_buf)
        print(f"Control Buff for NSSAI SST {sst_2} SD {sd_2} Sent!\n")



if __name__ == '__main__':

    dummy_ai_ctrl = True
    main()

