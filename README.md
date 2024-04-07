# How to run this program

Place all files in the same directory.

In the terminal, enter:
`python3 ./raft_server.py <server_config_file.json> <server_directory.json>`

Replace `<server_config.json>` and `<server_directory.json>` with the correct file names.

Since we're simulating multiple servers on the same machine, server configration files are named as such:

`server_10001_config.json`
`server_10002_config.json`
`server_10003_config.json`
...
to differentiate between "servers" we have on one machine.

In reality, each machine only runs one instance of service, so server configurations will be stored
in `server_config.json`.

Environment:

```
install:
    python -m pip install grpcio-tools==1.43.0
    python -m pip install protobuf==3.20.3
    python -m pip install types-protobuf

compile:
	python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. raft.proto
```