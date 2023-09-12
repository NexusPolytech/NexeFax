
<img src="https://github.com/NexusPolytech/NexeFax/blob/c9cdb2d8638443724a33a7ac138a61a2569b1288/modules/nexefax/Http_server/web/res/img/logoh.png" width="300px">

![Python](https://img.shields.io/badge/Language-Python3-yellow) ![Status](https://img.shields.io/badge/Status-BETA-red) ![Ver](https://img.shields.io/badge/Version-0.0.1-blue)

An open source eFax server solution written in Python that allows sending and receiving faxes via integration with Asterisk PBX, with support for multiple accounts each with their own users and details.

🔴 **IMPORTANT**: This project is still in BETA. It is a highly functional and working beta but you should expect some bugs. Please report all issues using the Issues tab.

## About & Why
Fax... in 2023.... really? Yes, really. While nowhere near as prevalent as they once were, fax machines are still used in 2023 due to faxes continued prevalence within key industries and some countries.

While there are a range of commercial solutions available in the form of fax servers and fax services , most open source implementations for fax were almost a decade old (if not older) and used outdated practices and outdated technology. 

NexeFax is a complete reimplementation of eFax using current practices the latest versions of software, built fully with the same open source spirit as other 

Some of the key features of NexeFax include:
* Multiple Fax Accounts
* Web UI interface to easily send faxes
* Each Fax Account can have multiple users for web UI access
* Inbuilt FastAGI server for Asterisk
* Very low memory footprint (<15Mb)

### Screenshots
**Login**

<img src="https://github.com/NexusPolytech/NexeFax/assets/1935851/821a2b81-89b6-48f9-96e6-e6a9ed2f4639" width="500px">

**Compose**

<img src="https://github.com/NexusPolytech/NexeFax/assets/1935851/3e1bde62-85f0-4477-837d-e9f72b119a7c" width="500px">

## How it works
NexeFax has 3 main components, it's inbuilt FastAGI server which receives events from Asterisk (such as when a Fax is received or after one is sent), it's inbuilt HTTP server which enables a web UI for users to send faxes, and it's inbuilt eFax server which handles the processing of PDF and TIFF files.

_Recieving Faxes_

Faxes are received by Asterisk and stored as a TIFF file. An AGI request is then made to NexeFax to start processing all received faxes. NexeFax parses the directory where Asterisk has stored the TIFF Fax files, converts them to PDF, processes and emails them accordingly.

_Sending Faxes_

Users send faxes using the web UI. The request is received by the inbuilt HTTP server which passes it along to the eFax server. The eFax server converts the PDF file to a TIFF file and creates an Asterisk call file using the dedicated *send* extension in the [nexefax] dialplan context.

# Installation
NexeFax is simple to install and run but you must read these installation instructions in full to understand how it works.

## Installing Dependencies
NexeFax depends on the following:
* Asterisk 16+ PBX
* res_fax (for Asterisk)
* Python 3.10+
* python_bcrypt (needed for dealing with user authentication)
* Imagemagick (to convert Fax TIFF files to PDF files)
* Ghostscript (to convert PDF files to Fax TIFF files)
* apache2-utils (needed for htpasswd to interact with auth files)

On a Debian/Ubuntu based Linux system run the following:
```
apt-get install python3 python3-bcrypt imagemagick ghostscript
```
Note that this does not deal with the installation of Asterisk or res_fax. These must be installed separately.

## Installing NexeFax Server
Extract the NexeFax server files to /usr/lib/nexefax.
```
cd /tmp
wget https://github.com/NexusPolytech/NexeFax/archive/refs/tags/v0.0.1.tar.gz
tar -xf v0.0.1.tar.gz
cp -r /tmp/NexeFax-0.0.1/ /usr/lib/nexefax
```

## Integration with Asterisk Dialplan
Add the [nexefax] context from the dialplans/asterisk/extensions.conf file into your Asterisk dialplan.

When you want to receive  a fax, your Dialplan must go to the *receive* extension of the [nexefax] context. You need to pass the Fax Account ID as the first argument.

In the below example, this is the *fax* extension for our context for ACME Corporation, which has been setup with the NexeFax account ID ACME.
```
exten => fax,1,Gosub(nexefax,receive,1(ACME))
```

# Running & Controlling NexeFax Server
NexeFax is a standalone Python server and should be run as a daemon or service.

## Using systemd for Debian/Ubuntu
On Debian/Ubuntu based systems, you can run and control NexeFax using a systemd service file.
```
cp /usr/lib/nexefax/control/systemd/nexefax.service /etc/systemd/system/nexefax.service
systemctl daemon-reload
```

Once the service file has been copied and the systemctl has been reloaded, you can run NexeFax using:
```
systemctl start nexefax
or
service nexefax start
```

## Using a HTTPS Reverse Proxy
The inbuilt HTTP server for NexeFax web UI does not support HTTPS. It is best practice to ensure that you use a reverse proxy server, such as Nginx or Apache, to securely provide NexeFax's web UI on a public facing interface.

A sample server configuration file for Nginx is included in the /usr/lib/nexefax/http-samples directory.


## Configuring NexeFax
NexeFax is configured with three types of files stored in /etx/nexefax:

1. **config.conf**: This is the main configuration files that controls NexeFax.
   
2. **accounts.conf**: This is the accounts file the creates the fax accounts that can send and receive faxes.

3. **auth files**: These are htpasswd files that must be created for each account that has been configured which contain the username and passwords for the users who can sign in and send faxes from that account.

Create the accounts.conf and config.conf files in /etc/nexefax. You can copy samples of these files from the conf-samples folder.
```
mkdir /etc/nexefax/
cp -r /usr/lib/nexefax/conf-samples/* /etc/nexefax/
```


__config.conf__

The following options can be configured in config.conf and effect all of NexeFax.

|Section | Option | Purpose | Required | Options | Default |
| -------- | ------ | ------- | -------- | ------- | ------- |
| general | tx_channel | The Asterisk channel that will originated to send a fax. This must contain the string **${TO}** which will be replaced with the recipient fax number.| **Yes** |  | |
| general | rx_dir | The directory that recieved fax TIFF files are stored in. | |  | /var/spool/asterisk/tmp |
| general | ast_call_dir | The directory that Asterisk call files will be placed. | |  | /var/spool/asterisk/outgoing |
| general | tmp_dir | The tmp directory for NexeFax temp files. | |  | /tmp/nexefax |
| general | ast_context | The Asterisk dialplan context for NexeFax. | |  | nexefax |
| general | tx_max_retries | Number of time Asterisk should attempt to make the call before failing attempt. | |  | 5 |
| general | tx_retry_time | Number of seconds Asterisk should wait between retries. | |  | 300 |
| general | tx_wait_time | Number of seconds Asterisk should wait for an answer. | |  | 30 |
| general | tx_faxopt_ecm | Set the Asterisk FAXOPT item 'ecm'. | |  | Yes |
| general | tx_faxopt_modem | Set the Asterisk FAXOPT item 'modem'. | |  | v17,v27,v29 |
| general | tx_faxopt_faxdetect | Set the Asterisk FAXOPT item 'faxdetect'. | |  | |
| general | tx_faxopt_minrate | Set the Asterisk FAXOPT item 'minrate'. | |  | 4800 |
| general | tx_faxopt_maxrate | Set the Asterisk FAXOPT item 'maxrate'. | |  | 14400 |
| general | tx_faxopt_t38timeout | Set the Asterisk FAXOPT item 't38timeout'. | |  | 5000 |
| general | tx_faxopt_negboth | Set the Asterisk FAXOPT item 'negotiate_both'. | |  | |
| logging | file | Set the NexeFax log file. | |  | /var/log/nexefax/info.log |
| logging | debug | Enable debug mode. | | Yes or No | /var/log/nexefax/info.log |
| server | bind | The IP address to bind on. | | 0.0.0.0 for every IP address or a specific IP address | 0.0.0.0 |
| server | port_fagi | The port the FastAGI server should listen on. | |  | 4573 |
| server | port_http | The port the HTTP server should listen on. | |  | 3298 |
| server | web_session_length | How long in seconds an authenticated web users session should last. | |  | 86400 |
| email | method | How email should be sent. | | sendmail or smtp | sendmail |
| email | smtp_mode | If [email] method is smtp, the connection mode for the SMTP connection. | | tls for STARTTLS, ssl for SSL, leave blank for nothing |  |
| email | smtp_port | If [email] method is smtp, the port for the SMTP connection. | | | 25 |
| email | smtp_auth | If [email] method is smtp, if authentication is needed for this connection. | | Yes or No | |
| email | smtp_host | If [email] method is smtp, the SMTP host to connect to. | | IP or FQDN | 127.0.0.1 |
| email | smtp_auth_user | If [email] smtp_auth is Yes, the auth user. | |  | |
| email | smtp_auth_pass | If [email] smtp_auth is Yes, the auth password. | |  | |
| email | from_name | The name emails should be sent from. | |  | NexeFax |
| email | from_email | The address emails should be sent from. | |  | nexefax@**your local host name** |
| email | subject | The subject that should be used for new faxes recieved. | |  | nexefax@**your local host name** |



__accounts.conf__

The section name for an account is it's account ID and is used to identify that account and to sign in to that account in the Web UI.
```
[ACME]
info_name=ACME Corporation
info_fax=202 555 0154
info_phone=202 555 0103
info_email=contact@acme.corp
info_web=www.acme.corp
```
In the above example, the account ID is ACME

The following options can be configured for each account in accounts.conf and effect that specific account.
| Option | Purpose | Required | Options | Default |
| -------- | ------ | ------- | -------- | ------- |
| rx_email_to | The email address(es) that Faxes will be sent to. | **Yes** | Can be a single email address of multiple email addresses seperated by a comma (,) |  |
| rx_email_cc | The email address(es) that Faxes will be CC'd to. | | Can be a single email address of multiple email addresses seperated by a comma (,) |  |
| rx_email_subject | The subject for new eFax emails. | |  | The default set in the [email] subject option in config.ini |
| tx_number | The number (inclding country and area code) faxes will be sent from, with no symbols or letters. | **Yes** |  | |
| tx_name | The name of the entity sending the faxes. | |  | |
| tx_notify_success | Send an email when a fax from this account was sent successfully. | | True or False | False |
| tx_notify_failure | Send an email when a fax from this account failed to send. | | True or False | True |
| tx_channel | Override the TX channel for this account. | | | |

The following options can be configured to provide information for the sending entity. They are not used yet but will be used in future versions.
| Option | Purpose | Required | Options | Default |
| -------- | ------ | ------- | -------- | ------- |
| info_name | Information about the sending entity: Name | |  | |
| info_fax | Information about the sending entity: Fax Number | No |  | |
| info_phone | Information about the sending entity: Phone | No |  | |
| info_email | Information about the sending entity: Email Address | No |  | |
| info_web | Information about the sending entity: Website | No |  | |



__Auth Files__

Auth files htpasswd files which are stored inside /etx/nexefax/auth. They are used to allow access to the web UI.

You must setup an auth file for each account you have created in accounts.conf.

In the below example we will be creating a user named **bob.smith** within the ACME account auth file.
```
htpasswd -B -c /etc/nexefax/auth/ACME bob.smith

New password: MyStrongPassword123
Re-type new password: MyStrongPassword123
Adding password for user bob.smith
```

You can use the exact same command as above with an existing user to change their password.
