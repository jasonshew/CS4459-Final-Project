# Jason B. Shew - 251285678 - CS4459B - Assignment 2
# Please check your protobuf and grpcio-tools version (the latter not higher than 1.43.0)
# pip install grpcio-tools==1.43.0
# pip install protobuf==3.20.3
# Also remember to install types-protobuf
# pip install types-protobuf

import grpc
import time
from concurrent import futures
from datetime import datetime, timedelta
import heartbeat_service_pb2 as heartbeat_service
import heartbeat_service_pb2_grpc

SERVER_ADDRESS = 'localhost'
SERVER_PORT = 50053

HEARTBEAT_LOG_FILE = 'heartbeat.txt'

CLIENTS_LAST_HEARTBEAT = {}
TIMEOUT = 5


class ViewService(heartbeat_service_pb2_grpc.ViewServiceServicer):

    def Heartbeat(self, request, context):
        now = datetime.now()
        server_type = str(request.service_identifier).capitalize()
        CLIENTS_LAST_HEARTBEAT.update({request.service_identifier: now})
        message = "{} is alive. Latest heartbeat received at {}".format(server_type, now)
        with open(HEARTBEAT_LOG_FILE, 'a') as file:
            print(message)
            file.write(message + '\n')
        return heartbeat_service.google_dot_protobuf_dot_empty__pb2.Empty()


def monitor():
    for service_identifier, last_heartbeat in CLIENTS_LAST_HEARTBEAT.items():
        now = datetime.now()
        server_type = str(service_identifier).capitalize()
        if (now - last_heartbeat) > timedelta(seconds=TIMEOUT):
            message = "{} might be down. Latest heartbeat received at {}".format(server_type,
                                                                                 CLIENTS_LAST_HEARTBEAT[
                                                                                     service_identifier])

            with open(HEARTBEAT_LOG_FILE, 'a') as file:
                print(message)
                file.write(message + '\n')


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=500))
    heartbeat_service_pb2_grpc.add_ViewServiceServicer_to_server(ViewService(), server)
    server.add_insecure_port('[::]:' + str(SERVER_PORT))
    server.start()
    print("Heartbeat server is up on {}:{}".format(SERVER_ADDRESS, SERVER_PORT))
    try:
        while True:
            monitor()
            time.sleep(TIMEOUT)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
