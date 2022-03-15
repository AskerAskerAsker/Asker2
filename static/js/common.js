var darkbtn = document.getElementById('dark-mode');
var org_title = document.title;

if (darkbtn != null) {
	darkbtn.addEventListener('click', function() {
	    if (getDarkCookie() == 'true') {
	        setDarkCookie(false);
	        document.getElementById('theme-css').href = '/static/css/' + 'light.css' + cssversion;
	    } else {
	        setDarkCookie(true);
	        document.getElementById('theme-css').href = '/static/css/' + 'dark.css' + cssversion;
	    }
	});
}

async function check_for_notifications() {
    try {
        var notif_badge = document.getElementById('notif-badge');
    } catch (e) {
        return 0;
    }
	$.ajax({
			url: "/new_activity_check",
			type: "get",
			dataType: "json",
			data: {
				last_known_q: 0,
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

function veracity_test(user_points, MINIMUM_POINTS_FOR_POSTING_IMAGES) {
	if (user_points < MINIMUM_POINTS_FOR_POSTING_IMAGES) {
		alert('Você precisa de pelo menos ' + MINIMUM_POINTS_FOR_POSTING_IMAGES + ' Pontos Para Postar Imagens.');
		return false;
	}
	return true;
}