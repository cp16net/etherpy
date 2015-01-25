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



