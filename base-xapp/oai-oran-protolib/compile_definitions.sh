#!/bin/bash
echo "Compiling for python and c..."
protoc -I=. --python_out=./builds/ ./ran_messages.proto
protoc-c --c_out=./builds/ ./ran_messages.proto
echo "Done"