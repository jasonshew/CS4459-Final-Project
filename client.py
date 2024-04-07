# Jason B. Shew - 251285678 - CS4459B - Final Project
# Please check your protobuf and grpcio-tools version (the latter not higher than 1.43.0)
# pip install grpcio-tools==1.43.0
# pip install protobuf==3.20.3
# Also remember to install types-protobuf
# pip install types-protobuf
import json
import os
import sys

import grpc

import raft_pb2
import raft_pb2_grpc

SERVER_ID = None
SERVER_ADDRESS = None
SERVER_PORT = None
SERVER_DIRECTORY = {}
SERVER_DIRECTORY_FILE = 'server_directory.json'
CLIENT_LOG_FILE = 'client.txt'

QUIT_SYMBOL = "//"
CANCEL_SYMBOL = ".."


# Code to discover the primary's address
# This could be a direct query to a known service discovery mechanism or a stored value updated on notifications

def discover_server():
    global SERVER_ID, SERVER_ADDRESS, SERVER_PORT, SERVER_DIRECTORY_FILE
    if len(sys.argv) == 3:
        SERVER_DIRECTORY_FILE = sys.argv[2]
    dirname = os.path.dirname(__file__)
    if '/' not in SERVER_DIRECTORY_FILE:
        SERVER_DIRECTORY_FILE = os.path.join(dirname, SERVER_DIRECTORY_FILE)
    try:
        with open(SERVER_DIRECTORY_FILE, 'r') as file:
            servers_list = json.load(file)
            for each_server in servers_list:
                SERVER_DIRECTORY.update(
                    {each_server["server_id"]: each_server["address"] + ":" + str(each_server["port"])})
    except FileNotFoundError:
        print("Server directory not found. Check your local filesystem and try again.")
        sys.exit(0)
    except Exception:
        print("Server directory is not valid. Check your local filesystem and try again.")
        sys.exit(0)

    this_server_is_leader = False
    for key, val in SERVER_DIRECTORY.items():
        try:
            channel = grpc.insecure_channel(f'{val}')
            stub = raft_pb2_grpc.RaftStub(channel)
            server_response = stub.GetLeader(raft_pb2.EmptyMessage())
            SERVER_ID = int(server_response.leaderID)
            SERVER_ADDRESS = server_response.leaderAddress
            SERVER_PORT = int(SERVER_ADDRESS.split(":")[1])

            if int(key) == SERVER_ID:
                this_server_is_leader = True
                print("Connected to service successfully.")
                return stub
        except Exception:
            continue

    if SERVER_ID is None or SERVER_ID == -1:
        return None

    elif not this_server_is_leader:
        channel = grpc.insecure_channel(f'{SERVER_ADDRESS}:{SERVER_PORT}')
        stub = raft_pb2_grpc.RaftStub(channel)
        if stub is not None:
            print("Connected to service successfully.")
        return stub


def print_failure_msg():
    print("\nWARNING:\n"
          "SERVICE IS NOT AVAILABLE\n"
          "PLEASE QUIT OR TRY AGAIN LATER\n")


def run():
    global SERVER_ADDRESS, SERVER_PORT
    stub = discover_server()
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

    if stub is not None:
        try:
            for k, v in data_kv_pair.items():
                server_response = stub.SetKeyVal(
                    raft_pb2.SetKeyValMessage(
                        key=k,
                        value=v
                    ))
                if server_response.success:
                    with open(CLIENT_LOG_FILE, 'a') as file:
                        file.write(k + ' ' + v + '\n')
                        print("\nServer has successfully processed your request\n")
        except grpc.RpcError as e:
            print_failure_msg()
            print(e)
    else:
        print_failure_msg()


if __name__ == '__main__':
    while True:
        run()
