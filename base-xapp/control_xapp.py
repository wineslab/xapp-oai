import logging
from xapp_control import *
import xapp_control_ricbypass
from e2sm_proto import *
from time import sleep

def main():

    rnti = input("Enter RNTI:")
    rnti = int(rnti)

    prop_1 = input("Is prop_1 true? (y/n)")
    if prop_1 == "y":
        prop_1 = True
    else:
        prop_1 = False
    prop_2 = float(input("Enter prop_2 (float)"))

    print("Sending control message")
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.CONTROL
    inner_mess = RAN_control_request()
    
    # ue list map entry
    ue_list_control_element = RAN_param_map_entry()
    ue_list_control_element.key = RAN_parameter.UE_LIST
    
    # ue list message 
    ue_list_message = ue_list_m()
    ue_list_message.connected_ues = 1 # this will not be processed by the gnb, it can be anything

    # ue info message
    ue_info_message = ue_info_m()
    ue_info_message.rnti = rnti
    ue_info_message.prop_1 = prop_1
    ue_info_message.prop_2 = prop_2

    # put info message into repeated field of ue list message
    ue_list_message.ue_info.extend([ue_info_message])

    # put ue_list_message into the value of the control map entry
    ue_list_control_element.ue_list.CopyFrom(ue_list_message)

    # finalize and send
    inner_mess.target_param_map.extend([ue_list_control_element])
    master_mess.ran_control_request.CopyFrom(inner_mess)
    print(master_mess)
    buf = master_mess.SerializeToString()
    xapp_control_ricbypass.send_to_socket(buf)




if __name__ == '__main__':
    main()

