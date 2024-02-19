import logging
from xapp_control import *
import xapp_control_ricbypass
# from  ran_messages_pb2 import *
import importlib
ran_messages_pb2 = importlib.import_module("oai-oran-protolib.builds.ran_messages_pb2")
from time import sleep

BYPASS_RIC = False

def trigger_indication():
    print("Encoding sub request")
    master_mess = ran_messages_pb2.RAN_message()
    master_mess.msg_type = ran_messages_pb2.RAN_message_type.INDICATION_REQUEST
    inner_mess = ran_messages_pb2.RAN_indication_request()
    inner_mess.target_params.extend([ran_messages_pb2.RAN_parameter.GNB_ID])
    #inner_mess.target_params.extend([RAN_parameter.GNB_ID])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    print(buf)
    return buf

def trigger_slicing_control(iter):
    print("Encoding initial RIC Control request")
    slicing_mess = ran_messages_pb2.slicing_control_m()
    slicing_mess.sst = 1
    slicing_mess.sd  = 1
    slicing_mess.min_ratio = 11
    slicing_mess.max_ratio = 11 + iter % 90

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
    # configure logger and console output
    logging.basicConfig(level=logging.DEBUG, filename='slicing-xapp-logger.log', filemode='a+',
                        format='%(asctime)-15s %(levelname)-8s %(message)s')
    formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    if BYPASS_RIC: # connect directly to gnb_emu

        buf = trigger_slicing_control()
        xapp_control_ricbypass.send_to_socket(buf)
        print("request sent, now waiting for incoming answers")

        return

        while True:
            r_buf = xapp_control_ricbypass.receive_from_socket()
            ran_ind_resp = ran_messages_pb2.RAN_indication_response()
            ran_ind_resp.ParseFromString(r_buf)
            print(ran_ind_resp)
            sleep(1)
            xapp_control_ricbypass.send_to_socket(buf)

    else:
        buf = trigger_indication()
        #buf = trigger_slicing_control()
        UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPClientSocketOut.sendto(buf, ("127.0.0.1",7001))
        print("request sent, now waiting for incoming answers")
        control_sck = open_control_socket(4200)
        
        iter = 0
        while True:
            logging.info("loop again")
            data_sck = receive_from_socket(control_sck)
            #data_sck = "dummy"
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
                control_buf = trigger_slicing_control(iter)
                iter = iter + 1
                send_socket(control_sck, control_buf)

if __name__ == '__main__':
    main()


