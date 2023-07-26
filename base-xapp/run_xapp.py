import logging
from xapp_control import *
import xapp_control_ricbypass
from  ran_messages_pb2 import *
from time import sleep
BYPASS_RIC = True

def main():
    # configure logger and console output
    logging.basicConfig(level=logging.DEBUG, filename='/home/xapp-logger.log', filemode='a+',
                        format='%(asctime)-15s %(levelname)-8s %(message)s')
    formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    if BYPASS_RIC: # connect directly to gnb_emu
        #xapp_control_ricbypass.receive_from_socket()
        print("Encoding initial ric indication request")
        master_mess = RAN_message()
        master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
        inner_mess = RAN_indication_request()
        inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
        #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
        master_mess.ran_indication_request.CopyFrom(inner_mess)
        buf = master_mess.SerializeToString()
        xapp_control_ricbypass.send_to_socket(buf)
        print("request sent, now waiting for incoming answers")

        while True:
            r_buf = xapp_control_ricbypass.receive_from_socket()
            ran_ind_resp = RAN_indication_response()
            ran_ind_resp.ParseFromString(r_buf)
            print(ran_ind_resp)
            sleep(1)
            xapp_control_ricbypass.send_to_socket(buf)

        r_buf = xapp_control_ricbypass.receive_from_socket()
        ran_ind_resp = RAN_indication_response()
        ran_ind_resp.ParseFromString(r_buf)
        print(ran_ind_resp)

        exit()

    control_sck = open_control_socket(4200)

    while True:
        logging.info("loop again")
        data_sck = receive_from_socket(control_sck)
        if len(data_sck) <= 0:
            logging.info("leq 0 data")
            if len(data_sck) == 0:
                continue
            else:
                logging.info('Negative value for socket')
                break
        else:
            logging.info('Received data: ' + repr(data_sck))
            logging.info("Sending something back")
            send_socket(control_sck, "test test test")


if __name__ == '__main__':
    main()
