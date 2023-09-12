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
import logging
import modules.nexefax.Fagi_server.Fagi_server as Fagi_server


class Fagi_server_handler(socketserver.StreamRequestHandler):
    server: Fagi_server.Fagi_server
    agivars = {}

    def handle(self):
        logging.debug("New request on the Fagi server")
        self.agivars = {}
        while True:
            self.data = self.rfile.readline().strip().decode("utf-8")
            if self.data == "":
                break
            try:
                self.proc_data()
            except Exception as e:
                logging.debug(
                    "A Processing error with this AGI data: " + repr(self.data)
                )
        self.handle_request()

    def proc_data(self):
        if self.data.startswith("agi_"):
            return self.proc_agivar()
        match self.data:
            case _:
                return

    def proc_agivar(self):
        colonLoc = self.data.index(":")
        varname = self.data[4:colonLoc]
        varval = self.data[colonLoc + 1 :].strip()
        self.agivars.update({varname: varval})
        logging.debug("AGI Variable " + varname + " is " + varval)

    def handle_request(self):
        url = ""
        if "network_script" in self.agivars:
            url = self.agivars.get("network_script")
        match url:
            case "test":
                return self.handle_test()
            case "receive":
                return self.handle_rx()
            case "send/post":
                return self.handle_tx_post()
            case _:
                return self.handle_error(404)

    def handle_error(self, code=500):
        self.output("Error " + str(code))

    def handle_rx(self):
        self.server.get_efax_srv().rx()

    def handle_tx_post(self):
        fax_status = self.agivars.get("arg_1")
        fax_error = self.agivars.get("arg_2")
        fax_file = self.agivars.get("arg_3")
        account = self.agivars.get("accountcode")
        msg_data = {
            "status": fax_status,
            "error": fax_error,
            "file": fax_file,
            "account": account,
        }
        self.server.get_efax_srv().tx_post(msg_data)

    def handle_test(self):
        self.output("eFax Test hit!")

    def output(self, txt):
        self.wfile.write(txt.encode("utf-8"))
