/////////////////////////////////////////////////////////////////////////////
// Copyright (C) 2023, Nexus Polytech Pty Limited. Some rights reserved.
//
// nexuspoly.tech | contact@nexuspoly.tech | GPO Box 1231, SYDNEY NSW 2001
//
// Codebase: NexeFax
//
// License: BSD 3-Clause License
//
// See LICENSE file for more details.
/////////////////////////////////////////////////////////////////////////////

(function(){
$ = function(el){return document.querySelector(el)};

window.nexefax = {}
window.nexefax.web = {
    go_to: function(page){
        this.loading_start();
        document.location = "/" + page;
    },
    api_get_url: function(ep){
        let host = document.location.origin;
        let prefix = "/api/"
        return host + prefix + ep;
    },
    api_post: async function(ep, data){
        let xhr = await fetch(this.api_get_url(ep), {
            method: 'POST',
			headers: {
			  'Accept': 'application/json'
			},
			body: data
		});
		try {
            var jsonObj = JSON.parse(await xhr.text());
		} catch(e) {
            this.toast_show('An error has occured. Try again.');
            return {};
		}
		return jsonObj;
    },
    loading_start: function(){
        $("#loading").classList.remove("hidden");
    },
    loading_stop: function(){
        setTimeout((function(){$("#loading").classList.add("hidden");}), 750);
    },
    toast_show: function(text, type="general"){
        let toastId = Date.now();
        let toastEl = document.createElement("div");
        toastEl.id = "toast-" + toastId;
        toastEl.classList.add("toast");
        toastEl.classList.add(type);
        toastEl.classList.add("show");
        toastEl.innerHTML = "<div class=\"symbol\">!</div><div class=\"desc\">" + text + "</div>";
        document.body.appendChild(toastEl);
        setTimeout(function(){$("#toast-" + toastId).remove(); }, 6000);
    },
    login: async function(){
        let accounttxt = $("#login-account").value;
        if(accounttxt.length == 0){
            $("#login-account").focus();
            return this.toast_show("You must enter your Account.", "warning");
        }
        let usertxt = $("#login-user").value;
        if(usertxt.length == 0){
            $("#login-user").focus();
            return this.toast_show("You must enter your Username.", "warning");
        }
        let passtxt = $("#login-password").value;
        if(passtxt.length == 0){
            $("#login-password").focus();
            return this.toast_show("You must enter your Password.", "warning");
        }

		var postData = new FormData();
		postData.append("account", accounttxt);
		postData.append("user", usertxt);
		postData.append("password", passtxt);

        this.loading_start();
        let login = await this.api_post("login", postData);
        if(login.hasOwnProperty("result") && login.result == "ok"){
            let session_id = login.data;
            this.auth_set(session_id);
            this.go_to("send");
		}else{
            this.loading_stop();
			if(login.result == "error"){
				var errorTxt = login.error + ". " + "Make sure that your login details are correct.";
			}else{
				var errorTxt = "There was a system error. Please try again.";
			}
			this.toast_show(errorTxt, "error");
		}
    },
    auth_set: function(session){
        document.cookie = "nexefax-session="+session;
    },
    auth_status: async function(){
        let status = await this.api_post("status");
        if(status.hasOwnProperty("result") && status.result == "ok"){
            this.loading_stop();
            window.nexefax.status = status.data;
            return true;
		}else{
            return false;
		}
    },
    prepare: async function(){
        this.loading_start();
        let authStatus = await window.nexefax.web.auth_status();
        if(authStatus == false){
            var errorTxt = "There was a system error. Please make sure you are logged in and try again.";
            this.toast_show(errorTxt, "error");
            alert(errorTxt);
            return;
        }
        let tx_line = window.nexefax.status.tx_name + " <" + window.nexefax.status.tx_number + ">";
        $("#send-from").value = tx_line;
        this.loading_stop();
    },
    send: async function(){
      
        let send_to = $("#send-to").value;
        if(send_to.length == 0){
            $("#send-to").focus();
            return this.toast_show("You must enter the recipients details.", "warning");
        }
        let subject = $("#send-subject").value;
        if(subject.length == 0){
            $("#send-subject").focus();
            return this.toast_show("You must enter a subject.", "warning");
        }
        let fax_file = $("#send-faxfile").files;
        if(fax_file.length == 0){
            $("#send-faxfile").focus();
            return this.toast_show("You must upload a PDF to fax.", "warning");
        }
        let file = fax_file[0];
        if(file.type != "application/pdf"){
            $("#send-faxfile").focus();
            return this.toast_show("You can only upload a PDF file.", "error");
        }
        
        const postData = new FormData($("form"));
        this.loading_start();
        let send = await this.api_post("send", postData);
        this.loading_stop();
        if(send.hasOwnProperty("result") && send.result == "ok"){
            this.toast_show("Your fax was sent!", "success");
            this.reset_compose();
		}else{
            this.loading_stop();
			if(send.result == "error"){
				var errorTxt = "An error occured when sending your fax: " + send.error;
			}else{
				var errorTxt = "There was a system error. Please try again.";
			}
			this.toast_show(errorTxt, "error");
        }
    },
    reset_compose: function(){
        $("form").reset();
        let tx_line = window.nexefax.status.tx_name + " <" + window.nexefax.status.tx_number + ">";
        $("#send-from").value = tx_line;
        this.preview_pdf();
    },
    preview_pdf: function(){
        let blobsrc = ""
        let fax_file = $("#send-faxfile").files;
        if(fax_file.length == 1 && fax_file[0].type == "application/pdf"){
            blobsrc = URL.createObjectURL(fax_file[0])
        }
        $("embed").setAttribute("src", blobsrc);
    },
    logout: function(){
        this.go_to("logout");
    },
}
})();