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


import os.path
import configparser
import logging
import string
import random
import socket
import time
import smtplib
import bcrypt
from email import utils as emailutils
from subprocess import Popen, PIPE

CFG_LOCATION = "/etc/nexefax/"

__config__ = None
__accounts__ = None


def initLogging():
    config = get_config()
    log_file = config["logging"]["file"]
    log_level = logging.INFO
    if config.getboolean("logging", "debug"):
        log_level = logging.DEBUG
    logging.basicConfig(
        filename=log_file,
        encoding="utf-8",
        level=log_level,
        format="%(asctime)s: [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
    )


def get_config():
    global __config__
    if __config__ is not None:
        return __config__
    cfg_file = CFG_LOCATION + "/config.conf"
    cfg_exists = os.path.isfile(cfg_file)
    if cfg_exists == False:
        raise Exception("Configuration file (" + cfg_file + ") could not be loaded.")
    config = configparser.ConfigParser()
    config.read_dict(get_config_defaults())
    config.read(cfg_file)
    validate_config(config)
    __config__ = config
    return config


def get_config_defaults():
    default = {
        "general": {
            "rx_dir": "/var/spool/asterisk/tmp",
            "ast_call_dir": "/var/spool/asterisk/outgoing",
            "tmp_dir": "/tmp/nexefax",
            "ast_context": "nexefax",
            "tx_max_retries": "5",
            "tx_retry_time": "300",
            "tx_wait_time": "30",
            "tx_faxopt_ecm": "yes",
            "tx_faxopt_modem": "v17,v27,v29",
            "tx_faxopt_faxdetect": "no",
            "tx_faxopt_minrate": "4800",
            "tx_faxopt_maxrate": "14400",
            "tx_faxopt_t38timeout": "5000",
            "tx_faxopt_negboth": "no",
        },
        "logging": {
            "file": "/var/log/nexefax/info.log",
            "debug": "no",
        },
        "server": {
            "bind": "0.0.0.0",
            "port_fagi": "4573",
            "port_http": "3298",
            "web_session_length": "86400",
        },
        "email": {
            "method": "sendmail",
            "smtp_mode": "",
            "smtp_port": "25",
            "smtp_auth": "no",
            "smtp_host": "127.0.0.1",
            "smtp_auth_user": "",
            "smtp_auth_pass": "",
            "from_name": "NexeFax",
            "from_email": "nexefax@" + socket.gethostname(),
            "subject": "New eFax Received",
        },
    }
    return default


def get_account_defaults():
    config = get_config()
    default = {
        "info_name": "",
        "info_fax": "",
        "info_phone": "",
        "info_email": "",
        "info_web": "",
        "rx_email_cc": "",
        "tx_email_to": "",
        "tx_name": "",
        "tx_notify_success": False,
        "tx_notify_failure": True,
        "tx_channel": config.get("general", "tx_channel"),
    }
    return default


def validate_config(config: configparser.ConfigParser):
    if config.has_option("general", "tx_channel") == False:
        raise Exception(
            "Configuration option 'tx_channel' in section [general] was not set in config.conf"
        )
    if "${TO}" not in config["general"]["tx_channel"]:
        raise Exception(
            "Configuration option 'tx_channel' in section [general] is missing the '${TO}' variable in config.conf"
        )
    if config.getint("server", "port_fagi", fallback=-1) == -1:
        raise Exception(
            "Configuration option 'port_fagi' in section [server] is not an integer in config.conf"
        )
    if config.getint("server", "port_http", fallback=-1) == -1:
        raise Exception(
            "Configuration option 'port_http' in section [server] is not an integer in config.conf"
        )
    if config["email"]["method"].lower() not in ["smtp", "sendmail"]:
        raise Exception(
            "Configuration option 'method' in section '[email]' is not valid in config.conf"
        )
    if config["email"]["smtp_mode"].lower() not in ["tls", "ssl", ""]:
        raise Exception(
            "Configuration option 'method' in section '[email]' is not valid in config.conf"
        )


def get_time():
    return int(time.time())


def get_time_as_str():
    return str(get_time())


def get_accounts():
    global __accounts__
    if __accounts__ is not None:
        return __accounts__
    accounts_file = CFG_LOCATION + "accounts.conf"
    accounts_exists = os.path.isfile(accounts_file)
    if accounts_exists == False:
        raise Exception("Accounts file (" + accounts_file + ") could not be loaded.")
    accounts = configparser.ConfigParser()
    accounts["DEFAULT"] = get_account_defaults()
    accounts.read(accounts_file)
    account_ids = accounts.sections()
    required_settings = ["rx_email_to", "tx_number", "tx_name"]
    for account_id in account_ids:
        new_account_id = account_id.lower()
        section_data = accounts[account_id]
        accounts[new_account_id] = section_data
        accounts.remove_section(account_id)
        for setting_name in required_settings:
            if accounts.has_option(new_account_id, setting_name) == False:
                logging.error(
                    "The required setting "
                    + setting_name
                    + " has not been set for account "
                    + new_account_id
                )
                raise Exception(
                    "The required setting "
                    + setting_name
                    + " has not been set for account "
                    + new_account_id
                )
    __accounts__ = accounts
    return accounts


def does_account_exist(account_id: str):
    return get_accounts().has_section(account_id.lower())


def get_accountsettings(account_id: str):
    accounts = get_accounts()
    account_id = account_id.lower()
    return accounts[account_id]


def convert_tiff_to_pdf(file: str):
    options = "-format pdf -density 300x300 -compress LZW"
    cmd = "convert $IN " + options + " $OUT"
    return convert_file("pdf", cmd, file)


def convert_pdf_to_tiff(file: str):
    options = "-q -dBATCH -dNOPAUSE -sDEVICE=tiffg4"
    cmd = "gs " + options + " -sOutputFile=$OUT $IN"
    return convert_file("tiff", cmd, file)


def convert_file(file_format: str, cmd: str, input_file: str):
    config = get_config()
    tmp_dir = config["general"]["tmp_dir"] + "/"
    if os.path.exists(tmp_dir) == False:
        dir_created = os.mkdir(tmp_dir)
        if dir_created == False:
            logging.error("Could not create TMP_DIR at " + tmp_dir)
            return False
    last_slash_location = input_file.rindex("/")
    dot_location = input_file.index(".")
    file_name = input_file[last_slash_location + 1 : dot_location]
    output_file = (
        tmp_dir + file_name + "-" + generate_random_str(6) + "." + file_format.lower()
    )
    cmd = cmd.replace("$IN", input_file).replace("$OUT", output_file)
    if os.path.exists(output_file):
        os.unlink(output_file)
    os.system(cmd)
    if os.path.isfile(output_file):
        return output_file
    else:
        return False


def send_email(msg):
    config = get_config()
    msg["Date"] = emailutils.formatdate()
    msg.add_header("X-Entity-Ref-ID", generate_random_str(64))
    # msg.add_header("Message-ID", "<" + generateRandom(42) + "@nexefax.local>")
    msg.add_header("Message-ID", emailutils.make_msgid())
    email_method = config["email"]["method"].lower()
    if email_method == "smtp":
        return send_email_via_smtp(msg)
    if email_method == "sendmail":
        return send_email_via_sendmail(msg)
    return False


def send_email_via_sendmail(msg):
    sendmail_bin = "/usr/sbin/sendmail"
    p = Popen([sendmail_bin, "-t", "-oi"], stdin=PIPE, universal_newlines=True)
    p.communicate(msg.as_bytes())
    return False


def send_email_via_smtp(msg):
    config = get_config()
    smtp_host = config.get("email", "smtp_host")
    smtp_port = config.getint("email", "smtp_port")
    smtp_mode = config.get("email", "smtp_mode").upper()
    smtp_auth = config.getboolean("email", "smtp_auth")
    smtp_auth_user = config.get("email", "smtp_auth_user")
    smtp_auth_pass = config.get("email", "smtp_auth_pass")
    try:
        if smtp_mode == "SSL":
            server = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port)
        else:
            server = smtplib.SMTP(host=smtp_host, port=smtp_port)
            if smtp_mode == "TLS":
                tls_established = server.starttls()[0]
                if tls_established != 220:
                    server.quit()
                    logging.error(
                        "Could connect to the SMTP server but failed to start TLS"
                    )
                    return False
        if smtp_auth:
            server.login(smtp_auth_user, smtp_auth_pass)
        email_status = server.send_message(msg)
        server.quit()
        return len(email_status) == 0
    except Exception as e:
        exception_type = e.__class__.__name__
        exception_msg = str(e)
        if exception_type == "SMTPAuthenticationError":
            exception_msg = "Authentication Failed (" + str(e) + ")"
        logging.error("Error sending email via SMTP: " + exception_msg)
        return False


def generate_random_str(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for i in range(length))


def make_call_file(data, vars={}):
    output = ""
    valid_params = [
        "Channel",
        "CallerID",
        "MaxRetries",
        "RetryTime",
        "WaitTime",
        "Account",
        "Context",
        "Extension",
        "Priority",
    ]
    for x in data:
        if x in valid_params:
            output += x + ": " + data[x].strip() + "\n"
    for x in vars:
        output += "SetVar: " + x + "=" + vars[x].strip() + "\n"
    config = get_config()
    call_path = config.get(
        "general", "ast_call_dir", fallback="/tmp"
    )  # tmp as the fallabck value is the safest option
    rand_file_name = generate_random_str(32)
    full_file_name = call_path + "/" + rand_file_name + ".call"
    result = False
    try:
        with open(full_file_name, "w") as call_file:
            result = call_file.write(output) > 0
            call_file.close()
    except:
        return False
    return result


def make_info_file(data, file):
    output = "[nexefax]\n"
    for x in data:
        output += x + "=" + data[x].strip() + "\n"
    try:
        with open(file + ".txt", "w") as info_file:
            result = info_file.write(output) > 0
            info_file.close()
    except:
        return False
    return result


def make_tmp_file(file):
    config = get_config()
    tmp_dir = config["general"]["tmp_dir"] + "/"
    if os.path.exists(tmp_dir) == False:
        dir_created = os.mkdir(tmp_dir)
        if dir_created == False:
            logging.error("Could not create TMP_DIR at " + tmp_dir)
            return False
    tmp_file = tmp_dir + generate_random_str(5) + "_" + file["name"]
    try:
        with open(tmp_file, "wb") as pdf_file:
            result = pdf_file.write(file["data"]) > 0
            pdf_file.close()
            if result == 0:
                return False
    except Exception as e:
        return False
    return tmp_file


def hash_password(plaintext):
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(plaintext, salt)
    return hash


def hash_verify(plaintext, hash):
    return bcrypt.checkpw(plaintext.encode("utf-8"), hash.encode("utf-8"))
