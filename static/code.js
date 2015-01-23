var editor = ace.edit("editor");
editor.getSession().setMode("ace/mode/python");

// change the syntax language
$("#select-syntax-language").change(function (){
    editor.getSession().setMode($(this).val());      
});



