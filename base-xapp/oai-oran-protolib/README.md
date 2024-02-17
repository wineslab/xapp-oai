# oai-oran-protolib
Custom protobuf definitions for oai ric support

## How to compile

### Install protobuf compiler
```
sudo apt install -y protobuf-compiler
```

### Install protobuf-c

Check the [README](https://github.com/protobuf-c/protobuf-c?tab=readme-ov-file#building)

### Install protoc development headers

According to the [discussion](https://github.com/protobuf-c/protobuf-c/issues/317#issuecomment-397445649)
```
sudo apt install -y libprotoc-dev
```

### Run `compile_definitions.sh`