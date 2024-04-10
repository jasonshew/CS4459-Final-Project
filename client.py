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
STUB = None
SET = "WRITE"
GET = "READ"
USER_REQUEST = None
QUIT_SYMBOL = "//"
CANCEL_SYMBOL = ".."


def fetch_server_directory():
    global SERVER_ID, SERVER_ADDRESS, SERVER_PORT, SERVER_DIRECTORY_FILE, STUB
    if len(sys.argv) == 2:
        SERVER_DIRECTORY_FILE = sys.argv[1]
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


def connect_server(notify=True):
    global SERVER_ID, SERVER_ADDRESS, SERVER_PORT, STUB
    retry = len(SERVER_DIRECTORY.keys()) * 2
    server_response = None
    while retry > 0 and not server_response:
        for key, val in SERVER_DIRECTORY.items():
            try:
                channel = grpc.insecure_channel(f'{val}')
                STUB = raft_pb2_grpc.RaftStub(channel)
                server_response = STUB.GetLeader(raft_pb2.EmptyMessage())
                if server_response.leaderID != -1:
                    SERVER_ID = int(server_response.leaderID)
                    leader_ip_port = server_response.leaderAddress
                    SERVER_ADDRESS = leader_ip_port.split(":")[0]
                    SERVER_PORT = int(leader_ip_port.split(":")[1])
                    if notify:
                        print("🟢 Connected to service successfully\n")
                    break
            except Exception:
                retry -= 1
                continue
            except KeyboardInterrupt:
                print("\nGOODBYE!\n")
                sys.exit(0)
        retry -= 1

    if retry == 0 and (STUB is None or SERVER_ID == -1):
        print_failure_msg()
        sys.exit(0)


def print_failure_msg():
    print("\n🥹 SORRY\n"
          "SERVICE IS CURRENTLY UNAVAILABLE\n"
          "PLEASE QUIT OR TRY AGAIN LATER\n")


def get_input_product_code():
    while True:
        try:
            product_code = input('🔷 Enter PRODUCT CODE or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not product_code or product_code.isspace():
                print('🚫 Product code cannot be empty. Try again.')
                continue
            if ' ' in product_code:
                print('🚫 Product code cannot contain any spaces. Try again.')
                continue
            if product_code == QUIT_SYMBOL:
                print("\nGOODBYE!\n")
                sys.exit(0)
            if not product_code.isdigit():
                print('🚫 Product code should only contain numbers. Try again.')
                continue
            return product_code
        except Exception:
            return None
        except KeyboardInterrupt:
            print("\nGOODBYE!\n")
            sys.exit(0)


def get_input_product_name():
    while True:
        try:
            product_name = input(
                '🔷 Enter PRODUCT NAME, "' + CANCEL_SYMBOL + '" to cancel, or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not product_name or product_name.isspace():
                print('🚫 PRODUCT NAME cannot be empty. Try again.')
                continue
            if product_name == CANCEL_SYMBOL:
                os.execl(sys.executable, sys.executable, *sys.argv)
            if product_name == QUIT_SYMBOL:
                print("\nGOODBYE!\n")
                sys.exit(0)
            return product_name
        except Exception:
            return None
        except KeyboardInterrupt:
            print("\nGOODBYE!\n")
            sys.exit(0)


def process_user_command():
    global SERVER_ADDRESS, SERVER_PORT, STUB
    try:
        while True:
            print("🔶 [R] Register a Product")
            print("🔶 [S] Search for a Product")
            print("🔶 [Q] Quit")
            user_choice = input("\n🔷 Select an operation: ")
            user_choice = user_choice.strip().upper()

            if user_choice == "Q":
                print("\nGOODBYE!\n")
                sys.exit(0)
            elif user_choice == "R":
                product_code = get_input_product_code()
                if product_code:
                    product_name = get_input_product_name()
                    if product_name:
                        return SET, product_code, product_name
            elif user_choice == "S":
                product_code = get_input_product_code()
                return GET, product_code
            else:
                print("\n🚫 Invalid input. Please try again.\n")
                continue
    except KeyboardInterrupt:
        print("\nGOODBYE!\n")
        sys.exit(0)


def run(serverResponse):
    global USER_REQUEST
    server_response = serverResponse
    user_command = process_user_command()
    if user_command[0] == SET:
        USER_REQUEST = (user_command[1], user_command[2])
        try:
            server_response = STUB.SetKeyVal(
                raft_pb2.SetKeyValMessage(
                    key=USER_REQUEST[0],
                    value=USER_REQUEST[1]
                ))
        except Exception:
            pass
        except KeyboardInterrupt:
            print("\nGOODBYE!\n")
            sys.exit(0)

        with open(CLIENT_LOG_FILE, 'a') as file:
            file.write(USER_REQUEST[0] + ' ' + USER_REQUEST[1] + '\n')

        retry = len(SERVER_DIRECTORY.keys()) * 2
        if (server_response != None):
            while retry > 0 and not server_response.success:
                connect_server()
                server_response = STUB.SetKeyVal(
                    raft_pb2.SetKeyValMessage(
                        key=USER_REQUEST[0],
                        value=USER_REQUEST[1]
                    ))
                if not server_response or not server_response.success:
                    retry -= 1
            if server_response.success:
                print("\n✅ Your request was processed.\n\nThe following product has been successfully registered:")
                print_bold(f'\nProduct Code: {USER_REQUEST[0]}\nProduct Name: {USER_REQUEST[1]}\n')
                USER_REQUEST = None
            else:
                print_failure_msg()
                print("BBBBBBBBBB")
                sys.exit(0)

    elif user_command[0] == GET:
        USER_REQUEST = user_command[1]
        if STUB is not None:
            try:
                server_response = STUB.GetVal(
                    raft_pb2.GetValMessage(
                        key=USER_REQUEST,
                    ))
                if server_response.success and server_response.value:
                    print(
                        f"\n✅ Here is the product you're looking for: \n")
                    print_bold(f"\n{server_response.value} (Product Code: {USER_REQUEST})\n")
                elif server_response.success:
                    print(f"\n🥹 Sorry, no product with the code {USER_REQUEST} has been found.\n")
                else:
                    connect_server(notify=False)
            except grpc.RpcError as e:
                connect_server(notify=False)
            except KeyboardInterrupt:
                print("\nGOODBYE!\n")
                sys.exit(0)
        else:
            print_failure_msg()

    else:
        print(f"🔴 Client request {user_command[0]} is invalid.")
        sys.exit(0)

    return server_response


def print_bold(text):
    print(f"\033[1m{text}\033[0m")


if __name__ == '__main__':

    print_bold("\n\n🍀 THANKS FOR USING DIM (DISTRIBUTED INVENTORY MANAGEMENT) SERVICE\n\n")
    while True:
        fetch_server_directory()
        server_response = connect_server(notify=True)
        run(server_response)
