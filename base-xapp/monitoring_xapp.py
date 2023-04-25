import logging
from xapp_control import *
import xapp_control_ricbypass
from ran_messages_pb2 import *


from time import sleep

def main():    

    print("Encoding initial ric indication request")
    master_mess = RAN_message()
    master_mess.msg_type = 1
    print(RAN_message_type.SUBSCRIPTION)
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    xapp_control_ricbypass.send_to_socket(buf)
    print("request sent, now waiting for incoming answers")


if __name__ == '__main__':
    main()

