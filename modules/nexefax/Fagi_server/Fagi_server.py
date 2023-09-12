#!/usr/bin/python3

###########################################################################
# Copyright (C) 2023, Nexus Polytech Pty Limited. Some rights reserved.
#
# nexuspoly.tech | contact@nexuspoly.tech | GPO Box 1231, SYDNEY NSW 2001
#
# Codebase: NexeFax
#
# Version 0.0.1 BETA
#
# License: BSD 3-Clause License
#
# See LICENSE file for more details.
###########################################################################


import socketserver
import threading
import logging


class Fagi_server(socketserver.ThreadingTCPServer):
    def start(self, efaxsrv):
        logging.info("Starting FAGI listening service")
        self.efaxsrv = efaxsrv
        self.bg_thread = threading.Thread(target=self.serve_forever)
        self.bg_thread.start()

    def stop(self):
        logging.info("Stopping FAGI listening service")
        self.shutdown()
        self.server_close()

    def get_efax_srv(self):
        return self.efaxsrv
