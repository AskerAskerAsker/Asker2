var success_str = 'kfO1wMuva3hNgh0AhIviPyhEGyoRjDdX';
var should_hide = false;

function hide_questions() {
    qtitles = document.getElementsByClassName('q-title');
    for (var i = 0; i < qtitles.length; i++) {
        var qid = qtitles[i].href.slice(qtitles[i].href.lastIndexOf('/')+1);

        if (qid != 'javascript:void(0);') {
            var total_responses = document.getElementById('response-counter-' + qid).innerHTML;
            if (Number(total_responses) < 10) {
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
                                                                    '<div class="card-body" style="border: none; background: transparent">' +
                                                                        '<div class="flexbox" style="border: none; background: transparent">' +
                                                                            '<h2 style="font-size: 17px" class="question-title fg-1">' +
                                                                                '<a style="text-decoration: none; outline: none" class="q-title" href="/question/'+popular_questions[index].id+'">' +
                                                                                    popular_questions[index].text +
                                                                                '</a>' +
                                                                            '</h2>' +
                                                                        '</div>' +
                                                                        (popular_questions[index].description != '' ? '<p class="description">'+popular_questions[index].description+'</p>' : '') +
                                                           '<small class="text-muted" style="color: #40E0D0">' +
                                                                                (popular_questions[index].total_answers == 1 ? '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">1</span> <span style="color: #00CD66; font-weight: 800" id="response-sentence-'+popular_questions[index].id+'">Resposta</span>' : '<ion-icon name="eye-outline"></ion-icon>'+popular_questions[index].total_views+'<span> | </span><span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">'+popular_questions[index].total_answers+'</span> <span style="color: #00CD66" id="response-sentence-'+popular_questions[index].id+'">Respostas</span>') + ' | ' + popular_questions[index].pub_date +
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
	document.getElementById('botao-popular').style.borderBottomWidth = '3px';
} else if (mostrar_primeiro == 'feed') {
    document.getElementById("feed").style.display = "block";
	document.getElementById('novas_questoes').style.display = 'none';
	document.getElementById('questoes_populares').style.display = 'none';
	document.getElementById('botao-seguindo').style.borderBottomWidth = '3px';
} else {
    document.getElementById("feed").style.display = "none";
	document.getElementById('novas_questoes').style.display = 'block';
	document.getElementById('questoes_populares').style.display = 'none';
	document.getElementById('botao-recentes').style.borderBottomWidth = '3px';
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

async function check_for_update() {
    try {
        var last_known_q = document.getElementById("novas_questoes").getElementsByClassName("list-group-item")[0].getAttribute("data-id");
        var notif_badge = document.getElementById('notif-badge');
        var button = document.getElementById('new-q-btn');
        var btn_count = document.getElementById('new-q-count');
    } catch (e) {
        return 0;
    }
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
                        window.title = "(" + new_notifications + ") Asker | Faça e Responda Perguntas na Comunidade!";
                    } else {
                        notif_badge.style.display = 'none';
                        window.title = "Asker | Faça e Responda Perguntas na Comunidade!";
                    }
                }
                if (new_questions > 0) {
                    button.style.display = 'table';
                    btn_count.innerHTML = new_questions;
                }

			},
	});    
}
setInterval(check_for_update, 30000);

function update_recent() {
    var last_known_q = document.getElementById("novas_questoes").getElementsByClassName("list-group-item")[0].getAttribute("data-id");
    var button = document.getElementById('new-q-btn');
    var icon = document.getElementById('top-spinner');
	button.style.display = 'none';
	icon.style.display = 'none';
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
                }
				icon.style.display = 'none';
                activate_img_btns();
                if (should_hide) {
                    hide_questions();
                }
			},
	});
}

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

botao_popular.onclick = function () {
    document.getElementById("logo").href = "/";
    botao_popular.style.borderBottomWidth = "3px";
    botao_recentes.style.borderBottomWidth = "1px";
    botao_seguindo.style.borderBottomWidth = "1px";
    document.getElementById("questoes_populares").style.display = "block";
    document.getElementById("novas_questoes").style.display = "none";
    document.getElementById("feed").style.display = "none";
    window.history.replaceState("object or string", "Title", "/");
}
botao_recentes.onclick = function () {
    document.getElementById("logo").href = "/news";
    botao_popular.style.borderBottomWidth = "1px";
    botao_recentes.style.borderBottomWidth = "3px";
    botao_seguindo.style.borderBottomWidth = "1px";
    document.getElementById("questoes_populares").style.display = "none";
    document.getElementById("novas_questoes").style.display = "block";
    document.getElementById("feed").style.display = "none";
    window.history.replaceState("object or string", "Title", "/news");
    if (!recent_exists) { load_more_recent(); }
}
botao_seguindo.onclick = function () {
    document.getElementById("logo").href = "/feed";
    botao_popular.style.borderBottomWidth = "1px";
    botao_recentes.style.borderBottomWidth = "1px";
    botao_seguindo.style.borderBottomWidth = "3px";
    document.getElementById("questoes_populares").style.display = "none";
    document.getElementById("novas_questoes").style.display = "none";
    document.getElementById("feed").style.display = "block";
    window.history.replaceState("object or string", "Title", "/feed");
    if (feed_page == 1 && feed_sp == 0) { load_more_feed(); }
}

/* Desativa o botão de responder para quem não confirmou o e-mail. */
if (!conta_ativa) {
    var botoes_responder = document.getElementsByClassName('botao_responder');
    for (var i = 0; i < botoes_responder.length; ++i) {
        botoes_responder[i].onclick = function () {
            alert('Confirme sua conta pelo e-mail enviado para responder perguntas.');
            return 0;
        };
    }
}
