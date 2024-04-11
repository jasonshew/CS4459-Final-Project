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

LEADER_ID = None
LEADER_ADDRESS = None
LEADER_PORT = None
SERVER_DIRECTORY = {}
SERVER_DIRECTORY_FILE = 'server_directory.json'
CLIENT_LOG_FILE = 'client.txt'
SET = "WRITE"
GET = "READ"
USER_REQUEST = None
QUIT_SYMBOL = "//"
CANCEL_SYMBOL = ".."
LEADERS_LIST = []
GET_VAL_RESPONSE = None
SET_KEY_VAL_RESPONSE = None
GET_LEADER_RESPONSE = None
LEADER_STUB = None
ANY_STUB = None


def fetch_server_directory():
    global SERVER_DIRECTORY_FILE, SERVER_DIRECTORY
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


def connect_to_any_server(notify=True):
    global LEADER_ID, LEADER_ADDRESS, LEADER_PORT, ANY_STUB, SERVER_DIRECTORY
    retry = len(SERVER_DIRECTORY.keys())
    response = None
    while retry > 0 and ANY_STUB is None:
        for key, val in SERVER_DIRECTORY.items():
            try:
                channel = grpc.insecure_channel(f'{val}')
                ANY_STUB = raft_pb2_grpc.RaftStub(channel)
                response = ANY_STUB.GetLeader(raft_pb2.EmptyMessage())
                if response and notify:
                    if response.leaderID == key:
                        print(f"🟢 Leader server (#{response.leaderID}) is ready to serve you.")
                        return
                    else:
                        print(f"🟢 Follower server (#{key}) is up for your search requests.")
                        connect_to_leader()
                        return
                elif response:
                    return
                else:
                    continue
            except Exception:
                retry -= 1
                continue
            except KeyboardInterrupt:
                print("\nGOODBYE!\n")
                sys.exit(0)
        retry -= 1
        if response is None:
            print_failure_msg()
            print("NO SERVER IS AVAILABLE AT THE MOMENT\n")
            sys.exit(0)


def print_failure_msg():
    print_bold("\n⚠️ SORRY\n"
               "PART OF OUR SERVICE IS CURRENTLY UNAVAILABLE\n"
               "PLEASE QUIT OR TRY AGAIN\n")


def connect_to_leader():
    global LEADER_ID, LEADER_PORT, LEADER_ADDRESS, GET_LEADER_RESPONSE, LEADER_STUB, ANY_STUB
    if ANY_STUB is not None:
        GET_LEADER_RESPONSE = ANY_STUB.GetLeader(raft_pb2.EmptyMessage())
    if GET_LEADER_RESPONSE and GET_LEADER_RESPONSE.leaderID != -1:
        LEADER_ID = GET_LEADER_RESPONSE.leaderID
        LEADER_ADDRESS = GET_LEADER_RESPONSE.leaderAddress.split(":")[0]
        LEADER_PORT = int(GET_LEADER_RESPONSE.leaderAddress.split(":")[1])
        channel = grpc.insecure_channel(f'{GET_LEADER_RESPONSE.leaderAddress}')
        LEADER_STUB = raft_pb2_grpc.RaftStub(channel)
    else:
        return

    if not LEADERS_LIST:
        LEADERS_LIST.append(LEADER_ID)
    elif LEADER_ID != LEADERS_LIST[-1]:
        LEADERS_LIST.append(LEADER_ID)
    print(f"🟢 Leader server (#{LEADER_ID}) is ready to serve you.")


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
    try:
        while True:
            print()
            print("🔶 [R] Register a Product")
            print("🔶 [S] Search for a Product")
            print("🔶 [Q] Quit")
            print()
            user_choice = input("🔷 Select an operation: ")
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


def run():
    global USER_REQUEST, SET_KEY_VAL_RESPONSE, GET_VAL_RESPONSE, LEADER_STUB, ANY_STUB
    user_command = process_user_command()
    if user_command[0] == SET:
        USER_REQUEST = (user_command[1], user_command[2])
        try:
            connect_to_any_server(notify=False)
            SET_KEY_VAL_RESPONSE = ANY_STUB.SetKeyVal(
                raft_pb2.SetKeyValMessage(
                    key=USER_REQUEST[0],
                    value=USER_REQUEST[1]
                ))

            with open(CLIENT_LOG_FILE, 'a') as file:
                file.write(USER_REQUEST[0] + ' ' + USER_REQUEST[1] + '\n')

            if SET_KEY_VAL_RESPONSE is None:
                connect_to_leader()
                SET_KEY_VAL_RESPONSE = LEADER_STUB.SetKeyVal(raft_pb2.SetKeyValMessage(
                    key=USER_REQUEST[0],
                    value=USER_REQUEST[1]
                ))

            if SET_KEY_VAL_RESPONSE.success:
                print("\n✅ Your request was processed.\n\nThe following product has been successfully registered:")
                print_bold(f'\nProduct Code: {USER_REQUEST[0]}\nProduct Name: {USER_REQUEST[1]}\n')
            else:
                print_failure_msg()
        except grpc.RpcError or Exception as e:

            connect_to_any_server(notify=True)
            SET_KEY_VAL_RESPONSE = LEADER_STUB.SetKeyVal(raft_pb2.SetKeyValMessage(
                key=USER_REQUEST[0],
                value=USER_REQUEST[1]
            ))
            pass
        except KeyboardInterrupt:
            print("\nGOODBYE!\n")
            sys.exit(0)

    elif user_command[0] == GET:
        USER_REQUEST = user_command[1]
        try:
            connect_to_any_server(notify=False)
            GET_VAL_RESPONSE = ANY_STUB.GetVal(
                raft_pb2.GetValMessage(
                    key=USER_REQUEST,
                ))
            if GET_VAL_RESPONSE:
                if GET_VAL_RESPONSE.success and GET_VAL_RESPONSE.value:
                    print(
                        f"\n✅ Here is the product you're looking for: \n")
                    print_bold(f"\n{GET_VAL_RESPONSE.value} (Product Code: {USER_REQUEST})\n")
                elif GET_VAL_RESPONSE.success:
                    print(f"\n🥹 Sorry, no product with the code {USER_REQUEST} has been found.\n")

            else:
                connect_to_any_server(notify=True)
                pass
        except grpc.RpcError or Exception as e:
            connect_to_any_server(notify=True)
            pass
        except KeyboardInterrupt:
            sys.exit(0)


    else:
        print(f"🔴 Client request {user_command[0]} is invalid.")
        sys.exit(0)


def print_bold(text):
    print(f"\033[1m{text}\033[0m")


if __name__ == '__main__':

    print_bold("\n\n🍀 THANKS FOR USING DIM (DISTRIBUTED INVENTORY MANAGEMENT) SERVICE\n\n")
    while True:
        fetch_server_directory()
        connect_to_any_server()
        run()
