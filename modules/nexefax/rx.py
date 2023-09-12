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
import modules.nexefax.common as common
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def proc():
    logging.info("Processing received eFaxes")
    pending_files = get_pending_files()
    for file in pending_files:
        if proc_pending_file(file) == False:
            logging.error("Failed to process " + file)


def proc_pending_file(file_name_full):
    config = common.get_config()
    logging.info("Processing file " + file_name_full)
    file_tiff = config["general"]["rx_dir"] + "/" + file_name_full
    dot_location = file_name_full.index(".tiff")
    file_name = file_name_full[0:dot_location]
    file_parts = file_name.split("-")
    if len(file_parts) != 6:
        return False
    account_id = file_parts[1]
    if common.does_account_exist(account_id) == False:
        logging.warning("No account was found with the ID " + account_id)
        return
    file_pdf = common.convert_tiff_to_pdf(file_tiff)
    if file_pdf == False:
        logging.error("Could not convert TIFF file to PDF")
        return False
    email_sent = send_email(account_id, file_pdf)
    os.unlink(file_pdf)
    if email_sent:
        os.unlink(file_tiff)
    return email_sent


def get_pending_files():
    config = common.get_config()
    rx_dir = config["general"]["rx_dir"] + "/"
    return [
        filename
        for filename in os.listdir(rx_dir)
        if filename.startswith("nexefax-") and filename.endswith(".tiff")
    ]


def send_email(account_id: str, pdf_file: str):
    config = common.get_config()
    account_settings = common.get_accountsettings(account_id)
    from_name = config["email"]["from_name"]
    from_email = config["email"]["from_email"]
    header_from = from_name + " <" + from_email + ">"
    header_subject = account_settings.get(
        "rx_email_subject", config["email"]["subject"]
    )

    to_raw = account_settings.get("rx_email_to", "")
    cc_raw = None
    bcc_raw = None
    if "rx_email_cc" in account_settings:
        cc_raw = account_settings["rx_email_cc"]
    if "rx_email_bcc" in account_settings:
        bcc_raw = account_settings["rx_email_bcc"]

    content_body = "Hello, please find attached your eFax."

    msg = MIMEMultipart()
    msg["From"] = header_from
    msg["Subject"] = header_subject
    msg["To"] = to_raw
    if cc_raw is not None:
        msg["Cc"] = cc_raw
    if bcc_raw is not None:
        msg["Bcc"] = bcc_raw
    msg.attach(MIMEText(content_body))
    file_name = pdf_file[pdf_file.rindex("/") + 1 :]
    with open(pdf_file, "rb") as file:
        part = MIMEApplication(file.read(), Name=file_name)
        part["Content-Disposition"] = 'attachment; filename="' + file_name + '"'
        msg.attach(part)
    return common.send_email(msg)
