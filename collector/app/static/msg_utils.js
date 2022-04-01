popupMsg = function(head, msg, kind,timeout=3000){ // kind: success / info / warning / danger
    let d = new Date();
    let id = "popup-msg-" + d.getTime();

    let toast = "<div id=\""+id+"\" class=\"toast bg-dark text-white\" role=\"alert\" aria-live=\"assertive\" aria-atomic=\"true\""
    toast += "data-delay="+timeout+">";
    toast += "<div class=\"toast-header bg-dark text-white\">"
    toast += "<strong class=\"mr-auto bg-dark text-white\">" + head + "</strong>";
    let _timestamp = d.getUTCHours() + ':' + d.getUTCMinutes()
    toast += "<small class=\"text-muted\">" + _timestamp + "</small>";
    toast += "<button type=\"button\" class=\"ml-2 mb-1 close\" data-dismiss=\"toast\" aria-label=\"Close\">"
    toast += "<span aria-hidden=\"true\">&times;</span></button></div>"
    toast += "<div class=\"alert alert-"+kind+"\"style=\"white-space: pre;\">" + msg + "</div></div>"
    $("#toastHook").append(toast);
    console.debug("New popup Appended: " + id);
    console.debug("msg: " + msg);

    $("#"+id).toast("show");

};

function setup_msg_receiver() {
    if (CURRENT_USER.length<3){
        console.log("[setup_msg_receiver()] Current Username not valid: '" + CURRENT_USER + "'");
        return;
    }
    const address = location.hostname
    const websock = new WebSocket("wss://" + address + ":" + ws_port_msg + "/");

    websock.addEventListener("open", (event) =>{
        console.log(CURRENT_USER)
        websock.send(CURRENT_USER)
    });

    websock.addEventListener("message", ({ data }) =>{
        const j_msg = JSON.parse(data);
        console.log(j_msg);

        popupMsg(j_msg.head, j_msg.msg, j_msg.kind, j_msg.timeout );
    });

    websock.addEventListener("close", (event) =>{
        console.log("User: '" + CURRENT_USER + "' close msg_WS");
        console.log(event)
    });

    console.log("WEBsocket MSG SETUP!");
}