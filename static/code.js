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
    payload = {
	"type": "delta_event",
	"data": delta_event
    }
    updater.sendMessage(payload);
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
	var cur = editor.curOp
	if ('name' in cur.command && cur.command.name.indexOf("insert") > -1) {
	    updater.socket.send(JSON.stringify(message));
	}
    },

    showMessage: function(message) {
	editor.getSession().doc.applyDeltas([JSON.parse(message.data)]);
	console.debug("show message: " + message);
    },
};

$(document).ready(function(){
    updater.start();
});
