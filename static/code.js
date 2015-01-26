var editor = ace.edit("editor");
editor.getSession().setMode("ace/mode/python");
editor.setTheme("ace/theme/monokai");
editor.$blockScrolling = Infinity

// change the syntax language
$("#select-syntax-language").change(function (){
    editor.getSession().setMode($(this).val());      
});

// change the theme
$("#select-theme").change(function (){
    editor.setTheme($(this).val());
});

var send_change_event = true;
editor.getSession().on('change', function(e) {
    var delta_event = {
	"range": e.data.range,
	"action": e.data.action,
    }
    if (e.data.action.indexOf("Lines") > -1) {
	delta_event.lines = e.data.lines;
    }
    else if (e.data.action.indexOf("Text") > -1) {
	delta_event.text = e.data.text;
    }
    updater.sendMessage(delta_event);
});

var updater = {
    socket: null,

    start: function() {
	console.debug("starting up");
	var url = "ws://" + location.host + "/codesocket";
	updater.socket = new WebSocket(url);
	updater.socket.onmessage = updater.showMessage;
    },

    sendMessage: function(message) {
	console.debug("sending data: " + message);
	if (send_change_event) {
	    updater.socket.send(JSON.stringify(message));
	}
	else{
	    send_change_event = true;
	}
    },

    showMessage: function(message) {
	send_change_event = false;
	editor.getSession().doc.applyDeltas([JSON.parse(message.data)]);
	console.debug("show message: " + message);
    },
};

$(document).ready(function(){
    updater.start();
});
