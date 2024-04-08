import json
import os
import random
import sys
from concurrent import futures
from enum import Enum
from threading import Timer

import grpc

import raft_pb2
import raft_pb2_grpc

SERVER_CONFIG_FILE = "server_config.json"  # This is the default config file. Should use a customized config file using command line
SERVER_DIRECTORY_FILE = "server_directory.json"
SERVER_DIRECTORY = {}
ELECTION_TIMEOUT = None
HEARTBEAT_INTERVAL = 0.05
SERVER_STATUS = None  # Server status: Follower, Candidate, Leader
TERM_NUMBER = 0  # Current term of the server
LEADER = None  # Current leader in the system
SERVER_ID = 0  # Own server ID, which is unique
SERVER_ADDRESS = None  # Own server address
SERVER_PORT = 0  # Own server port
VOTED = None  # ID of the server that this server voted for
TIMER_THREAD = None  # Thread for general timers: election, heartbeat
IS_ELECTION_FINISHED = True  # Determine if election is completed
SERVER_LOG = []  # server log -> [{index: 0, term: 0, command: ('set', 'key1', 'val1')}, ...]
SERVER_LOG_FILE = ""
COMMIT_INDEX = 0
LAST_APPLIED = 0
NEXT_INDEX = {}
MATCH_INDEX = {}


class ServerState(Enum):
    Follower = 1
    Candidate = 2
    Leader = 3


def config_server():
    global SERVER_ID, SERVER_LOG_FILE, TERM_NUMBER, SERVER_ADDRESS, SERVER_PORT, PEER_SERVERS, ELECTION_TIMEOUT, SERVER_CONFIG_FILE, SERVER_DIRECTORY_FILE
    if len(sys.argv) == 3:
        SERVER_CONFIG_FILE = sys.argv[1]
        SERVER_DIRECTORY_FILE = sys.argv[2]
    dirname = os.path.dirname(__file__)
    if '/' not in SERVER_CONFIG_FILE:
        SERVER_CONFIG_FILE = os.path.join(dirname, SERVER_CONFIG_FILE)
    if '/' not in SERVER_DIRECTORY_FILE:
        SERVER_DIRECTORY_FILE = os.path.join(dirname, SERVER_DIRECTORY_FILE)
    try:
        with open(SERVER_CONFIG_FILE, 'r') as file_1, open(SERVER_DIRECTORY_FILE, 'r') as file_2:
            server_info = json.load(file_1)
            servers_list = json.load(file_2)
            server_info["peers"].clear()
            for each_server in servers_list:
                SERVER_DIRECTORY.update(
                    {each_server["server_id"]: each_server["address"] + ":" + str(each_server["port"])})
                if each_server["server_id"] != server_info["server_id"]:
                    server_info["peers"].append(
                        {"server_id": each_server["server_id"], "address": each_server["address"],
                         "port": each_server["port"]})
                    with open(SERVER_CONFIG_FILE, 'w') as file_3:
                        json.dump(server_info, file_3, sort_keys=False, indent=4)
    except Exception:
        print("Server configuration file or server directory not found. Check your local filesystem and try again.")
        sys.exit(0)
    SERVER_ID = server_info["server_id"]
    SERVER_ADDRESS = server_info["address"]
    SERVER_PORT = server_info["port"]
    SERVER_LOG_FILE = f'server_{SERVER_ID}_log.json'


def register_this_server():
    the_server = {
        "server_id": SERVER_ID,
        "address": SERVER_ADDRESS,
        "port": SERVER_PORT
    }
    try:
        with open(SERVER_DIRECTORY_FILE, 'r') as file_1:
            servers_list = json.load(file_1)
            for server in servers_list:
                if server["server_id"] == SERVER_ID:
                    print("This server is already in the server directory.")
                    return
            servers_list.append(the_server)
            with open(SERVER_DIRECTORY_FILE, 'w') as file_2:
                json.dump(servers_list, file_2, sort_keys=False, indent=4)
                print("This server has been registered successfully.")
    except FileNotFoundError:
        print("Server directory not found. Registration failed.")
        sys.exit(0)
    except PermissionError:
        print("Permission denied. Registration failed.")
        sys.exit(0)
    except Exception:
        print("Registration failed.")
        sys.exit(0)


def verify_server_log():
    try:
        with open(SERVER_LOG_FILE, 'r') as file:
            logfile = json.load(file)
            print("Server logfile located: " + str(len(logfile["server_log"])) + " entries")
    except FileNotFoundError:
        with open(SERVER_LOG_FILE, 'w') as file:
            initialized_log = [{}]
            json.dump(initialized_log, file, sort_keys=False)
            print("Server logfile created successfully.")


def replicateLog(new_log):
    global SERVER_DIRECTORY, TERM_NUMBER, SERVER_ID, COMMIT_INDEX, SERVER_LOG, SERVER_STATUS, NEXT_INDEX, MATCH_INDEX, \
        TIMER_THREAD

    print('Log replication', new_log)

    replication_success_num = 0
    for key in list(SERVER_DIRECTORY.keys()):
        try:
            channel = grpc.insecure_channel(SERVER_DIRECTORY[key])
            stub = raft_pb2_grpc.RaftStub(channel)

            message = raft_pb2.AppendEntriesMessage()
            message.currentTerm = TERM_NUMBER
            message.leaderID = SERVER_ID
            message.lastLogIndex = MATCH_INDEX[key]
            message.lastLogTerm = 0 if len(SERVER_LOG) == 0 else SERVER_LOG[MATCH_INDEX[key]]['term']
            message.leaderCommitIndex = COMMIT_INDEX

            command_message = raft_pb2.CommandMessage(operation=new_log['command'][0], key=new_log['command'][1],
                                                      value=new_log['command'][2])
            log_entry = raft_pb2.LogEntry(index=new_log['index'], term=new_log['term'], command=command_message)

            message.logEntries.append(log_entry)

            response = stub.AppendEntries(message)

            print(response)

            if response.currentTerm > TERM_NUMBER:
                TIMER_THREAD.cancel()
                TERM_NUMBER = response.currentTerm
                SERVER_STATUS = ServerState.Follower

                print(f"This server #{SERVER_ID} is a Follower. (Term: {TERM_NUMBER})")

                TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
                TIMER_THREAD.start()
                break

            if response.success:
                replication_success_num += 1

                NEXT_INDEX[key] += 1
                MATCH_INDEX[key] = NEXT_INDEX[key] - 1

        except grpc.RpcError:
            continue
        except Exception as Error:
            print(Error)

    if replication_success_num > len(list(SERVER_DIRECTORY.keys())) / 2:
        COMMIT_INDEX += 1


class Raft(raft_pb2_grpc.RaftServicer):
    def __init__(self, *args, **kwargs):
        pass

    def SetKeyVal(self, request, context):
        global SERVER_LOG, COMMIT_INDEX, LAST_APPLIED, SERVER_STATUS, TERM_NUMBER, LEADER, SERVER_DIRECTORY
        try:
            if SERVER_STATUS.name == 'Candidate':
                return raft_pb2.SetKeyValResponse(success=False)

            if SERVER_STATUS.name == 'Leader':
                new_log_entry = {'index': len(SERVER_LOG), 'term': TERM_NUMBER,
                                 'command': ('set', request.key, request.value)}

                replicateLog(new_log_entry)

                SERVER_LOG.append(new_log_entry)
                LAST_APPLIED += 1

                print(SERVER_LOG)

                with open(SERVER_LOG_FILE, 'r') as file:
                    json_data = json.load(file)
                    json_data.append(new_log_entry)
                with open(SERVER_LOG_FILE, 'w') as file:
                    file.write(json.dumps(json_data, indent=4))

                return raft_pb2.SetKeyValResponse(success=True)
            else:  # Follower case
                leader_channel = grpc.insecure_channel(SERVER_DIRECTORY[int(LEADER)])
                leader_stub = raft_pb2_grpc.RaftStub(leader_channel)
                message = raft_pb2.SetKeyValMessage(key=request.key, value=request.value)
                return leader_stub.SetKeyVal(message)
        except Exception as Error:
            return raft_pb2.SetKeyValResponse(success=False)

    def GetVal(self, request, context):
        global SERVER_LOG

        print(SERVER_LOG)

        target_value = None
        for entry in SERVER_LOG:
            if request.key == entry['command'][1]:
                target_value = entry['command'][2]

        return raft_pb2.GetValResponse(success=True, value=target_value)

    def GetLeader(self, request, context):
        global LEADER, SERVER_DIRECTORY, SERVER_ID, SERVER_ADDRESS
        current_leader = LEADER

        if LEADER is None:
            current_leader = -1
            address = ''
        else:
            if LEADER == SERVER_ID:
                address = SERVER_ADDRESS
            else:
                address = SERVER_DIRECTORY[int(LEADER)]

        print(f'{current_leader} {address}')

        return raft_pb2.GetLeaderResponse(leaderID=current_leader, leaderAddress=address)

    def AppendEntries(self, request, context):
        global TIMER_THREAD, TERM_NUMBER, SERVER_STATUS, ELECTION_TIMEOUT, LEADER, VOTED, SERVER_LOG, COMMIT_INDEX

        # Reset timer only if this server is a Follower
        if SERVER_STATUS.name == 'Follower':
            TIMER_THREAD.cancel()

        heartbeat_success = False
        if request.currentTerm >= TERM_NUMBER:
            heartbeat_success = True
            LEADER = request.leaderID

            # Write SERVER_LOG
            if SERVER_LOG[request.lastLogIndex] is None and len(SERVER_LOG) > 0:
                heartbeat_success = False
            else:
                log_entry = request.logEntries[0]
                log_command = log_entry.command

                SERVER_LOG.append({'index': log_entry.index, 'term': log_entry.term,
                                   'command': (log_command.operation, log_command.key, log_command.value)})

                COMMIT_INDEX = min(request.leaderCommitIndex, SERVER_LOG[-1]['index'])

                print('Server log updated')
                print(SERVER_LOG)
                print(f'Leader commit index: {COMMIT_INDEX}')

            if request.currentTerm > TERM_NUMBER:  # Update own term
                VOTED = None
                TERM_NUMBER = request.currentTerm
                print(f"This server #{SERVER_ID} is a follower (Current Term: {TERM_NUMBER})")

                # Become follower due to higher Term
                if SERVER_STATUS.name == 'Candidate' or SERVER_STATUS.name == 'Leader':  # Become Follower if greater term is come
                    SERVER_STATUS = ServerState.Follower
                    print(f"This server #{SERVER_ID} has become a follower (Current Term: {TERM_NUMBER})")
                    TIMER_THREAD.cancel()  # Cancel Timer for Candidate and Leader

        # Create new timer for Follower
        if SERVER_STATUS.name == 'Follower':
            TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
            TIMER_THREAD.start()

        return raft_pb2.AppendEntriesResponse(followerID=SERVER_ID, currentTerm=TERM_NUMBER, success=heartbeat_success)

    def RequestVote(self, request, context):
        global VOTED, TERM_NUMBER, SERVER_STATUS, TIMER_THREAD, ELECTION_TIMEOUT, LEADER

        voting_success = False
        if SERVER_STATUS.name == 'Follower':
            TIMER_THREAD.cancel()

        if request.currentTerm >= TERM_NUMBER:
            if request.currentTerm > TERM_NUMBER:
                TERM_NUMBER = request.currentTerm
                VOTED = request.candidateID
                voting_success = True

                print(f'This server voted for Server #{request.candidateID}')

                # Become follower due to higher Term
                if SERVER_STATUS.name == 'Candidate' or SERVER_STATUS.name == 'Leader':
                    SERVER_STATUS = ServerState.Follower
                    print(f"This server #{SERVER_ID} has become a follower (Current Term: {TERM_NUMBER})")
                    TIMER_THREAD.cancel()

            if VOTED is None:
                VOTED = request.candidateID
                voting_success = True

                print(f'Voted for Server #{request.candidateID}')

        if SERVER_STATUS.name == 'Follower':
            TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
            TIMER_THREAD.start()

        return raft_pb2.RequestVoteResponse(currentTerm=TERM_NUMBER, voteGranted=voting_success)


def send_heartbeat():
    global SERVER_DIRECTORY, TERM_NUMBER, SERVER_ID, TIMER_THREAD, SERVER_STATUS, ELECTION_TIMEOUT, COMMIT_INDEX, SERVER_LOG

    for key in list(SERVER_DIRECTORY.keys()):
        try:
            channel = grpc.insecure_channel(SERVER_DIRECTORY[key])
            stub = raft_pb2_grpc.RaftStub(channel)

            message = raft_pb2.AppendEntriesMessage()
            message.leaderID = SERVER_ID
            message.currentTerm = TERM_NUMBER
            message.lastLogIndex = 0 if len(SERVER_LOG) == 0 else SERVER_LOG[-1]['index']
            message.lastLogTerm = 0 if len(SERVER_LOG) == 0 else SERVER_LOG[-1]['term']
            message.leaderCommitIndex = COMMIT_INDEX
            response = stub.AppendEntries(message)
            channel.close()

            if response.currentTerm > TERM_NUMBER:
                TIMER_THREAD.cancel()
                TERM_NUMBER = response.currentTerm
                SERVER_STATUS = ServerState.Follower

                print(f"This server #{SERVER_ID} has become a Follower (Current Term: {TERM_NUMBER})")

                TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
                TIMER_THREAD.start()
                break

        except grpc.RpcError:
            continue


class RaftTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def generate_random_timeout():
    return random.randrange(150, 300) / 1000


def start_election():
    global SERVER_STATUS, SERVER_DIRECTORY, TERM_NUMBER, SERVER_ID, TIMER_THREAD, VOTED, LEADER, ELECTION_TIMEOUT, IS_ELECTION_FINISHED

    if LEADER is None or int(LEADER) < 0:
        print("Leader Server not discovered yet")
    else:
        print(f'Leader Server #{LEADER} went down')

    IS_ELECTION_FINISHED = False

    TIMER_THREAD.cancel()  # Cancel previous timer
    TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, stop_election)

    SERVER_STATUS = ServerState.Candidate
    TERM_NUMBER += 1
    votes = 1
    VOTED = SERVER_ID
    print(f"This server #{SERVER_ID} voted for itself (Status: Candidate / Current Term: {TERM_NUMBER})")

    # Start collecting votes
    for key in list(SERVER_DIRECTORY.keys()):
        try:
            if IS_ELECTION_FINISHED:  # Election finished due to timer is up
                break

            channel = grpc.insecure_channel(SERVER_DIRECTORY[key])
            stub = raft_pb2_grpc.RaftStub(channel)

            message = raft_pb2.RequestVoteMessage(candidateID=SERVER_ID, currentTerm=TERM_NUMBER)
            response = stub.RequestVote(message)

            if response.voteGranted:
                votes += 1
            else:
                if response.currentTerm > TERM_NUMBER:
                    TERM_NUMBER = response.currentTerm
                    SERVER_STATUS = ServerState.Follower
                    print(
                        f"This server #{SERVER_ID} (Status: Follower / Current Term: {TERM_NUMBER}) opted out of "
                        f"election")
                    break
        except grpc.RpcError:
            continue

    if SERVER_STATUS.name == 'Follower':  # Candidate became Follower during election
        TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
    else:
        if votes == 1:
            print('1 vote received')
        elif votes > 1:
            print(f'{votes} votes received')

        majority = len(list(SERVER_DIRECTORY.keys())) / 2

        if votes > majority:
            print(f"This server #{SERVER_ID} is the Leader (Term: {TERM_NUMBER})")
            SERVER_STATUS = ServerState.Leader
            LEADER = SERVER_ID
            TIMER_THREAD = RaftTimer(HEARTBEAT_INTERVAL, send_heartbeat)
        else:  # Candidate does not have the majority of votes
            SERVER_STATUS = ServerState.Follower
            ELECTION_TIMEOUT = generate_random_timeout()
            TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)

    TIMER_THREAD.start()
    VOTED = None


# Stop election when timer is up
def stop_election():
    global IS_ELECTION_FINISHED
    IS_ELECTION_FINISHED = True


def serve():
    global SERVER_STATUS, TIMER_THREAD, SERVER_ID, ELECTION_TIMEOUT, SERVER_ADDRESS, TERM_NUMBER, SERVER_DIRECTORY, MATCH_INDEX, NEXT_INDEX
    SERVER_STATUS = ServerState.Follower
    ELECTION_TIMEOUT = generate_random_timeout()

    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_pb2_grpc.add_RaftServicer_to_server(Raft(), grpc_server)
    grpc_server.add_insecure_port('[::]:' + str(SERVER_PORT))

    MATCH_INDEX[SERVER_ID] = 0
    NEXT_INDEX[SERVER_ID] = 0

    try:
        TIMER_THREAD = RaftTimer(ELECTION_TIMEOUT, start_election)
        grpc_server.start()
        TIMER_THREAD.start()

        print("This server #{} is up on {}:{} as a Follower (Current Term: {})\n".format(SERVER_ID,
                                                                                         SERVER_ADDRESS,
                                                                                         SERVER_PORT, TERM_NUMBER))

        grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        print(f'\nStopping this server #{SERVER_ID}')
        TIMER_THREAD.cancel()


if __name__ == "__main__":
    config_server()
    verify_server_log()
    register_this_server()
    serve()
