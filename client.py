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
SET = "SET"
GET = "GET"

QUIT_SYMBOL = "//"
CANCEL_SYMBOL = ".."


# Code to discover the primary's address
# This could be a direct query to a known service discovery mechanism or a stored value updated on notifications

def discover_server():
    global SERVER_ID, SERVER_ADDRESS, SERVER_PORT, SERVER_DIRECTORY_FILE, STUB
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
            STUB = raft_pb2_grpc.RaftStub(channel)
            server_response = STUB.GetLeader(raft_pb2.EmptyMessage())
            if (server_response):
                SERVER_ID = int(server_response.leaderID)
                leader_ip_port = server_response.leaderAddress
                SERVER_ADDRESS = leader_ip_port.split(":")[0]
                SERVER_PORT = int(leader_ip_port.split(":")[1])
                print("Connected to service successfully.")
                break
        except Exception:
            continue
        except KeyboardInterrupt:
            print("\nGOODBYE!")
            sys.exit(0)

    if SERVER_ID is None or SERVER_ID == -1:
        return None


def print_failure_msg():
    print("\nWARNING:\n"
          "SERVICE IS NOT AVAILABLE\n"
          "PLEASE QUIT OR TRY AGAIN LATER\n")


def get_input_product_code():
    while True:
        try:
            product_code = input('Enter PRODUCT CODE or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not product_code or product_code.isspace():
                print('Product code cannot be empty. Try again.')
                continue
            if ' ' in product_code:
                print('Product code cannot contain any spaces. Try again.')
                continue
            if product_code == QUIT_SYMBOL:
                print("\nGOODBYE!")
                sys.exit(0)
            if not product_code.isdigit():
                print('Product code should only contain numbers. Try again.')
                continue
            return product_code
        except Exception:
            return None
        except KeyboardInterrupt:
            print("\nGOODBYE!")
            sys.exit(0)


def get_input_product_name():
    while True:
        try:
            product_name = input(
                'Enter PRODUCT NAME, "' + CANCEL_SYMBOL + '" to cancel, or "' + QUIT_SYMBOL + '" to quit: ').strip()
            if not product_name or product_name.isspace():
                print('PRODUCT NAME cannot be empty. Try again.')
                continue
            if product_name == CANCEL_SYMBOL:
                os.execl(sys.executable, sys.executable, *sys.argv)
            if product_name == QUIT_SYMBOL:
                print("\nGOODBYE!")
                sys.exit(0)
            return product_name
        except Exception:
            return None
        except KeyboardInterrupt:
            print("\nGOODBYE!")
            sys.exit(0)


def process_user_command():
    global SERVER_ADDRESS, SERVER_PORT, STUB
    print("THANKS FOR USING DIM (DISTRIBUTED INVENTORY MANAGEMENT) SERVICE")
    try:
        while True:
            print("[R] Register a Product")
            print("[S] Search for a Product")
            print("[Q] Quit")
            user_choice = input("Select an operation: ")
            user_choice = user_choice.strip().upper()

            if user_choice == "Q":
                print("\nGOODBYE!")
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
                print("Invalid input. Please try again.\n")
                continue
    except KeyboardInterrupt:
        print("\nGOODBYE!")
        sys.exit(0)


def run():
    user_command = process_user_command()
    if user_command[0] == SET:
        data_kv_pair = {user_command[1]: user_command[2]}

        if STUB is not None:
            print("********", STUB is None)
            try:
                for k, v in data_kv_pair.items():
                    print("------")
                    server_response = STUB.SetKeyVal(
                        raft_pb2.SetKeyValMessage(
                            key=k,
                            value=v
                        ))
                    print("------")
                    print("-------------", server_response)

                    if server_response.success:
                        with open(CLIENT_LOG_FILE, 'a') as file:
                            file.write(k + ' ' + v + '\n')
                            print("\nServer has successfully processed your request\n")
                            print(f'Product Code: {k} | Product Name: {v} – Registered')
                    else:
                        print_failure_msg()
                        print("AAAAA")
            except grpc.RpcError as e:
                print_failure_msg()
                print("BBBBB")
                print(e)
            except Exception:
                print_failure_msg()
                print("CCCCC")
            except KeyboardInterrupt:
                print("\nGOODBYE!")
                sys.exit(0)
        else:
            print_failure_msg()
            print("DDDDD")
    elif user_command[0] == GET:
        data_key = user_command[1]
        if STUB is not None:
            try:
                server_response = STUB.GetVal(
                    raft_pb2.GetValMessage(
                        key=data_key,
                    ))
                if server_response.success and server_response.value:
                    print(f"\nThe product you are looking for is {server_response.value} (Product Code: {data_key})\n")
                else:
                    print(f"\nThe product you are looking for doesn't exist")
            except grpc.RpcError as e:
                print_failure_msg()
                print("EEEEEEE")
                print(e)
            except KeyboardInterrupt:
                print("\nGOODBYE!")
                sys.exit(0)
        else:
            print_failure_msg()
            print("FFFFFF")
    else:
        print_failure_msg()
        print("GGGGGGG")


if __name__ == '__main__':
    discover_server()
    while True:
        run()
