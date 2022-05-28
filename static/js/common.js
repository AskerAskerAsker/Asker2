var darkbtn = document.getElementById('dark-mode');
var org_title = document.title;

function update_user_badges() {
	var ubadges = document.getElementsByClassName('ubadge');
	for (var i = 0; i < ubadges.length; i++) {
		var badge_val = parseInt(ubadges[i].getAttribute('data-value'));
		if (badge_val) {
			if (badge_val > 10000)
				ubadges[i].style.display = 'inline';
			if (badge_val > 40000)
				ubadges[i].style.color = 'white';
			
			if (badge_val > 500000) {
				// 1m+ (futuramente)
				ubadges[i].style.background = 'linear-gradient(to left, rgb(241, 111, 161), rgb(144, 86, 241))';
			} else if (badge_val > 500000) {
				ubadges[i].style.backgroundColor = '#562491';
			} else if (badge_val > 200000) {
				ubadges[i].style.backgroundColor = '#7330c1';
			} else if (badge_val > 100000) {
				ubadges[i].style.backgroundColor = '#9664d1';
			} else if (badge_val > 40000) {
				ubadges[i].style.backgroundColor = '#9664d1';
			} else if (badge_val > 20000) {
				ubadges[i].style.backgroundColor = '#60e09f';
			} else if (badge_val > 10000) {
				ubadges[i].style.backgroundColor = '#9fecc6';
			}
			
			ubadges[i].innerHTML = badge_val.toLocaleString('pt-BR') + ' pontos';
		}
	}
}

function fix_double_escape(el) {
    /* Em perguntas antigas, o HTML era escapado na descrição e guardado assim na DB.
       Em um servidor novo com uma nova DB esta função poderá ser descartada.
       Ou em algum momento quando a descrição de perguntas antigas for consertada.
       Como só acontecia na entry de descr. de perguntas, apenas nela a função deve ser usada.
    */
    try {
        el.innerText = el.innerText.replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&#x27;', "'").replaceAll('&amp;', '&');
    } catch (e) {
        console.log(e);
    }
}

function get_random_string(length) {
    var str = Math.random().toString(36).slice(2);
    while (str.length < length) {
        str = str + Math.random().toString(36).slice(2);
    }
    return str.slice(str.length - length);
}

function anchor_urls(el) {
    var m = el.innerHTML.matchAll(/(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig);
    var res = el.innerHTML;
    var links = {};
    for (let item of m) {
        var url = item[0];
        var placeholder = get_random_string(url.length);
        var retries = 0;
        while (placeholder in links && retries < 10) {
            placeholder = get_random_string(url.length);
            retries++;
        }
        if (!(placeholder in links)) {
            var a = document.createElement('a');
            a.setAttribute('href', url);
            a.innerHTML = url;
            links[placeholder] = a.outerHTML;
            res = res.replace(url, placeholder);
            a.remove()
        }
    }
    Object.keys(links).forEach(function(k) {
        res = res.replace(k, links[k]);
    });
    el.innerHTML = res;
}

function make_links() {}
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