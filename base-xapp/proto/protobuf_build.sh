#!/bin/bash
protoc -I=$(pwd) --python_out=$(pwd) $(pwd)/*.proto