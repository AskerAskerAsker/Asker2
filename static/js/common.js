var darkbtn = document.getElementById('dark-mode');
var org_title = document.title;
darkbtn.addEventListener('click', function() {
    if (getDarkCookie() == 'true') {
        setDarkCookie(false);
        document.getElementById('theme-css').href = '/static/css/' + 'light.css' + cssversion;
    } else {
        setDarkCookie(true);
        document.getElementById('theme-css').href = '/static/css/' + 'dark.css' + cssversion;
    }
});

async function check_for_notifications() {
    try {
        var notif_badge = document.getElementById('notif-badge');
    } catch (e) {
        return 0;
    }
	$.ajax({
			url: "/update_index_check",
			type: "get",
			dataType: "json",
			data: {
				last_known_q: 999999,
			},
			complete: function(data) {
                new_notifications = data.responseJSON['nn'];
                if (notif_badge) {
                    if (new_notifications > 0) {
                        notif_badge.innerHTML = new_notifications;
                        notif_badge.style.display = 'block';
                        document.title = "(" + new_notifications + ") " + org_title;
                    } else {
                        notif_badge.style.display = 'none';
                        document.title = org_title;
                    }
                }

			},
	});    
}
