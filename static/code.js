var editor = ace.edit("editor");
editor.getSession().setMode("ace/mode/python");
editor.setTheme("ace/theme/monokai");

// change the syntax language
$("#select-syntax-language").change(function (){
    editor.getSession().setMode($(this).val());      
});

// change the theme
$("#select-theme").change(function (){
    editor.setTheme($(this).val());
});

editor.getSession().on('change', function(e) {
    var change_event = {
	"start": {
	    "row": e.data.range.start.row,
	    "column": e.data.range.start.column,
	},
	"end": {
	    "row": e.data.range.end.row,
	    "column": e.data.range.end.column,
	},
	"action": e.data.action,
	"text": e.data.text,
    }
//    alert(JSON.stringify(change_event));
    updater.sendMessage(change_event);
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
	updater.socket.send(JSON.stringify(message));
    },

    showMessage: function(message) {
	console.debug("show message: " + message);
    },
};

$(document).ready(function(){
    updater.start();
});
