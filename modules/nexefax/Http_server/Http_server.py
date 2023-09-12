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


import http.server
import threading
import logging
import os
import modules.nexefax.common as common


class Http_server(http.server.HTTPServer):
    __VER = 0.1
    __SESSIONS: dict = {}
    __MIMETYPES: dict = {}

    def version_string(self):
        return "SadHTTP/" + str(self.__VER)

    def start(self, efaxsrv):
        logging.info("Starting HTTP listening service")
        self.efaxsrv = efaxsrv
        self.bg_thread = threading.Thread(target=self.serve_forever)
        self.bg_thread.start()

    def stop(self):
        logging.info("Stopping HTTP listening service")
        self.shutdown()
        self.server_close()

    def login_valid(self, account, user, password):
        if account == "" or user == "" or password == "":
            return False
        account_credentials = self.get_account_logins(account)
        if account_credentials == False:
            return False
        if user not in account_credentials:
            return False
        stored_pass_hash = account_credentials[user]
        hash_match = common.hash_verify(password, stored_pass_hash)
        return hash_match

    def get_account_logins(self, account: str):
        auth_path = common.CFG_LOCATION + "/auth/"
        auth_file = auth_path + account.lower()
        if os.path.exists(auth_file) == False:
            return False
        credentials = {}
        with open(auth_file) as htpwd:
            for line in htpwd.readlines():
                username, pwd = line.strip().split(":")
                credentials[username] = pwd
        return credentials

    def session_start(self):
        session_id = common.generate_random_str(32)
        config = common.get_config()
        session_length = config.getint("server", "web_session_length")
        now = common.get_time()
        session_data = {}
        session_data["id"] = session_id
        session_data["expire"] = now + session_length
        session_data["valid"] = True
        self.__SESSIONS[session_id] = session_data
        return session_id

    def session_get(self, session_id):
        if session_id not in self.__SESSIONS:
            return {}
        session_data = self.__SESSIONS[session_id]
        session_expire = session_data["expire"]
        now = common.get_time()
        if now >= session_expire:
            self.session_end(session_id)
            return {}
        return session_data

    def session_set(self, session_id, new_session_data):
        session_data: dict = self.session_get(session_id)
        if "valid" not in session_data:
            return
        read_only_keys = ["id", "expire", "valid"]
        for key_id in new_session_data:
            if key_id not in read_only_keys:
                session_data[key_id] = new_session_data[key_id]
        self.__SESSIONS[session_id] = session_data

    def session_end(self, session_id):
        self.__SESSIONS.pop(session_id)

    def session_maintain(self):
        for x in self.__SESSIONS:
            self.session_get(x)

    def mime_get(self, ext: str):
        if len(self.__MIMETYPES) == 0:
            self.mime_load()
        ext = ext.lower()
        default = "application/octet-stream"
        if ext not in self.__MIMETYPES:
            return default
        return self.__MIMETYPES[ext]

    def mime_load(self):
        cwd = os.getcwd()
        MIME_TYPES_FILE = os.path.dirname(__file__) + "/mime.types"
        f = open(MIME_TYPES_FILE, "r")
        contents = f.readlines()
        for x in contents:
            parts = x.strip().split("\t")
            self.__MIMETYPES[parts[0]] = parts[1]

    def get_efax_srv(self):
        return self.efaxsrv
