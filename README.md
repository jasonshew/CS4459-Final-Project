# DIM (Distributed Inventory Management)

## How to run this program

Place all files in the same directory.

### Server side:
In the terminal, enter:
`./dimserver <server_config_file.json> <server_directory.json>`

Replace `<server_config.json>` and `<server_directory.json>` with the correct file names.

Since we're simulating multiple servers on the same machine, server configration files are named as such:

`server_config_10001.json`
`server_config_10002.json`
`server_config_10003.json`
...
to differentiate between "servers" we have on one machine.

In reality, each machine only runs one instance of service, so server configurations will be stored
in `server_config.json`.

The default files to use are `server_config.json` and `server_directory.json`. But, again, since you need to run multiple instances, it's necessary to use a different server configuration file for each instance.


### Client side:
In the terminal, enter:
`./dimclient <server_directory_file>`

Replace `<server_directory.json>` with the correct file name. The default file to use is `server_directory.json`

### File structure:

As to the format of both files, please refer to the json files in the repo.

Server direcory file structure:
[
  {
    "server_id": 10000,
    "address": "localhost",
    "port": 10000
  },
  {
    "server_id": 10001,
    "address": "localhost",
    "port": 50001
  },
  {
    "server_id": 10002,
    "address": "localhost",
    "port": 50002
  },

]

Server configuration file structure:

{
    "server_id": 10000,
    "address": "localhost",
    "port": 50001,
    "peers": []
}

### Environment (The same environment for your Assignment 1 and 2):

```
install:
    python -m pip install grpcio-tools==1.43.0
    python -m pip install protobuf==3.20.3
    python -m pip install types-protobuf

compile:
	python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. raft.proto
```
