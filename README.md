# xapp-oai
This repo contains simple monitoring and control xApps based on custom E2SM definitions. Definitions are plugged in as the 'oai-oran-protolib' submodule.

## Docker container deployment

This is the recommended deployment option, as it does not require setting requirements. First, [install docker](https://docs.docker.com/get-docker/). You'll also need `git`. 

### Instructions

Clone this repo and enter the repo's folder:

```
git clone https://github.com/ANTLab-polimi/xapp-oai.git
cd xapp-oai
```

Then build the image:

```
docker build -f Dockerfile -t xapp:mrn_base .
```

If the build is successfull, you will see the built image with `docker images`

Now start the container:
```
docker run -dit --name xapp --net=host xapp:mrn_base
```
The xApps not start automatically. First connect a terminal to the running container:

```
docker exec -it xapp bash
```

and then in this terminal you can run the monitoring xApp: 
```
python3 base-xapp/monitoring_xapp.py
```

If you also want to run the control xapp, open another terminal connected to the container and run:
```
python3 base-xapp/control_xapp.py
```

## Baremetal 
This depends on your system, but you basically need Python, protobuf and its python module. Ubuntu instructions can be extracted from the Dockerfile.
