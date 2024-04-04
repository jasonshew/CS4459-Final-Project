# Jason B. Shew - 251285678 - CS4459B - Assignment 2
# Please check your protobuf and grpcio-tools version (the latter not higher than 1.43.0)
# pip install grpcio-tools==1.43.0
# pip install protobuf==3.20.3
# Also remember to install types-protobuf
# pip install types-protobuf

import grpc
import time
from concurrent import futures
import replication_pb2 as replication
import replication_pb2_grpc
import heartbeat_service_pb2 as heartbeat_service
import heartbeat_service_pb2_grpc

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 50051

BACKUP_SERVER_GROUP = {0: ('localhost', 50052)}

HEARTBEAT_SERVER_ADDRESS = 'localhost'
HEARTBEAT_SERVER_PORT = 50053

PRIMARY_LOG_FILE = 'primary.txt'

ACK = "REQUEST COMPLETED"
TIMEOUT = 5


class Sequence(replication_pb2_grpc.SequenceServicer):

    def Write(self, request, context):
        key_to_write = request.key
        value_to_write = request.value
        line_to_write = key_to_write + ' ' + value_to_write + '\n'
        backup_count = 0
        for backup_server in BACKUP_SERVER_GROUP.values():
            with grpc.insecure_channel('{}:{}'.format(backup_server[0], backup_server[1])) as channel:
                stub = replication_pb2_grpc.SequenceStub(channel)
                response_from_backup_server = stub.Write(replication.WriteRequest(
                    key=key_to_write,
                    value=value_to_write
                ))
                if response_from_backup_server.ack == ACK:
                    backup_count += 1
        if backup_count == len(BACKUP_SERVER_GROUP):
            print('ALL BACKUP SERVERS ARE ALIVE: REQUEST BACKUP SUCCESSFUL\n')
            with open(PRIMARY_LOG_FILE, "a") as file:
                file.write(line_to_write)
                return replication.WriteResponse(
                    ack=ACK
                )
        else:
            print(str(backup_count) + ' OUT OF ' + str(len(BACKUP_SERVER_GROUP)) + ' BACKUP SERVERS WERE ALIVE')
            return replication.WriteResponse(
                ack=""
            )


def send_heartbeat():
    with grpc.insecure_channel('{}:{}'.format(HEARTBEAT_SERVER_ADDRESS, HEARTBEAT_SERVER_PORT)) as channel:
        stub = heartbeat_service_pb2_grpc.ViewServiceStub(channel)
        while True:
            try:
                stub.Heartbeat(heartbeat_service.HeartbeatRequest(service_identifier="primary"))
                print("Heartbeat sent from primary server")
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
    print("Primary server is up on {}:{}\n".format(SERVER_ADDRESS, SERVER_PORT))
    try:
        while True:
            send_heartbeat()
            time.sleep(TIMEOUT)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
