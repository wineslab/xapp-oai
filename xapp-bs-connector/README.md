# xApp-Base Station Connector

Provides a connecting layer between an xApp agent and the RIC, marshalling messages from/to base stations through the RIC via E2 interface.

Supports payloads as strings, or as Protobuf-serialized objects.
In the latter case, set the `using_protobuf` variable to `true` in the [`main` function of the HelloWorld xApp](src/hw_xapp_main.cc)

```cc
bool using_protobuf = true;
```
