// Jquery function to get URL query parameters
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

// Fetch the event info
function getEvent(id) {
    link = "/query/";
    $.ajax({
        url: link,
        data: {
            id : id
        },
        dataType: "json"
    })
    .done(function(data) {
        renderPage(data);
    })
    .fail(function(data) {
        renderPage(data);
    });
}

// Get HTML for Markdown using server's python module
function parseMarkdown(md, context) {
    link = "/query/";
    $.ajax({
        url: link,
        context : context,
        data : {
            action : "m",
            data : md
        },
        type: "POST",
        dataType: "json"
    })
    .done(function(data) {
        if(data.code == 200) {
            $(this).append(data.data);
        }
    })
    .fail(function(data) {
        if(data.code == 400) {
            $(this).append(md);
        }
    });
}

// Fill in the info on the page after the request
function renderPage(data) {
    if(data.code == 200) {
        parseMarkdown(data.summary, $("#summary"));
        parseMarkdown(data.desc, $("#desc"));

        //Handle start time
        date = new Date(Date.parse(data.start.dateTime));
        $("#start").append("Starts on: " + date);
        
        var ts_id = countdown(date, 
            function(ts) { 
                str = "Starts in: <strong>" + ts.days + "d " + ts.hours + ":" + ts.minutes + ":" + ts.seconds + "</strong>";
                $("#countdown").html(str);
            },
            countdown.DAYS|countdown.HOURS|countdown.MINUTES|countdown.SECONDS);
    }
    else if(data.code == 404) {
        document.write("Event not found.");
    }
}


id = $.QueryString["id"];

if(id) {
    getEvent(id);
} else {
    document.write("No event id specified.");
}