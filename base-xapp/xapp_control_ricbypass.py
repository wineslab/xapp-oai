import socket
import socketserver

localIP = "127.0.0.1"
serverPort = 6655
maxSize = 4096
initialized = False
UDPClientSocket = None

def initialize():
    global UDPClientSocket
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    #UDPClientSocket.bind((localIP, serverPort))
    print("Control socket initialized")

def receive_from_socket():
    if not initialized:
        initialize()
    global UDPClientSocket
    bytesAddressPair = UDPClientSocket.recvfrom(maxSize)

def sent_to_socket(data):
    if not initialized:
        initialize()
    global UDPClientSocket
    UDPClientSocket.sendto(data, (localIP,serverPort))
    

