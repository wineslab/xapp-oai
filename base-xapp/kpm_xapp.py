import logging
from os import lseek
from xapp_control import *
import xapp_control_ricbypass
from  ran_messages_pb2 import *
from time import sleep, time
import socket
from random import randint

# Parameters
BYPASS_RIC = False		# Variable to bypass the RIC (True: yes, False: no)
NO_UE_SLEEP_INTERVAL_S = 1	# Time to sleep when UEs are not connected


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

            # Check if there's any ue connected
            if len(ue_info_list) == 0:
                print("\t---------")
                print("\tNo ues connected, sleeping {}s".format(NO_UE_SLEEP_INTERVAL_S))
                print("")
                sleep(NO_UE_SLEEP_INTERVAL_S)
                continue

            # Print the UE information
            for idx, ue in enumerate(ue_info_list):
                print(ue)


if __name__ == '__main__':
    main()

