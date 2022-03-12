var success_str = 'kfO1wMuva3hNgh0AhIviPyhEGyoRjDdX';
var should_hide = false;
var org_title = document.title;

function hide_questions() {
    qtitles = document.getElementsByClassName('q-title');
    for (var i = 0; i < qtitles.length; i++) {
        var qid = qtitles[i].href.slice(qtitles[i].href.lastIndexOf('/')+1);

        if (qid != 'javascript:void(0);') {
            var total_responses = document.getElementById('response-counter-' + qid).innerHTML;
            if (Number(total_responses) < 12) {
                qtitles[i].href = 'javascript:void(0);'
                qtitles[i].setAttribute('onclick', 'login_toggle();');
            }
        }
    }
}

function login_toggle() {
    var popup_bg = document.getElementById('popup-bg');
    if (popup_bg.style.display == 'none') {
        popup_bg.style.display = 'block';
        document.getElementById('new-user-pp-container').style.display = 'block';
        document.body.style.overflow = 'hidden';
    } else {
        popup_bg.style.display = 'none';
        document.getElementById('new-user-pp-container').style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function image_toggle(el) {
    var ovf_guide = el.getElementsByClassName('overflow-guide')[0];
    var img_off = el.getElementsByClassName('index-qimg-off');
    if (img_off.length > 0) {
        ovf_guide.style.opacity = 0;
        img_off[0].className = 'index-qimg-on';
    } else {
        el.getElementsByClassName('index-qimg-on')[0].className = 'index-qimg-off';
        if (!(el.scrollHeight > el.clientHeight)) {
            el.getElementsByClassName('overflow-guide')[0].style.opacity = 100;
            el.scrollIntoView();
        }
    }
}

function activate_img_btns() {
    let btns = document.getElementsByClassName('index-qimg-btn');
    for (var i = 0; i < btns.length; i++) {
        var el = btns[i];
        var el_img = el.getElementsByClassName('index-qimg-off')[0].children[0];

        el_img.onload = function(e) {
            btn_el = e.currentTarget.parentNode.parentNode;
            if (!(btn_el.scrollHeight > btn_el.clientHeight)) {
                btn_el.getElementsByClassName('overflow-guide')[0].style.opacity = 100;
            }
        }
    }
}

function enviar_resposta_pergunta(form) {
	form.style.opacity = 0.5;
	form.submit_btn.disabled = true;

	$.ajax({
		url: '/save_answer',
		type: 'post',
		data: $(form).serialize(),
		complete: function(data) {
			var response_counter = document.getElementById('response-counter-' + form.question_id.value);
			response_counter.innerText = Number(response_counter.innerText) + 1;

            if (response_counter.innerText == '1') {
                document.getElementById('response-sentence-' + form.question_id.value).innerText = 'Resposta';
            } else {
                document.getElementById('response-sentence-' + form.question_id.value).innerText = 'Respostas';
            }

			form.parentElement.innerHTML = data.responseText;
		},
	});
	return false;
}

var botao_popular = document.getElementById("botao-popular");
var botao_recentes = document.getElementById("botao-recentes");
var botao_seguindo = document.getElementById("botao-seguindo");

var questoes_recentes = document.getElementById("lista_de_questoes_recentes");
var questoes_populares = document.getElementById("lista_de_questoes_populares");

// Renderiza as questões populares
function renderizar_questoes_populares(popular_questions) {
    for (var index = 0; index < 20; ++index) {
    try { questoes_populares.innerHTML += '<li class="list-group-item bg-main questao" data-id="'+popular_questions[index].id+'">' +
												'<div class="card-body" style="border: none;">' +
													'<div class="profile-picture-index"><div class="profile-pic-small" style="background:url(\'' + popular_questions[index].question_creator_avatar + '\');"></div> <span class="qcreator-small">' + popular_questions[index].creator + '</span></div>' +
													'<div class="flexbox" style="border: none; background: transparent">' +
														'<h2 style="font-size: 16px" class="question-title fg-1">' +
															'<a style="text-decoration: none; outline: none" class="q-title" href="/question/'+popular_questions[index].id+'">' +
																popular_questions[index].text +
															'</a>' +
														'</h2>' +
													'</div>' +
													(popular_questions[index].description != '' ? '<p class="description">'+popular_questions[index].description+'</p>' : '') +
									   '<small class="text-muted" style="color: #40E0D0">' +
															(popular_questions[index].total_answers == 1 ? '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">1</span> <span style="color: #00CD66; font-weight: 800" id="response-sentence-'+popular_questions[index].id+'">Resposta</span>' : '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">'+popular_questions[index].total_answers+'</span> <span style="color: #00CD66" id="response-sentence-'+popular_questions[index].id+'">Respostas</span>') + ' | ' + popular_questions[index].pub_date +
														'</small>' +

											'</li>'; } catch (e) {
											}
    }
}
renderizar_questoes_populares(popular_questions_);

if (mostrar_primeiro == 'popular') {
    document.getElementById("feed").style.display = "none";
	document.getElementById('novas_questoes').style.display = 'none';
	document.getElementById('questoes_populares').style.display = 'block';
	document.getElementById('botao-popular').style.fontWeight = 'bold';
} else if (mostrar_primeiro == 'feed') {
    document.getElementById("feed").style.display = "block";
	document.getElementById('novas_questoes').style.display = 'none';
	document.getElementById('questoes_populares').style.display = 'none';
	document.getElementById('botao-seguindo').style.fontWeight = 'bold';
} else {
    document.getElementById("feed").style.display = "none";
	document.getElementById('novas_questoes').style.display = 'block';
	document.getElementById('questoes_populares').style.display = 'none';
	document.getElementById('botao-recentes').style.fontWeight = 'bold';
}

document.getElementsByTagName('body')[0].style.display = 'block';

var recent_exists = false;
function load_more_recent() {
    button = document.getElementById('load-more-recent-btn');
    icon = button.nextElementSibling;
	button.style.display = 'none';
	icon.style.display = 'block';
    if (recent_exists) {
        var id_de_inicio = document.getElementById("novas_questoes").getElementsByClassName("list-group-item")[document.getElementById("novas_questoes").getElementsByClassName("list-group-item").length - 1].getAttribute("data-id") - 1;
    } else {
        var id_de_inicio = 0;
    }
	$.ajax({
			url: "/more_questions",
			type: "get",
			dataType: "html",
			data: {
				id_de_inicio: id_de_inicio,
			},
			complete: function(data) {
                if (data.responseText == '-1') {
                    icon.style.display = 'none';
                    button.style.display = 'none';
                    document.getElementById('novas_questoes').innerHTML += '<div class="end"><p>Fim! <i class="far fa-sad-cry" aria-hidden="true"></i></p></div>'
                } else if (data.responseText.includes(success_str)) {
                    icon.style.display = 'none';
                    button.style.display = 'block';
                    q_list = document.getElementById('lista_de_questoes_recentes');
                    q_list.innerHTML += data.responseText;
                let descriptions = document.getElementsByClassName('description');
				for (let i in descriptions) {
					try {
						descriptions[i].innerText = descriptions[i].innerText.replaceAll('&quot;', '"');
					} catch {}
				}
                recent_exists = true;
                }
				icon.style.display = 'none';
				button.style.display = 'block';
                activate_img_btns();
                if (should_hide) {
                    hide_questions();
                }
			},
	});
}

function open_popular() {
    botao_popular.style.fontWeight = '900';
    botao_recentes.style.fontWeight = '400';
    botao_seguindo.style.fontWeight = '400';
    document.getElementById("questoes_populares").style.display = "block";
    document.getElementById("novas_questoes").style.display = "none";
    document.getElementById("feed").style.display = "none";
    window.history.replaceState("object or string", "Title", "/");
	document.body.scrollTop = document.documentElement.scrollTop = 0;
}
function open_recent() {
    botao_popular.style.fontWeight = '400';
    botao_recentes.style.fontWeight = '900';
    botao_seguindo.style.fontWeight = '400';
    document.getElementById("questoes_populares").style.display = "none";
    document.getElementById("novas_questoes").style.display = "block";
    document.getElementById("feed").style.display = "none";
    window.history.replaceState("object or string", "Title", "/news");
    if (!recent_exists) { load_more_recent(); }
	document.body.scrollTop = document.documentElement.scrollTop = 0;
}
function open_feed() {
    botao_popular.style.fontWeight = '400';
    botao_recentes.style.fontWeight = '400';
    botao_seguindo.style.fontWeight = '900';
    document.getElementById("questoes_populares").style.display = "none";
    document.getElementById("novas_questoes").style.display = "none";
    document.getElementById("feed").style.display = "block";
    window.history.replaceState("object or string", "Title", "/feed");
    if (feed_page == 1 && feed_sp == 0) { load_more_feed(); }
	document.body.scrollTop = document.documentElement.scrollTop = 0;
}
botao_popular.onclick = open_popular;
botao_recentes.onclick = open_recent;
botao_seguindo.onclick = open_feed;

function update_recent() {
    var last_known_q = document.getElementById("novas_questoes").getElementsByClassName("list-group-item")[0].getAttribute("data-id");
    var button = document.getElementById('new-q-btn');
    var icon = document.getElementById('top-spinner');
	button.style.display = 'none';
	icon.style.display = 'none';
	open_recent();
	$.ajax({
			url: "/update_index",
			type: "get",
			dataType: "html",
			data: {
				last_known_q: last_known_q,
			},
			complete: function(data) {
                if (data.responseText == '-1') {
                    icon.style.display = 'none';
                } else if (data.responseText.includes(success_str)) {
                    q_list = document.getElementById('lista_de_questoes_recentes');
                    q_list.innerHTML = data.responseText + q_list.innerHTML;
                    window.scrollTo(0, 0);
                }
                icon.style.display = 'none';
                activate_img_btns();
                if (should_hide) {
                    hide_questions();
                }
			},
	});
}

var UPD_INTERVAL = 0;
async function check_for_update() {
    try {
        var last_known_q = document.getElementById("novas_questoes").getElementsByClassName("list-group-item")[0].getAttribute("data-id");
        var notif_badge = document.getElementById('notif-badge');
    } catch (e) {
        var last_known_q = -1;
		var notif_badge = null;
    }
	var button = document.getElementById('new-q-btn');
	var btn_count = document.getElementById('new-q-count');
	$.ajax({
			url: "/update_index_check",
			type: "get",
			dataType: "json",
			data: {
				last_known_q: last_known_q,
			},
			complete: function(data) {

                new_notifications = data.responseJSON['nn'];
                new_questions = data.responseJSON['nq'];

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
				if (new_questions == -1) {
                    button.getElementsByTagName('button')[0].removeAttribute('onclick');
                    button.onclick = function(e) {
						open_recent();
						var button = document.getElementById('new-q-btn');
						button.onclick = update_recent;
						button.style.display = 'none';
					};
                    button.style.display = 'table';
                    btn_count.innerHTML = 'Ver';
				} else if (new_questions > 29) {
                    button.getElementsByTagName('button')[0].removeAttribute('onclick');
                    button.addEventListener('click', function(e) { location.reload(); });
                    button.style.display = 'table';
                    btn_count.innerHTML = '30+';
                    clearInterval(UPD_INTERVAL);
                } else if (new_questions > 0) {
                    button.style.display = 'table';
                    btn_count.innerHTML = new_questions;
                }
			},
	});
}
UPD_INTERVAL = setInterval(check_for_update, 35000);

function load_more_popular(button, icon, page) {

	button.style.display = 'none';
	icon.style.display = 'block';
	$.ajax({
			url: "/more_popular_questions",
			type: "get",
			dataType: "json",
			data: {
					page: page,
			},
			complete: function(data) {

                try {
                    if (data.responseJSON.empty == 'true') {
                        icon.style.display = 'none';
                        button.style.display = 'none';
                        document.getElementById('questoes_populares').innerHTML += '<div class="end"><p>Fim! <i class="far fa-sad-cry" aria-hidden="true"></i> Veja as <a href="/news">perguntas recentes.</a></p></div>'
                    } else {
                        icon.style.display = 'none';
                        button.style.display = 'block';
                        renderizar_questoes_populares(data.responseJSON);
                        if (should_hide) {
                            hide_questions();
                        }
                    }
                } catch (e) {
                    console.log(e);
                }
			},
	});
}

feed_page = 1;
feed_sp = 0;
function load_more_feed() {
    button = document.getElementById('load-more-feed-btn');
    icon = button.nextElementSibling;
	button.style.display = 'none';
	icon.style.display = 'block';
	$.ajax({
			url: "/get_index_feed_page",
			type: "get",
			dataType: "html",
			data: {
					page: feed_page,
                    sp: feed_sp,
			},
			complete: function(data) {
                if (data.responseText == '0') {
                    feed_page += 1;
                    feed_sp = 0;
                    load_more_feed(button, icon)
                } else if (data.responseText == '-1') {
                    icon.style.display = 'none';
                    button.style.display = 'none';
                    document.getElementById('feed').innerHTML += '<div class="end"><p>Fim! <i class="far fa-sad-cry" aria-hidden="true"></i><br>Você ainda pode responder às <a href="/news">perguntas recentes.</a></p></div>'
                } else {
                    icon.style.display = 'none';
                    button.style.display = 'block';
                    feedlist = document.getElementById('feed_list');
                    feedlist.innerHTML += data.responseText;
                    feed_sp += 1;
                }
			},
	});
}

/* Desativa o botão de responder para quem não confirmou o e-mail. */
if (typeof conta_ativa !== 'undefined') {
	if (!conta_ativa) {
	    var botoes_responder = document.getElementsByClassName('botao_responder');
	    for (var i = 0; i < botoes_responder.length; ++i) {
	        botoes_responder[i].onclick = function () {
	            alert('Confirme Sua Conta Pelo e-mail Enviado Para Responder Perguntas.');
	            return 0;
	        };
	    }
	}
}

function star_question(el, qid) {
	$.ajax({
		url: "/question/star",
		type: "get",
		dataType: "html",
		data: {
			qid: qid,
		},
		complete: function(data) {
			var total_stars = parseInt(data.responseText);
			if (total_stars || total_stars == 0) {
				el.getElementsByClassName('starcount')[0].innerHTML = total_stars;
				var off = el.getElementsByClassName('offstar')[0];
				var on = el.getElementsByClassName('onstar')[0];
				if (el.getElementsByClassName('offstar')[0]['classList'].contains('hidden')) {
					//off['classList'].remove('hidden');
					//on['classList'].add('hidden');
				} else {
					off['classList'].add('hidden');
					on['classList'].remove('hidden');
				}
			}
		}
	});
}

function prepare_video(el) {
	var vid = el.getElementsByClassName('qvid-file')[0];
	var bar = el.getElementsByClassName('qvid-bar')[0];
	var prog = el.getElementsByClassName('qvid-prog')[0];
	var play = el.getElementsByClassName('qvplay')[0];
	var pause = el.getElementsByClassName('qvpause')[0];
	var mt = el.getElementsByClassName('qvmt')[0];
	var unmt = el.getElementsByClassName('qvunmt')[0];
	var expand = el.getElementsByClassName('qvexpand')[0];
	var curr_time = el.getElementsByClassName('qvctime')[0];
	var total_time = el.getElementsByClassName('qvttltime')[0];
	var controls = el.getElementsByClassName('qvid-controls')[0];

	var fullscreen = vid.webkitRequestFullscreen || vid.mozRequestFullScreen || vid.msRequestFullscreen;

	function toggleplay() {
		if (vid.paused) {
			vid.play();
			play['classList'].add('hidden');
			pause['classList'].remove('hidden');
		} else {
			vid.pause();
			play['classList'].remove('hidden');
			pause['classList'].add('hidden');
		}
	}

	play.onclick = toggleplay;
	pause.onclick = toggleplay;
	vid.onclick = function() {
		if (controls.style.height == '0px') {
			controls.style.height = '42px';
		} else {
			controls.style.height = '0px';
			toggleplay();
		}
	};
	el.onmouseenter = function() {
		controls.style.height = '42px';
	};
	el.onmouseleave = function() {
		controls.style.height = '0px';
	};

	mt.onclick = function() {
		vid.muted = false;
		mt['classList'].add('hidden');
		unmt['classList'].remove('hidden');
	};
	unmt.onclick = function() {
		vid.muted = true;
		mt['classList'].remove('hidden');
		unmt['classList'].add('hidden');
	};

	expand.onclick = function() {
		fullscreen.call(vid);
	};

	var dur = Math.floor(vid.duration)
	total_time.innerHTML = (dur-(dur%=60))/60+(9<dur?':':':0')+dur
	
	bar.addEventListener('click', function(e) {
		var x = e.pageX;
		var min = this.getBoundingClientRect().left;
		var tot = this.offsetWidth;
		var pct = (x-min)/tot;
		vid.currentTime = pct * vid.duration;
	});

	vid.addEventListener('timeupdate', function() {
		var vidprog = vid.currentTime / vid.duration;
		var ct = Math.floor(vid.currentTime);
		prog.style.width = vidprog * 100 + '%';
		curr_time.innerHTML = (ct-(ct%=60))/60+(9<ct?':':':0')+ct
	});
}

function load_vid(el, vid_url) {
	var vid_container = el.getElementsByClassName('qvid-container')[0];
	var vid_el = document.createElement('video');
	vid_el['classList'].add('qvid-file');
	vid_el.src = 'media/' + vid_url;
	vid_el.muted = true;
	vid_container.appendChild(vid_el);

	el.removeAttribute('onclick');
	var vid_thumb = el.getElementsByClassName('index-qimg')[0];
	vid_thumb.remove();

	vid_el.addEventListener('loadeddata', (e) => {
		if(vid_el.readyState >= 3){
			prepare_video(el);
		}
	});
}

/*
 * Verifica se tem algum vídeo aparecendo na tela;
 * Se estiver aparecendo:
 *  reproduz o vídeo no mudo
 * Se não:
 *  Não faz nada.
 */

/* Função que verifica se o elemento está visível para o usuário. */

//Visível se parte do elemento é visível.
function element_of_load_more_is_visible(elem) {
    if (!(elem instanceof Element)) throw Error('DomUtil: elem is not an element.');
    const style = getComputedStyle(elem);
    if (style.display === 'none') return false;
    if (style.visibility !== 'visible') return false;
    if (style.opacity < 0.1) return false;
    if (elem.offsetWidth + elem.offsetHeight + elem.getBoundingClientRect().height +
        elem.getBoundingClientRect().width === 0) {
        return false;
    }
    const elemCenter   = {
        x: elem.getBoundingClientRect().left + elem.offsetWidth / 2,
        y: elem.getBoundingClientRect().top + elem.offsetHeight / 2
    };
    if (elemCenter.x < 0) return false;
    if (elemCenter.x > (document.documentElement.clientWidth || window.innerWidth)) return false;
    if (elemCenter.y < 0) return false;
    if (elemCenter.y > (document.documentElement.clientHeight || window.innerHeight)) return false;
    let pointContainer = document.elementFromPoint(elemCenter.x, elemCenter.y);
    do {
        if (pointContainer === elem) return true;
    } while (pointContainer = pointContainer.parentNode);
    return false;
}

function is_completely_visible(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

let load_more = document.getElementById('load-more-recent-btn');
let load_more_popular_btn = document.getElementById('load-more-popular-btn');
let players = document.getElementsByClassName('index-qvid-btn');

window.onscroll = function () {
    if (element_of_load_more_is_visible(load_more)) {
        load_more_recent();
    }
    else if (element_of_load_more_is_visible(load_more_popular_btn)) {
        load_more_popular(load_more_popular_btn, load_more_popular_btn.nextElementSibling, popular_page);
    }
	
    for (let i in players) {
        player = players[i];
		if (typeof player === 'object') {
			video = player.getElementsByClassName('qvid-file')[0];
			player.click();
			if (typeof video === 'undefined') {
				continue;
			}
			video.pause();

			if (is_completely_visible(video)) {
				prepare_video(player);
				var is_vid_muted = player.getElementsByClassName('qvunmt')[0].classList.contains('hidden');
				video.muted = is_vid_muted;
				video.play();
				player.getElementsByClassName('qvplay')[0].classList.add('hidden');
				player.getElementsByClassName('qvpause')[0].classList.remove('hidden');
			} else {
				video.pause();
				player.getElementsByClassName('qvplay')[0].classList.remove('hidden');
				player.getElementsByClassName('qvpause')[0].classList.add('hidden');
			}
		}
    }
};
