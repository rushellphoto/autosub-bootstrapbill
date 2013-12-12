// Javascript for test buttons used from Sickbeard source, Thanks. Project can be found here: https://github.com/midgetspy/Sick-Beard

$(document).ready(function () {

    $('#testMail').click(function () {
        $('#testMail-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Mail...</span>');
        var mailsrv = $("#mailsrv").val();
		var mailfromaddr = $("#mailfromaddr").val();
		var mailtoaddr = $("#mailtoaddr").val();
		var mailusername = $("#mailusername").val();
		var mailpassword = $("#mailpassword").val();
		var mailsubject = $("#mailsubject").val();
		var mailencryption = $("#mailencryption").val();
		var mailauth = $("#mailauth").val();
		$.get(autosubRoot + "/config/testMail", {'mailsrv': mailsrv, 'mailfromaddr': mailfromaddr, 'mailtoaddr': mailtoaddr, 'mailusername': mailusername, 'mailpassword': mailpassword, 'mailsubject': mailsubject, 'mailencryption': mailencryption, 'mailauth': mailauth},
			function (data) { $('#testMail-result').html(data); });
    });

    $('#testTwitter').click(function () {
        $('#testTwitter-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Twitter...</span>');
        var twitterkey = $("#twitterkey").val();
		var twittersecret = $("#twittersecret").val();
		$.get(autosubRoot + "/config/testTwitter", {'twitterkey': twitterkey, 'twittersecret': twittersecret},
			function (data) { $('#testTwitter-result').html(data); });
    });
    
    $('#testPushalot').click(function () {
        $('#testPushalot-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Pushalot...</span>');
        var pushalotapi = $("#pushalotapi").val();
		$.get(autosubRoot + "/config/testPushalot", {'pushalotapi': pushalotapi},
			function (data) { $('#testPushalot-result').html(data); });
    });
	
	$('#testNotifyMyAndroid').click(function () {
        $('#testNotifyMyAndroid-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Notify My Android...</span>');
        var nmaapi = $("#nmaapi").val();
		var nmapriority = $("#nmapriority").val();
		$.get(autosubRoot + "/config/testNotifyMyAndroid", {'nmaapi': nmaapi, 'nmapriority': nmapriority},
			function (data) { $('#testNotifyMyAndroid-result').html(data); });
    });
	
	$('#testPushover').click(function () {
        $('#testPushover-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Pushover...</span>');
        var pushoverapi = $("#pushoverapi").val();
		$.get(autosubRoot + "/config/testPushover", {'pushoverapi': pushoverapi},
			function (data) { $('#testPushover-result').html(data); });
    });
	
	$('#testGrowl').click(function () {
        $('#testGrowl-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Growl...</span>');
        var growlhost = $("#growlhost").val();
		var growlport = $("#growlport").val();
		var growlpass = $("#growlpass").val();
		$.get(autosubRoot + "/config/testGrowl", {'growlhost': growlhost, 'growlport': growlport, 'growlpass': growlpass},
			function (data) { $('#testGrowl-result').html(data); });
    });
	
	$('#testProwl').click(function () {
        $('#testProwl-result').html('<span><img src="' + autosubRoot + '/images/loading16.gif"> Testing Prowl...</span>');
        var prowlapi = $("#prowlapi").val();
		var prowlpriority = $("#prowlpriority").val();
		$.get(autosubRoot + "/config/testProwl", {'prowlapi': prowlapi, 'prowlpriority': prowlpriority},
			function (data) { $('#testProwl-result').html(data); });
    });
	
	// Code to display the tooltip on the configuration page.
	$("a").tooltip()
	
	// Code to hide/show the notification fields.
	$(".enabler option:selected").each(function () {
		if ($(this).val() == "False") {
			$('#content_' + $(this).parent().attr("id")).hide();
		}
	});

	$(".enabler").change(function () {
 		var dropdown = $(this);
		$(this).children("option:selected").each(function() {
 			if ($(this).val() == "True") {
 				$('#content_' + dropdown.attr("id")).show();
 			}
 			if ($(this).val() == "False") {
 				$('#content_' + dropdown.attr("id")).hide();
 			}
 		});
 	});

	$('#advanced-config').each(function () {
		$('#content_advanced').hide();
		$('#adv-conf-up').hide();
	});
	
	$('#advanced-config').click(function() {
		$('#content_advanced').toggle();
		$('#adv-conf-up').toggle();
		$('#adv-conf-down').toggle();
	});
});

// Code to sort the Wanted/Downloaded tables on the Home page.
var lines = $(".overview");
var elems = $(".overview div");
var numElems = elems.length;
for (var index = 1; index <= elems.length; index++) {
	var elemId = "Display" + index;
	var containerIndex = parseInt((index - 1) / 4);
	var container = lines[containerIndex];
	var elem = document.getElementById(elemId);
	elem.parentNode.removeChild(elem);
	container.appendChild(elem);
}
