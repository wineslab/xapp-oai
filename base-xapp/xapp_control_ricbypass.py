from ast import Global
import socket
import socketserver
import string

localIP = "127.0.0.1"
in_port = 6600
out_port = 6655
maxSize = 4096
initialized = False
UDPClientSocketOut = None
UDPClientSocketIn = None

def initialize():
    global UDPClientSocketOut
    global UDPClientSocketIn
    global initialized
    UDPClientSocketOut = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketIn = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocketIn.bind(("", in_port))
    print("Control sockets initialized")
    initialized = True

def receive_from_socket():
    global initialized
    global UDPClientSocketIn
    print("receiving")
    if not initialized:
        initialize()
    bytesAddressPair = UDPClientSocketIn.recvfrom(maxSize)
    print("received {} bytes".format(len(bytesAddressPair[0])))
    return bytesAddressPair[0]

def sent_to_socket(data):
    global UDPClientSocketOut
    global initialized
    if not initialized:
        initialize()
    global UDPClientSocketOut
    UDPClientSocketOut.sendto(data, (localIP,out_port))
    

