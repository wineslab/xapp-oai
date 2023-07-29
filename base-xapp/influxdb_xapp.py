import logging
from os import lseek
from xapp_control import *
import xapp_control_ricbypass
from  ran_messages_pb2 import *
from time import sleep
import socket
from random import randint

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

BYPASS_RIC = False


def trigger_indication():
    print("encoding sub request")
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    print(buf)
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
            resp = RAN_indication_response()
            resp.ParseFromString(data_sck)
            print(resp)
            print("report index " + str(report_index))
            report_index += 1
            
            ue_info_list = list()

            for entry in resp.param_map:
                if entry.key == RAN_parameter.UE_LIST:
                    if entry.ue_list.connected_ues > 0:
                        for ue_i in range(0, entry.ue_list.connected_ues):
                            ue_info_list.append(entry.ue_list.ue_info[ue_i])

            # check if there's any ue connected
            if len(ue_info_list) == 0:
                print("\t---------")
                print("\tNo ues connected, sleeping {}s".format(NO_UE_SLEEP_INTERVAL_S))
                print("")
                continue

            for idx, ue in enumerate(ue_info_list):
                print(ue)
                try:

                    rsrp = ue.avg_rsrp
                    print("RSRP: " + str(rsrp))
                    rnti = ue.rnti
                    mcs = ue.mcs
                    dl_buffer = ue.dl_mac_buffer_occupation

                    p = Point("xapp-stats").tag("rnti", rnti).field("mcs", mcs).field("dl_mac_buffer_occupancy", dl_buffer)
                    print(p)
                    logging.info('Write to influxdb: ' + repr(p))
                    write_api.write(bucket=bucket, record=p)

                except:
                    print("Skip log, influxdb error")


if __name__ == '__main__':
    main()

