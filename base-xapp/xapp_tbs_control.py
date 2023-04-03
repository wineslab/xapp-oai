import logging
from xapp_control import *
import xapp_control_ricbypass
from  ran_messages_pb2 import *
from time import sleep
from rich.console import Console
from rich.panel import Panel
import multiprocessing

BYPASS_RIC = True

def main():

    rnti = input("Enter RNTI:")
    rnti = int(rnti)

    is_GBR = input("Is GBR? (y/n)")
    if is_GBR == "y":
        is_GBR = True
    else:
        is_GBR = False

    tbs_dl_toapply = input("Enter DL TBS in bytes:")
    tbs_dl_toapply = float(tbs_dl_toapply)

    tbs_ul_toapply = input("Enter UL TBS in bytes:")
    tbs_ul_toapply = float(tbs_ul_toapply)

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
    buf = master_mess.SerializeToString()
    xapp_control_ricbypass.send_to_socket(buf)




if __name__ == '__main__':
    main()

