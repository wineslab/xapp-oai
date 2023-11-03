import socket

in_port = 6600
out_port = 6655
maxSize = 4096
initialized_rx = False
initialized_tx = False
UDPClientSocketOut = None
UDPClientSocketIn = None

def initialize_rx():
    global UDPClientSocketIn
    global initialized_rx
    UDPClientSocketIn = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketIn.bind(("", in_port))
    print("Input control socket initialized")
    initialized_rx = True

def initialize_tx():
    global UDPClientSocketOut
    global initialized_tx
    UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    print("Output control socket initialized")
    initialized_tx = True

def receive_from_socket(timeout=1):
    global initialized
    global UDPClientSocketIn
    print("receiving")
    if not initialized_rx:
        initialize_rx()
    UDPClientSocketIn.settimeout(timeout)
    try:
        bytesAddressPair = UDPClientSocketIn.recvfrom(maxSize)
        print("received {} bytes".format(len(bytesAddressPair[0])))
        return bytesAddressPair[0]
    except socket.timeout:
        print("Timeout waiting for data from socket")
        return None


def send_to_socket(data, ip):
    global UDPClientSocketOut
    global initialized
    if not initialized_tx:
        initialize_tx()
    global UDPClientSocketOut
    UDPClientSocketOut.sendto(data, (ip, out_port))
    

