# Jason B. Shew - 251285678 - CS4459B - Assignment 2
# Please check your protobuf and grpcio-tools version (the latter not higher than 1.43.0)
# pip install grpcio-tools==1.43.0
# pip install protobuf==3.20.3
# Also remember to install types-protobuf
# pip install types-protobuf

import grpc
import time
from concurrent import futures
import threading
import replication_pb2 as replication
import replication_pb2_grpc
import heartbeat_service_pb2 as heartbeat_service
import heartbeat_service_pb2_grpc

SERVER_SERIAL_NUMBER = 0
SERVER_ADDRESS = 'localhost'
SERVER_PORT = 50052

HEARTBEAT_SERVER_ADDRESS = 'localhost'
HEARTBEAT_SERVER_PORT = 50053

BACKUP_LOG_FILE = 'backup.txt'

REQUESTS_FROM_CLIENTS = {}
ACK = "REQUEST COMPLETED"
TIMEOUT = 5


class Sequence(replication_pb2_grpc.SequenceServicer):
    def __init__(self):
        self.locks = {}
        self.global_lock = threading.Lock()

    def Write(self, request, context):
        key_to_write = request.key
        value_to_write = request.value
        line_to_write = key_to_write + ' ' + value_to_write + '\n'
        REQUESTS_FROM_CLIENTS.update({key_to_write: line_to_write})
        with open(BACKUP_LOG_FILE, "a") as file:
            file.write(line_to_write)
            return replication.WriteResponse(ack=ACK)


def send_heartbeat():
    with grpc.insecure_channel('{}:{}'.format(HEARTBEAT_SERVER_ADDRESS, HEARTBEAT_SERVER_PORT)) as channel:
        stub = heartbeat_service_pb2_grpc.ViewServiceStub(channel)
        while True:
            try:
                stub.Heartbeat(heartbeat_service.HeartbeatRequest(service_identifier="backup"))
                print("Heartbeat sent from backup server")
            except grpc.RpcError:
                print("WARNING:\n"
                      "MAKE SURE HEARTBEAT SERVER IS UP AND RUNNING\n")
            finally:
                time.sleep(TIMEOUT)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=500))
    replication_pb2_grpc.add_SequenceServicer_to_server(Sequence(), server)
    server.add_insecure_port('[::]:' + str(SERVER_PORT))
    server.start()
    print("Backup server is up on {}:{}\n".format(SERVER_ADDRESS, SERVER_PORT))
    try:
        while True:
            send_heartbeat()
            time.sleep(TIMEOUT)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
