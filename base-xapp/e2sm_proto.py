from sys import path
from os import getcwd

cwd = getcwd()
path.append('{}/base-xapp/oai-oran-protolib/builds'.format(cwd))
tmp = __import__('ran_messages_pb2')
globals().update(vars(tmp))