install:
    python -m pip install grpcio-tools==1.43.0
    python -m pip install protobuf==3.20.3
    python -m pip install types-protobuf
compile:
	python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. replication.proto heartbeat_service.proto raft.proto