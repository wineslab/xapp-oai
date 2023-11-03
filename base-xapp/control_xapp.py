import xapp_control_ricbypass
from e2sm_proto import *
from time import sleep
import concurrent.futures



def get_data_from_gNB(ip):
    action = 'pippo imcumbent'

    print("Sending control message")
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.CONTROL
    inner_mess = RAN_control_request()
    
    # control bandwidth elemnet map entry
    control_element = RAN_param_map_entry()
    control_element.key = RAN_parameter.INCUMBENT_ACTION
    control_element.string_value = action

    # finalize and send
    inner_mess.target_param_map.extend([control_element])
    master_mess.ran_control_request.CopyFrom(inner_mess)
    print(master_mess)
    buf = master_mess.SerializeToString()
    xapp_control_ricbypass.send_to_socket(buf, ip)

def main():
    gNB_ips = ['127.0.0.1']
    print("Encoding ric monitoring request")    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(gNB_ips)) as executor:    
        futures = {executor.submit(get_data_from_gNB, ip): ip for ip in gNB_ips}

if __name__ == '__main__':
    main()

