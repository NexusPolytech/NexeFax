#!/usr/bin/python3

###########################################################################
# Copyright (C) 2023, Nexus Polytech Pty Limited. Some rights reserved.
#
# nexuspoly.tech | contact@nexuspoly.tech | GPO Box 1231, SYDNEY NSW 2001
#
# Codebase: NexeFax
#
# License: BSD 3-Clause License
#
# See LICENSE file for more details.
###########################################################################


import signal
import logging
import time
import modules.nexefax.common as common
import modules.nexefax.rx as rx
import modules.nexefax.tx as tx
from modules.nexefax.Fagi_server.Fagi_server import Fagi_server
from modules.nexefax.Fagi_server.Fagi_server_handler import Fagi_server_handler
from modules.nexefax.Http_server.Http_server import Http_server
from modules.nexefax.Http_server.Http_server_handler import Http_server_handler


class Efax_server:
    processing_rx = False
    message_queue = []
    stopping = False

    def start_fagi_server(self):
        fagi_port = self.config.getint("server", "port_fagi")
        bind_addr = self.config.get("server", "bind")
        self.fagi_srv = Fagi_server((bind_addr, fagi_port), Fagi_server_handler)
        self.fagi_srv.start(self)

    def start_http_server(self):
        http_port = self.config.getint("server", "port_http")
        bind_addr = self.config.get("server", "bind")
        self.http_srv = Http_server((bind_addr, http_port), Http_server_handler)
        self.http_srv.start(self)

    def start(self):
        common.initLogging()
        self.config = common.get_config()
        logging.info("Starting NexeFax Server")
        self.maintain_tmp()
        try:
            self.start_fagi_server()
            self.start_http_server()
        except Exception as e:
            logging.error("Could not initialise NexeFax server. " + repr(e))
            quit()
        self.register_signals()
        self.run()

    def stop(self, _signo=None, _stack_frame=None):
        logging.info("Stopping NexeFax Server")
        self.stopping = True
        self.fagi_srv.stop()
        self.http_srv.stop()

    def register_signals(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGHUP, self.stop)
        signal.signal(signal.SIGABRT, self.stop)

    def run(self):
        self.rx()
        cycle = 0
        while True:
            if self.stopping == True:
                break
            time.sleep(1)
            self.proc_queue()
            if cycle > 60:
                self.maintain()
                cycle = -1
            cycle += 1
        logging.info("NexeFax has shutdown")
        quit()

    def maintain(self):
        if self.http_srv.bg_thread.is_alive():
            self.http_srv.session_maintain()
        else:
            self.start_http_server()
        if self.fagi_srv.bg_thread.is_alive() == False:
            self.start_fagi_server()

    def maintain_tmp(self):
        config = common.get_config()
        # Not yet implemented

    def rx(self):
        self.post("rx")

    def tx(self, data):
        return tx.proc(data)

    def tx_post(self, data):
        self.post("tx_post", data)

    def post(self, type, data=None):
        self.message_queue.append({"type": type, "data": data})

    def proc_rx(self):
        if self.processing_rx:
            return False
        self.processing_rx = True
        rx.proc()
        self.processing_rx = False
        return True

    def proc_tx_post(self, data):
        return tx.proc_post(data)

    def proc_queue(self):
        for msg in self.message_queue:
            try:
                result = self.proc_message(msg)
            except Exception as e:
                result = True  # remove the message that caused an exception
                logging.error(
                    "Exception thrown in proc_message: " + repr(e) + " " + repr(msg)
                )
            if result == True:
                self.message_queue.remove(msg)

    def proc_message(self, msg):
        match msg.get("type"):
            case "rx":
                return self.proc_rx()
            case "tx_post":
                return self.proc_tx_post(msg.get("data"))
            case _:
                logging.error("Invalid Message was posted.")
                logging.error(repr(msg))
                return True
