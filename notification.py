def notify_peers_of_new_primary(self):
    new_primary_address = self.server_address
    # add code to notify backups
    for backup_address in self.peers:
        # send notification to backup_address
        pass
