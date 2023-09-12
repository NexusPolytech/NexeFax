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


import logging
import os
import configparser
import modules.nexefax.common as common
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def proc(data):
    pdf_file = data["pdf_file"]
    fax_to = data["fax_to"]
    account = data["account"]
    subject = data["subject"]
    user = data["user"]
    fax_file = common.convert_pdf_to_tiff(pdf_file)
    if fax_file == False:
        return False
    os.unlink(pdf_file)
    config = common.get_config()
    tmp_dir = config["general"]["tmp_dir"] + "/"
    new_fax_file_name = (
        "nexefax-send-"
        + account
        + "-"
        + common.get_time_as_str()
        + "-"
        + fax_to
        + "-"
        + common.generate_random_str(10)
        + ".tiff"
    )
    new_fax_file = tmp_dir + new_fax_file_name
    os.rename(fax_file, new_fax_file)
    data["fax_file"] = new_fax_file
    info_file = common.make_info_file(data, new_fax_file)
    if info_file == False:
        return False
    return asterisk_make_call_file(data)


def asterisk_make_call_file(data):
    accounts = common.get_accounts()
    fax_to = data["fax_to"]
    fax_file = data["fax_file"]
    account_id = data["account"]
    callerid_num = accounts.get(account_id, "tx_number")
    callerid_name = accounts.get(account_id, "tx_name")
    callerid_all = '"' + callerid_name + '" <' + callerid_num + ">"
    call_var_channel = accounts.get(account_id, "tx_channel", fallback="").replace(
        "${TO}", fax_to
    )
    call_var_account = account_id
    call_var_callerid = callerid_all
    call_file_data = asterisk_get_call_file_base_params()
    call_file_vars = asterisk_get_call_file_faxopt_vars()
    call_file_data["Account"] = call_var_account
    call_file_data["Channel"] = call_var_channel
    call_file_data["CallerID"] = call_var_callerid
    call_file_vars["FAXTO"] = fax_to
    call_file_vars["FAXFILE"] = fax_file
    fax_queued = common.make_call_file(call_file_data, call_file_vars)
    return fax_queued


def asterisk_get_call_file_base_params():
    config = common.get_config()
    call_var_context = config.get("general", "ast_context", fallback="")
    call_var_maxretries = config.get("general", "tx_max_retries", fallback="5")
    call_var_retrytime = config.get("general", "tx_retry_time", fallback="60")
    call_var_waittime = config.get("general", "tx_wait_time", fallback="30")
    call_file_data = {}
    call_file_data["MaxRetries"] = call_var_maxretries
    call_file_data["RetryTime"] = call_var_retrytime
    call_file_data["WaitTime"] = call_var_waittime
    call_file_data["Context"] = call_var_context
    call_file_data["Extension"] = "send"
    call_file_data["Priority"] = "1"
    return call_file_data


def asterisk_get_call_file_faxopt_vars():
    config = common.get_config()
    call_var_faxopt_ecm = config.get(
        "general", "tx_faxopt_ecm", fallback="yes"
    )
    call_var_faxopt_modem = config.get(
        "general", "tx_faxopt_modem", fallback="v17,v27,v29"
    )
    call_var_faxopt_faxdetect = config.get(
        "general", "tx_faxopt_faxdetect", fallback="no"
    )
    call_var_faxopt_minrate = config.get(
        "general", "tx_faxopt_minrate", fallback="4800"
    )
    call_var_faxopt_maxrate = config.get(
        "general", "tx_faxopt_maxrate", fallback="14400"
    )
    call_var_faxopt_t38timeout = config.get(
        "general", "tx_faxopt_t38timeout", fallback="5000"
    )
    call_var_faxopt_negboth = config.get(
        "general", "tx_faxopt_negboth", fallback="no"
    )
    call_file_vars = {}
    call_file_vars["FAXOPT_GATEWAY"] = "no"
    call_file_vars["FAXOPT_ECM"] = call_var_faxopt_ecm
    call_file_vars["FAXOPT_MODEM"] = call_var_faxopt_modem
    call_file_vars["FAXOPT_FAXDETECT"] = call_var_faxopt_faxdetect
    call_file_vars["FAXOPT_MINRATE"] = call_var_faxopt_minrate
    call_file_vars["FAXOPT_MAXRATE"] = call_var_faxopt_maxrate
    call_file_vars["FAXOPT_T38TIMEOUT"] = call_var_faxopt_t38timeout
    call_file_vars["FAXOPT_NEGOTIATE_BOTH"] = call_var_faxopt_negboth
    return call_file_vars


def proc_post(data):
    account_id = data.get("account")
    if common.does_account_exist(account_id) == False:
        logging.warning("No account was found with the ID " + account_id)
        return
    account_setttings = common.get_accountsettings(account_id)
    fax_status = data.get("status")
    fax_error = data.get("error")
    fax_file = data.get("file")
    tx_notify_success = account_setttings.get("tx_notify_success")
    tx_notify_failure = account_setttings.get("tx_notify_failure")
    result = False
    if fax_status == "SUCCESS":
        if tx_notify_success:
            result = notify_success(fax_file)
        else:
            result = True
    else:
        if tx_notify_failure:
            result = notify_fail(fax_file, fax_error)
        else:
            result = True
    if result:
        os.unlink(fax_file)
        os.unlink(fax_file + ".txt")
    return result


def load_info_file(fax_file):
    info_file = fax_file + ".txt"
    fax_info = configparser.ConfigParser()
    fax_info.read(info_file)
    return fax_info


def notify_success(fax_file):
    return notify(fax_file, None)


def notify_fail(fax_file, fax_error):
    return notify(fax_file, fax_error)


def notify(fax_file, error=None):
    fax_info = load_info_file(fax_file)
    config = common.get_config()
    fax_to = fax_info.get("nexefax", "fax_to")
    account_id = fax_info.get("nexefax", "account")
    # fax_to_name = fax_info.get("nexefax", "to_name")
    fax_to_name = ""
    fax_to_string = fax_to
    if fax_to_name != "":
        fax_to_string = fax_to_name + "<" + fax_to + ">"
    account_settings = common.get_accountsettings(account_id)
    from_name = config["email"]["from_name"]
    from_email = config["email"]["from_email"]
    header_from = from_name + " <" + from_email + ">"
    header_subject = (
        "eFax "
        + ("sent" if error is None else "failed to send")
        + " to "
        + fax_to_string
    )
    to_raw = account_settings.get("rx_email_to", "")
    cc_raw = None
    if "rx_email_cc" in account_settings:
        cc_raw = account_settings["rx_email_cc"]
    content_body = "Hi " + account_settings.get("info_name") + ",\n\n"
    if error is None:
        content_body += "Your fax was sent successfully!"
    else:
        content_body += "An error occured when sending your fax.\n\nError: " + error
    content_body += (
        "\n\nA copy of the fax file and the fax information is attached to this email."
    )
    msg = MIMEMultipart()
    msg["From"] = header_from
    msg["Subject"] = header_subject
    msg["To"] = to_raw
    if cc_raw is not None:
        msg["Cc"] = cc_raw
    msg.attach(MIMEText(content_body))
    file_name = fax_file[fax_file.rindex("/") + 1 :]
    with open(fax_file, "rb") as file:
        part = MIMEApplication(file.read(), Name=file_name)
        part["Content-Disposition"] = 'attachment; filename="' + file_name + '"'
        msg.attach(part)
    with open(fax_file + ".txt", "rb") as file:
        part = MIMEApplication(file.read(), Name=file_name + ".txt")
        part["Content-Disposition"] = 'attachment; filename="' + file_name + '.txt"'
        msg.attach(part)
    return common.send_email(msg)
