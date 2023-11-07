import xapp_control_ricbypass
from e2sm_proto import *
from time import sleep
import concurrent.futures

def get_data_from_gNB(ip):
    # external message
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST

    # internal message
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST, RAN_parameter.IQ_MAPPING])

    # assign and serialize
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    xapp_control_ricbypass.send_to_socket(buf, ip)
    
    while True:
        r_buf = xapp_control_ricbypass.receive_from_socket()
        ran_ind_resp = RAN_indication_response()
        ran_ind_resp.ParseFromString(r_buf)
        print(ran_ind_resp)
        sleep(1)
        xapp_control_ricbypass.send_to_socket(buf, ip)


def main():    

    gNB_ips = ['127.0.0.1']
    print("Encoding ric monitoring request")    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(gNB_ips)) as executor:    
        futures = {executor.submit(get_data_from_gNB, ip): ip for ip in gNB_ips}
    



if __name__ == '__main__':
    main()

