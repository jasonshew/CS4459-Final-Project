import json
import os
import random
import sys
import threading
import time
from concurrent import futures
from datetime import datetime

import grpc

import heartbeat_service_pb2 as heartbeat_service
import heartbeat_service_pb2_grpc
import raft_pb2
import raft_pb2_grpc
import replication_pb2_grpc

SERVER_CONFIG_FILE = "server_config.json"  # This is the default config file. Should use a customized config file using command line
SERVER_DIRECTORY = "server_directory.json"
ACK = "REQUEST COMPLETED"
REQUESTS_FROM_CLIENTS = {}
HEARTBEAT_INTERVAL = 2
ELECTION_TIMEOUT = 5


class Raft(raft_pb2_grpc.RaftServicer):
    def __init__(self, server):
        self.server = server

    def AppendEntries(self, request, context):
        return raft_pb2.AppendEntriesReply(replier_id=request.requester_id, current_term=request.term,
                                           success=request.success)

    def RequestVote(self, request, context):
        return raft_pb2.VoteReply(replier_id=self.server.requester_id, current_term=request.current_term,
                                  last_log_index=request.last_log_index, last_log_term=request.last_log_term,
                                  vote_granted=True)

    def Submit(self, request, context):
        return raft_pb2.SubmitReply(replier_id=request.requester_id, message=request.message)


class Server:
    def __init__(self):
        self.election_timer = None
        self.election_timeout = None
        self.voted_for = None
        self.current_term = None
        self.is_leader = None
        self.peers = None
        self.logfile = None
        self.port = None
        self.address = None
        self.server_id = None
        self.heartbeat_interval = None
        self.heartbeat_thread = None
        self.last_heartbeat_sender = None
        self.last_heartbeat_arrival_time = None

    def config_server(self, server_config_file, server_directory, is_leader=False):
        dirname = os.path.dirname(__file__)
        server_config_file = os.path.join(dirname, server_config_file)
        server_directory = os.path.join(dirname, server_directory)
        try:
            with open(server_config_file, 'r') as file_1, open(server_directory, 'r') as file_2:
                print(server_config_file, server_directory)
                server_info = json.load(file_1)
                servers_list = json.load(file_2)
                server_info["peers"].clear()
                for each_server in servers_list:
                    if each_server["server_id"] != server_info["server_id"]:
                        server_info["peers"].append(
                            {"server_id": each_server["server_id"], "address": each_server["address"],
                             "port": each_server["port"]})
                        with open(server_config_file, 'w') as file_3:
                            json.dump(server_info, file_3, sort_keys=False, indent=4)
        except FileNotFoundError:
            print("Server configuration file or server directory not found. Check your local filesystem and try again.")
            sys.exit(0)
        self.server_id = server_info["server_id"]
        self.address = server_info["address"]
        self.port = server_info["port"]
        self.logfile = f'server_{self.server_id}_log.json'
        self.peers = server_info['peers']
        self.is_leader = is_leader
        self.current_term = self.get_last_log_term()
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.election_timeout = random.uniform(ELECTION_TIMEOUT, ELECTION_TIMEOUT * 2)
        self.election_timer = threading.Timer(self.election_timeout, self.initiate_election)
        self.start_election_timer()
        return self

    def log(self, message):
        print(f"{self.server_id}: {message}")

    def start_election_timer(self):
        if self.election_timer is not None:
            self.election_timer.cancel()
        self.election_timer = threading.Timer(self.election_timeout, self.initiate_election)
        self.election_timer.start()

        # if self.heartbeat_thread is not None and not self.is_leader:
        #     self.heartbeat_thread = None  # resetting heartbeat thread to ensure it can be restarted

    def initiate_election(self):
        print("Initiating election...............")
        self.current_term += 1
        self.voted_for = self.server_id
        self.is_leader = False  # temporarily step down until election is resolved
        self.log("Election started.")
        if len(self.peers) == 0:
            self.is_leader = True
        else:
            for server in self.peers:
                with grpc.insecure_channel('{}:{}'.format(server["address"], server["port"])) as channel:
                    stub = raft_pb2_grpc.RaftStub(channel)
                    try:
                        vote_response = stub.RequestVote(
                            raft_pb2.VoteRequest(requester_id=self.server_id, current_term=self.current_term,
                                                 last_log_index=self.get_last_log_index(),
                                                 last_log_term=self.get_last_log_term()))
                        print(f"[Vote ↗]Vote request sent from Server {self.server_id}")
                        yield vote_response

                    except grpc.RpcError as e:
                        if "StatusCode.UNAVAILABLE" in str(e):
                            pass
                        else:
                            print("Vote request failed to send\n", e)
        if self.is_leader:
            self.send_heartbeat()

    def receive_vote_request(self, term, candidate_id):
        if term < self.current_term:
            return False  # Old term
        if self.voted_for is None or self.voted_for == candidate_id:
            self.voted_for = candidate_id
            self.start_election_timer()  # Reset election timer
            return True
        return False

    def send_heartbeat(self):
        def heartbeat_loop():
            while self.is_leader:
                for server in self.peers:
                    with grpc.insecure_channel('{}:{}'.format(server["address"], server["port"])) as channel:
                        stub = heartbeat_service_pb2_grpc.ViewServiceStub(channel)
                        try:
                            stub.Heartbeat(
                                heartbeat_service.HeartbeatRequest(service_identifier=self.server_id))
                            print(
                                f"[Heartbeat ↗] Leader Server #{self.server_id} → 🟢 Server #{server['server_id']} (Running), at {datetime.now()}")
                        except grpc.RpcError as e:
                            if "StatusCode.UNAVAILABLE" in str(e):
                                print(
                                    f"[Heartbeat ↗] Leader Server #{self.server_id} → 🔴 Server #{server['server_id']} (Offline), at {datetime.now()}")
                                self.send_heartbeat()
                            else:
                                print(e)
                    time.sleep(HEARTBEAT_INTERVAL)

        if self.is_leader and self.heartbeat_thread is None:
            self.heartbeat_thread = threading.Thread(target=heartbeat_loop)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()

    def monitor(self):
        while not self.is_leader:
            if self.last_heartbeat_arrival_time:
                print(
                    f"[Heartbeat ↙] Last received from Leader Server #{self.last_heartbeat_sender} at {self.last_heartbeat_arrival_time}")
                time_since_last_heartbeat = (datetime.now() - self.last_heartbeat_arrival_time).total_seconds()
                if time_since_last_heartbeat > self.election_timeout:
                    print("[Heartbeat] TIMEOUT:", time_since_last_heartbeat)
                    self.initiate_election()
            else:
                time.sleep(HEARTBEAT_INTERVAL * 2)
                if not self.last_heartbeat_arrival_time:
                    self.is_leader = True
                    self.send_heartbeat()
            time.sleep(HEARTBEAT_INTERVAL)

    def get_last_log_index(self):
        try:
            with open(self.logfile, 'r') as file:
                server_log = json.load(file)
                if not len(server_log['server_log']):
                    return 0
                return server_log[-1]["index"]
        except FileNotFoundError:
            print("No existing server logfile found.")
            return 0

    def get_last_log_term(self):
        try:
            with open(self.logfile, 'r') as file:
                server_log = json.load(file)
                if not len(server_log['server_log']):
                    return 0
                return server_log[-1]["term"]
        except FileNotFoundError:
            print("No existing server logfile found.")
            return 0

    def get_current_leader(self):
        if self.is_leader:
            return self
        return self.last_heartbeat_sender

    def register_this_server(self):
        the_server = {
            "server_id": self.server_id,
            "address": self.address,
            "port": self.port
        }
        try:
            with open(SERVER_DIRECTORY, 'r') as file_1:
                servers_list = json.load(file_1)
                for server in servers_list:
                    if server["server_id"] == self.server_id:
                        return
                servers_list.append(the_server)
                with open(SERVER_DIRECTORY, 'w') as file_2:
                    json.dump(servers_list, file_2, sort_keys=False, indent=4)
                    print("This server has been registered.")
        except FileNotFoundError:
            print("Server directory not found. Registration failed.")
            sys.exit(0)
        except PermissionError:
            print("Permission denied. Check if the file is read-only. Registration failed.")
            sys.exit(0)


class ViewService(heartbeat_service_pb2_grpc.ViewServiceServicer):

    def __init__(self, server):
        self.server = server

    def Heartbeat(self, request, context):
        self.server.is_leader = False
        now = datetime.now()
        sender = request.service_identifier
        self.server.last_heartbeat_arrival_time = now
        self.server.last_heartbeat_sender = sender
        message = "[Heartbeat ↙] From Leader Server #{}, at {}".format(sender, now)
        print(message)
        return heartbeat_service.google_dot_protobuf_dot_empty__pb2.Empty()


class Sequence(replication_pb2_grpc.SequenceServicer):

    def __init__(self, server):
        self.server = server

    def Write(self, request, context):
        key_to_write = request.key
        value_to_write = request.value
        line_to_write = key_to_write + ' ' + value_to_write + '\n'
        REQUESTS_FROM_CLIENTS.update({key_to_write: line_to_write})


def run(this_server):
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=500))
    raft_pb2_grpc.add_RaftServicer_to_server(Raft(this_server), grpc_server)
    replication_pb2_grpc.add_SequenceServicer_to_server(Sequence(this_server), grpc_server)
    heartbeat_service_pb2_grpc.add_ViewServiceServicer_to_server(ViewService(this_server), grpc_server)
    grpc_server.add_insecure_port('[::]:' + str(this_server.port))
    grpc_server.start()
    print("Server #{} is up on {}:{}\n".format(this_server.server_id, this_server.address, this_server.port))

    monitor_thread = threading.Thread(target=this_server.monitor)
    monitor_thread.daemon = True
    monitor_thread.start()

    heartbeat_thread = threading.Thread(target=this_server.send_heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    election_thread = threading.Thread(target=this_server.initiate_election)
    election_thread.daemon = True
    election_thread.start()

    grpc_server.wait_for_termination()


if __name__ == "__main__":
    server_config_file = SERVER_CONFIG_FILE
    server_directory = SERVER_DIRECTORY
    if len(sys.argv) == 3:
        server_config_file = sys.argv[1]
        server_directory = sys.argv[2]
    new_server = Server()
    new_server.config_server(server_config_file, server_directory)
    new_server.initiate_election()
    try:
        with open(new_server.logfile, 'r') as file:
            logfile = json.load(file)
            print("Server logfile located: " + str(len(logfile["server_log"])) + " entries")
    except FileNotFoundError:
        with open(new_server.logfile, 'w') as file:
            initialized_log = {"server_log": []}
            json.dump(initialized_log, file, sort_keys=False)
            print("Server logfile created successfully.")
    new_server.register_this_server()
    run(new_server)
