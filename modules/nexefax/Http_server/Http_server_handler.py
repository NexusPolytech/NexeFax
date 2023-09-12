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
import logging
import os
import json
import urllib.parse
import modules.nexefax.common as common
import modules.nexefax.Http_server.Http_server as Http_server


class Http_server_handler(http.server.BaseHTTPRequestHandler):
    server: Http_server.Http_server

    WEB_LOCATION = os.path.dirname(Http_server.__file__) + "/web/"
    RES_LOCATION = WEB_LOCATION + "res/"
    RES_TYPES = ["css", "js", "img", "vid"]

    def version_string(self):
        return self.server.version_string()

    def resp_MIME(self, mime, code=200):
        self.send_response(code)
        self.send_header("Content-type", mime)
        self.req_FINISH()

    def resp_HTML(self, code=200):
        self.resp_MIME("text/html", code)

    def resp_JSON(self, code=200):
        self.resp_MIME("application/json", code)

    def error_404(self):
        self.serve_html("404.html", 404)

    def error_500(self):
        self.resp_HTML(500)
        error = "A Server Error has occured."
        self.wfile.write(error.encode("utf-8"))

    def do_GET(self):
        self.req_INIT()
        logging.debug(
            "GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers)
        )
        path = self.path
        match path:
            case s if path.startswith("/res/"):
                return self.serve_res(path)
            case "/":
                return self.req_REDIRECT("/login")
            case "/login":
                return self.page_login()
            case "/logout":
                return self.page_logout()
            case "/send":
                return self.page_send()
            case _:
                return self.error_404()

    def do_POST(self):
        self.req_INIT()
        logging.debug(
            "POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
            str(self.path),
            str(self.headers),
            repr(self._POST),
        )
        path = format(self.path)
        match path:
            case "/api/login":
                return self.api_login()
            case "/api/status":
                return self.api_status()
            case "/api/send":
                return self.api_send()
            case _:
                return self.error_404()

    def req_INIT(self):
        self._POST = {}
        self._FILE = {}
        self.get_init()
        self.cookie_init()
        self.session_init()
        if self.command == "POST":
            self.post_process_postdata()

    def req_REDIRECT(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.req_FINISH()

    def req_FINISH(self):
        if "clear" in self._SESSION:
            self.send_header(
                "Set-Cookie",
                "nexefax-session=XXXXXXXX; expires=Thu, 01 Jan 1970 00:00:00 GMT",
            )
        self.end_headers()

    def req_IP(self):
        if "X-Forwarded-For" not in self.headers:
            return self.client_address[0]
        return self.headers['X-Forwarded-For']

    def session_init(self):
        self._SESSION = {}
        self.AUTH = False
        if "nexefax-session" not in self._COOKIE:
            return
        session_id_claimed = self._COOKIE["nexefax-session"]
        session_data = self.server.session_get(session_id_claimed)
        if "valid" not in session_data:
            self.session_send_clear_flag()
            return
        self._SESSION = session_data
        self.AUTH = True

    def session_send_clear_flag(self):
        self._SESSION["clear"] = True

    def auth_check(self, no_redirect=False):
        if self.AUTH == True:
            return True
        if no_redirect == False:
            self.req_REDIRECT("/login")
        return False

    def get_init(self):
        self._GET = {}
        if "?" not in self.path and "&" not in self.path:
            return
        if "?" in self.path:
            idx = self.path.index("?")
        else:
            idx = self.path.index("&")
        query_raw = self.path[idx + 1 :]
        self.path = self.path[0:idx]
        raw_get_segments = query_raw.split("&")
        for x in raw_get_segments:
            if "=" not in x:
                x = x + "="
            parts = x.split("=")
            self._GET[urllib.parse.unquote(parts[0])] = urllib.parse.unquote(parts[1])

    def cookie_init(self):
        self._COOKIE = {}
        if "Cookie" not in self.headers:
            return
        cookie_raw = self.headers["Cookie"]
        cookie_raw_parts = cookie_raw.split("; ")
        for x in cookie_raw_parts:
            if "=" not in x:
                x = x + "="
            parts = x.split("=")
            self._COOKIE[parts[0]] = parts[1]

    def post_process_postdata(self):
        self._POST = {}
        self._FILE = {}
        if "Content-Type" not in self.headers:
            return
        content_length = int(self.headers["Content-Length"])
        content_type_full = self.headers["Content-Type"]
        if ";" in content_type_full:
            content_type = content_type_full[0 : content_type_full.index(";")]
        else:
            content_type = content_type_full
        raw_post_data = self.rfile.read(content_length)
        match content_type:
            case "application/x-www-form-urlencoded":
                self.post_process_form_urlencoded(raw_post_data)
            case "multipart/form-data":
                self.post_process_form(raw_post_data, content_type_full)

    def post_process_form(self, raw_post_data: bytes, content_type_full: str):
        if "boundary=" not in content_type_full:
            return
        boundary = "--" + content_type_full[content_type_full.index("boundary=") + 9 :]
        post_parts = raw_post_data[0:-2].split(boundary.encode())
        for part in post_parts:
            post_part = part.strip()
            if (b"Content-Disposition" not in post_part) and (b";" not in post_part):
                continue
            idx1 = post_part.index(b"Content-Disposition:")
            idx1 = idx1 + 20
            idx2 = post_part.index(b";")
            if b'\r\n' not in post_part:
                idx3 = len(post_part)
            else:
                idx3 = post_part.index(b"\r\n")
            content_disposition = post_part[idx1:idx2].strip()
            if content_disposition != b"form-data":
                return
            content_header_parts_raw = post_part[idx1:idx3].decode().strip().split(";")
            content_header_parts = {}
            for x in content_header_parts_raw:
                if "=" not in x:
                    continue
                x_parts = x.split("=")
                content_header_parts[x_parts[0].strip()] = x_parts[1].strip()
            if "name" not in content_header_parts:
                return
            var_name = content_header_parts["name"][1:-1]
            is_file = "filename" in content_header_parts
            if is_file:
                file_name = content_header_parts["filename"][1:-1]
                idx4 = post_part.index(b"\r\n", idx3 + 1)
                type_line_raw = post_part[idx3 + 2 : idx4].decode()
                if "Content-Type:" not in type_line_raw:
                    break
                file_type = type_line_raw[13:].strip()
                file_data = post_part[idx4 + 1 :]
                self._FILE[var_name] = {
                    "mime": file_type,
                    "name": file_name,
                    "data": file_data,
                }
                continue
            else:
                self._POST[var_name] = post_part.decode()[idx3 + 1 :].strip()

    def post_process_form_urlencoded(self, raw_post_data):
        raw_post_data_decoded = raw_post_data.decode("utf-8")
        raw_post_data_segments = raw_post_data_decoded.split("&")
        for x in raw_post_data_segments:
            if "=" not in x:
                x = x + "="
            parts = x.split("=")
            self._POST[urllib.parse.unquote(parts[0])] = urllib.parse.unquote(parts[1])

    def serve_res(self, res_path: str):
        res_path_parts = res_path.split("/")
        res_type = res_path_parts[2]
        res_file = res_path_parts[3]
        res_file_path = self.RES_LOCATION + res_type + "/" + res_file
        if res_type not in self.RES_TYPES or os.path.isfile(res_file_path) == False:
            return self.error_404()
        mime_type = ""
        match res_type:
            case "js":
                mime_type = "application/javascript"
            case "css":
                mime_type = "text/css"
            case "img" | "vid":
                ext = res_file[res_file.index(".") + 1 :]
                mime_type = self.server.mime_get(ext)
        self.resp_MIME(mime_type)
        self.serve_file("res/" + res_type + "/" + res_file)

    def serve_file(self, res, code=200):
        file = self.WEB_LOCATION + res
        if os.path.isfile(file) is False:
            logging.error("HTTP: Tried to serve non existant file " + res)
            return self.error_500()
        f = open(file, "rb")
        contents = f.read()
        self.wfile.write(contents)

    def serve_html(self, res, code=200):
        file = self.WEB_LOCATION + res
        if os.path.isfile(file) == False:
            logging.error("HTTP: Tried to serve non existant HTML file " + res)
            return self.error_500()
        f = open(file, "r")
        contents = f.read()
        self.resp_HTML(code)
        self.wfile.write(contents.encode("utf-8"))

    def page_send(self):
        if self.auth_check() == False:
            return
        self.serve_html("send.html")

    def page_login(self):
        if self.auth_check(True):
            return self.req_REDIRECT("/send")
        self.serve_html("login.html")

    def page_logout(self):
        self.session_send_clear_flag()
        return self.req_REDIRECT("/login")

    def api_error(self, error, code=400):
        json_object = {}
        json_object["result"] = "error"
        json_object["error"] = error
        return self.api_output(json_object, code)

    def api_result(self, data):
        json_object = {}
        json_object["result"] = "ok"
        json_object["data"] = data
        return self.api_output(json_object, 200)

    def api_output(self, data_object, code=200):
        self.resp_JSON(code)
        json_out = json.dumps(data_object)
        self.wfile.write(json_out.encode("utf-8"))

    def api_login(self):
        account = ""
        user = ""
        password = ""
        if "account" in self._POST:
            account = self._POST["account"]
        if "user" in self._POST:
            user = self._POST["user"]
        if "password" in self._POST:
            password = self._POST["password"]
        login_valid = self.server.login_valid(account, user, password)
        ip = self.req_IP()
        log_txt = ("Successful" if login_valid else "Failed") + " login for Account: " + account + ", User: " + user + ", IP: " + ip
        logging.info(log_txt)
        if login_valid:
            session_id = self.server.session_start()
            data = {"account": account.lower(), "user": user}
            self.server.session_set(session_id, data)
            return self.api_result(session_id)
        else:
            return self.api_error("Invalid Login Credentials")

    def api_status(self):
        if self.auth_check() == False:
            return
        account_id = self._SESSION["account"]
        config = common.get_config()
        account_settings = common.get_accountsettings(account_id.lower())
        tx_name = account_settings.get("tx_name")
        tx_number = account_settings.get("tx_number")
        data = {}
        data["account"] = self._SESSION["account"]
        data["user"] = self._SESSION["user"]
        data["tx_name"] = tx_name
        data["tx_number"] = tx_number
        return self.api_result(data)

    def api_send(self):
        if self.auth_check() == False:
            return
        post_data_good = True
        if "fax_to" not in self._POST:
            post_data_good = False
        if "subject" not in self._POST:
            post_data_good = False
        if "fax_file" not in self._FILE:
            post_data_good = False
        if post_data_good == False:
            return self.api_error(
                "One of the details needed to send your eFax was missing."
            )
        if self._FILE["fax_file"]["mime"].lower() != "application/pdf":
            return self.api_error("Only PDF files can be sent as a Fax.")
        tmp_file = common.make_tmp_file(self._FILE["fax_file"])
        if tmp_file == False:
            return self.api_error(
                "Your eFax system is not configured correctly. Please contact your system administrator."
            )
        data = {}
        data["pdf_file"] = tmp_file
        data["fax_to"] = self._POST["fax_to"]
        data["subject"] = self._POST["subject"]
        if "message" in self._POST:
            data["message"] = self._POST["message"]
        else:
            data["message"] = ""
        data["account"] = self._SESSION["account"]
        data["user"] = self._SESSION["user"]
        data["ip"] = self.req_IP()
        result = self.server.get_efax_srv().tx(data)
        if result == False:
            return self.api_error(
                "An error ocured sending your eFax. Please try again."
            )
        else:
            return self.api_result("Sent!")

    def dev_stop(self):
        self.server.get_efax_srv().stop()
