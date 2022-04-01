function update_html_counters(json_obj) {
    p_in = json_obj.in;
    p_out = json_obj.out;
    p_tot = json_obj.tot;
    if(p_tot <0) { p_tot=0; }
    some_error = json_obj.error;
    $("#person_in").text(p_in);
    $("#person_out").text(p_out);
    $("#person_tot").text(p_tot);

    if(some_error){
        $(".healthval").css('color', 'orange');
        // popupMsg('MU Error', 'Some Monitor unit is missing', 'danger', 5000)
    } else {
        $(".healthval").css('color', 'green');
        // msg = "New update: " + "IN: " + p_in + ", OUT: " + p_out + ", TOT: " + p_tot
        // popupMsg('MU Update', msg, 'success', 5000);
    }

    if(json_obj.tot < 0){
        $(".healthval-tot").css('color', 'orange');
    }
}

function setup_update_receiver() {
    const address = location.hostname
    const websock = new WebSocket("wss://" + address + ":" + ws_port_update + "/");
    websock.addEventListener("message", ({ data }) =>{
        const counts = JSON.parse(data);
        console.log(counts);

        update_html_counters(counts);

    });
    console.log("WEBsocket UPDATES SETUP!")
}
