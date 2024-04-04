import random
import threading


class Server:
    def __init__(self, server_id, peers, is_primary=False):
        self.server_id = server_id
        self.peers = peers  # a list of addresses of peer servers
        self.is_primary = is_primary
        self.current_term = 0
        self.voted_for = None
        self.election_timeout = random.uniform(5, 10)
        self.election_timer = threading.Timer(self.election_timeout, self.initiate_election)
        self.start_election_timer()

    def log(self, message):
        print(f"{self.server_id}: {message}")

    def start_election_timer(self):
        self.election_timer.cancel()  # cancel any existing timer
        self.election_timer = threading.Timer(self.election_timeout, self.initiate_election)
        self.election_timer.start()

    def initiate_election(self):
        self.current_term += 1
        self.voted_for = self.server_id
        self.is_primary = False  # temporarily step down until election is resolved
        self.log("Election started.")
        # election logic to request votes from peers would go here

    def receive_vote_request(self, term, candidate_id):
        if term < self.current_term:
            return False  # Old term
        if self.voted_for is None or self.voted_for == candidate_id:
            self.voted_for = candidate_id
            self.start_election_timer()  # Reset election timer
            return True
        return False

        # don't forget to handle client requests, heartbeats, etc.
