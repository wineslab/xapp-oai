from ast import Global
import socket
import socketserver
import string

localIP = "127.0.0.1"
in_port = 6600
out_port = 6655
maxSize = 4096
initialized_rx = False
initialized_tx = False
UDPClientSocketOut = None
UDPClientSocketIn = None

verbose = False

def initialize_rx():
    global UDPClientSocketIn
    global initialized_rx
    UDPClientSocketIn = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketIn.bind(("", in_port))
    if verbose:
        print("Input control socket initialized")
    initialized_rx = True

def initialize_tx():
    global UDPClientSocketOut
    global initialized_tx
    UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    if verbose:
        print("Output control socket initialized")
    initialized_tx = True

def receive_from_socket():
    global initialized
    global UDPClientSocketIn
    if verbose:
        print("receiving")
    if not initialized_rx:
        initialize_rx()
    bytesAddressPair = UDPClientSocketIn.recvfrom(maxSize)
    if verbose:
        print("received {} bytes".format(len(bytesAddressPair[0])))
    return bytesAddressPair[0]

def send_to_socket(data):
    global UDPClientSocketOut
    global initialized
    if not initialized_tx:
        initialize_tx()
    global UDPClientSocketOut
    UDPClientSocketOut.sendto(data, (localIP,out_port))
    

