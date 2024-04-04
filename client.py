# Jason B. Shew - 251285678 - CS4459B - Assignment 2
# Please check your protobuf and grpcio-tools version (the latter not higher than 1.43.0)
# pip install grpcio-tools==1.43.0
# pip install protobuf==3.20.3
# Also remember to install types-protobuf
# pip install types-protobuf
import os
import sys
import grpc
import replication_pb2 as replication
import replication_pb2_grpc

TARGET_SERVER_ADDRESS = 'localhost'
TARGET_SERVER_PORT = 50051

CLIENT_LOG_FILE = 'client.txt'

ACK = "REQUEST COMPLETED"
QUIT_SYMBOL = "//"
CANCEL_SYMBOL = ".."

primary_address = TARGET_SERVER_ADDRESS


def discover_primary():
    global primary_address
    # Code to discover the primary's address
    # This could be a direct query to a known service discovery mechanism or a stored value updated on notifications


def send_request_to_primary(data):
    if not primary_address:
        discover_primary()
    # Code to send a request to the primary server using primary_address


def run():
    channel = grpc.insecure_channel('{}:{}'.format(TARGET_SERVER_ADDRESS, TARGET_SERVER_PORT))
    stub = replication_pb2_grpc.SequenceStub(channel)
    try:
        while True:
            key_to_write = input('Enter <key> or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not key_to_write or key_to_write.isspace():
                print('<key> cannot be empty. Try again.')
                continue
            if ' ' in key_to_write:
                print('<key> cannot contain any spaces. Try again.')
                continue
            if key_to_write == QUIT_SYMBOL:
                print("\nGOODBYE!")
                sys.exit(0)
            if not key_to_write.isalnum():
                print('<key> should only contain letters and/or numbers. Try again.')
                continue
            break
        while True:
            value_to_write = input(
                'Enter <value>, "' + CANCEL_SYMBOL + '" to cancel, or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not value_to_write or value_to_write.isspace():
                print('<value> cannot be empty. Try again.')
                continue
            if value_to_write == CANCEL_SYMBOL:
                os.execl(sys.executable, sys.executable, *sys.argv)
            if value_to_write == QUIT_SYMBOL:
                print("\nGOODBYE!")
                sys.exit(0)
            break
        data_kv_pair = {key_to_write: value_to_write}
    except KeyboardInterrupt:
        print("\nGOODBYE!")
        sys.exit(0)
    try:
        for k, v in data_kv_pair.items():
            server_response = stub.Write(
                replication.WriteRequest(
                    key=k,
                    value=v
                ))
            if server_response.ack == ACK:
                with open(CLIENT_LOG_FILE, 'a') as file:
                    file.write(k + ' ' + v + '\n')
                    print("\nServer has successfully processed your request\n")
    except grpc.RpcError:
        print("\nWARNING:\n"
              "SERVICE IS NOT AVAILABLE\n"
              "PLEASE QUIT OR TRY AGAIN LATER\n")
    channel.close()


if __name__ == '__main__':
    while True:
        run()
