import logging
from os import lseek
from xapp_control import *
import xapp_control_ricbypass
from  ran_messages_pb2 import *
from time import sleep
import socket
from random import randint

BYPASS_RIC = False

def main():
    if BYPASS_RIC: # connect directly to gnb_emu
        #xapp_control_ricbypass.receive_from_socket()
        print("encoding initial ric indication request")
        master_mess = RAN_message()
        master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
        inner_mess = RAN_indication_request()
        inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
        #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
        master_mess.ran_indication_request.CopyFrom(inner_mess)
        buf = master_mess.SerializeToString()
        xapp_control_ricbypass.sent_to_socket(buf)
        print("request sent, now waiting for incoming answers")

        while True:
            r_buf = xapp_control_ricbypass.receive_from_socket()
            ran_ind_resp = RAN_indication_response()
            ran_ind_resp.ParseFromString(r_buf)
            print(ran_ind_resp)

        r_buf = xapp_control_ricbypass.receive_from_socket()
        ran_ind_resp = RAN_indication_response()
        ran_ind_resp.ParseFromString(r_buf)
        print(ran_ind_resp)

        exit()
    waittime = 1
    print("Will wait {} seconds for xapp-sm to start".format(waittime))
    sleep(waittime)
    print("encoding sub request")
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    print(buf)

    UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketOut.sendto(buf, ("127.0.0.1",7001))

    print("request sent, now waiting for incoming answers")

    control_sck = open_control_socket(4200)


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
            control_buf = gbr_control_interactive()
            send_socket(control_sck, control_buf)
            print("Control message sent")
            continue
            print("Sending RIC indication control with random data")
            master_mess = RAN_message()
            master_mess.msg_type = RAN_message_type.CONTROL
            inner_mess = RAN_control_request()

            # gnb id control element 
            gnb_id_control_element = RAN_param_map_entry()
            gnb_id_control_element.key = RAN_parameter.GNB_ID
            gnb_id_control_element.value = str(randint(1,10))

            # something control element
            something_control_element = RAN_param_map_entry()
            something_control_element.key = RAN_parameter.SOMETHING
            something_control_element.value = str(randint(1,10))

            inner_mess.target_param_map.extend([gnb_id_control_element, something_control_element])
            master_mess.ran_control_request.CopyFrom(inner_mess)

            print("printing built control message:")
            print(master_mess)

            ctrl_buf = master_mess.SerializeToString()
            send_socket(control_sck, ctrl_buf)
            print("Message sent")

            #logging.info("Sending something back")
            #send_socket(control_sck, "test test test")

def gbr_control_interactive():
    rnti = input("Enter RNTI:")
    rnti = int(rnti)

    is_GBR = input("Is GBR? (y/n)")
    if is_GBR == "y":
        is_GBR = True
    else:
        is_GBR = False

    dl_gbr = input("Enter DL GBR in Mbps:")
    tbs_dl_toapply = float(dl_gbr) / 8 * 1e3

    ul_gbr = input("Enter UL BGR in Mbps:")
    tbs_ul_toapply = float(ul_gbr) / 8 * 1e3

    print("Sending control message")
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.CONTROL
    inner_mess = RAN_control_request()
    
    # ue list map entry
    ue_list_control_element = RAN_param_map_entry()
    ue_list_control_element.key = RAN_parameter.UE_LIST
    
    # ue list message 
    ue_list_message = ue_list_m()
    ue_list_message.connected_ues = 1

    # ue info message
    ue_info_message = ue_info_m()
    ue_info_message.rnti = rnti
    ue_info_message.is_GBR = is_GBR
    ue_info_message.tbs_dl_toapply = tbs_dl_toapply
    ue_info_message.tbs_ul_toapply = tbs_ul_toapply

    # put info message into repeated field of ue list message
    ue_list_message.ue_info.extend([ue_info_message])

    # put ue_list_message into the value of the control map entry
    ue_list_control_element.ue_list.CopyFrom(ue_list_message)

    # finalize
    inner_mess.target_param_map.extend([ue_list_control_element])
    master_mess.ran_control_request.CopyFrom(inner_mess)
    print(master_mess)
    return master_mess.SerializeToString()
            
if __name__ == '__main__':
    main()

