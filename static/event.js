
(function($) {
    $.QueryString = (function(a) {
        if (a == "") return {};
        var b = {};
        for (var i = 0; i < a.length; ++i)
        {
            var p=a[i].split('=');
            if (p.length != 2) continue;
            b[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
        }
        return b;
    })(window.location.search.substr(1).split('&'))
})(jQuery);

name = $.QueryString["name"];
desc = $.QueryString["desc"];
link = $.QueryString["link"];
start = $.QueryString["start"];

document.write("<div id='name'>");
document.write(name);
document.write("</div><div id='desc'>");
document.write(desc);
document.write("</div><div id='start'>Starts: ");
document.write(start);
document.write("</div>");

if(link.length > 0) {
	document.write("<div id='link'><a href='");
	document.write(link);
	document.write("'>More info on person</a></div>");
}