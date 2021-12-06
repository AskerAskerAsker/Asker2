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


/*
 * Renderiza as questÃµes recentes. */

var questoes_recentes = document.getElementById("lista_de_questoes_recentes");

function renderizar_questoes(questions) {
	for (var index = 0; index < 20; ++index) {
		try {
			questoes_recentes.innerHTML += '<li class="list-group-item questao" style="border: none; background: transparent" data-id="'+questions[index].id+'">' +
																		'<div class="card-body" style="border: none; background: transparent">' +
                                                                        '<div class="profile-picture-index" style="padding-bottom: 7px"><img style="width: 20px; height: 20px; border-radius: 100px" src="'+questions[index].question_creator_avatar+'"><span style="font-weight: 600; font-size: 12px; opacity: 0.7; padding-left: 7px">'+questions[index].creator+'</span></div>'+
																			'<div class="flexox" style="border: none; background: transparent">' +  
																				'<h2 style="font-size: 17px" class="question-title fg-1">' +
																					'<a class="q-title" style="text-decoration: none; outline: none" href="/question/'+questions[index].id+'">' +
																						questions[index].text +
																					'</a>' +
																				'</h2>' +
																			'</div>' +
																			(questions[index].description != '' ? '<p class="description">'+questions[index].description+'</p>' : '') +
                                         '<small class="text-muted">' +
                             (questions[index].total_answers == 1 ? '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+questions[index].id+'">1</span> <span style="color: #00CD66; font-weight: 500" id="response-sentence-'+questions[index].id+'">Resposta</span>' : '<span style="color: #00CD66; font-weight: 500" id="response-counter-'+questions[index].id+'">'+questions[index].total_answers+'</span> <span style="color: #00CD66; font-weight: 500" id="response-sentence-'+questions[index].id+'">Respostas</span>') + ' | ' + questions[index].pub_date +
                                                                            '</small>' +
																																					(user_status == "anonymous" ? '<p>Faça <a href="/signin?redirect=/question/'+questions[index].id+'">login</a> ou <a href="/signup?redirect=/question/'+questions[index].id+'">crie uma conta</a> para responder essa pergunta.</p>' : '') +
																			(questions[index].user_answer != 'False' ? '<div class="user-response" data-iddapergunta="'+questions[index].id+'"><p><b style="color: #40E0D0; font-weight: 900">Sua Resposta:</b><br>'+questions[index].user_answer+'</p></div>' : '<div class="user-response" data-iddapergunta="'+questions[index].id+'">'+
																			'<div>' +
																			
																			(user_status != "anonymous" ?
																			
																				'<br><button class="btn btn-outline-primary btn-sm botao_responder" style="border-radius: 30px; margin-top: -5px" onclick="$(this).toggle(0); $(this.parentElement.parentElement.nextElementSibling).toggle(0);">' +
																					'<i class="fas fa-share"></i>' +
																					' Responder' : '') +
																				'</button>' +
																			'</div></div>' +
																			'<div style="display: none">' +
																				'<form onsubmit="return enviar_resposta_pergunta(this);">' +
																					'<input type="hidden" name="csrfmiddlewaretoken" value="'+csrf_token+'">' +
																					'<input type="hidden" name="from" value="index">' +
																					'<input name="question_id" type="hidden" value="'+questions[index].id+'">' +
																					'<textarea onclick=\'$(this).css("height", "120px");\' name="text" maxlength="5000" class="form-control form-control-sm" placeholder="Sua Resposta:" required></textarea>' +
																					'<br><button name="submit_btn" type="submit" class="btn btn-outline-primary btn-sm" style="border-radius: 30px">' +
																					'<i class="far fa-paper-plane"></i>' +
																					' Enviar' +
																					'</button>' +
																				'</form>' +
																				'</div>') +
																		'</div>' +
																	'</li>'; } catch (e) {
																	}
	}
    $('.description').linkify();
}

renderizar_questoes(recent_questions);

/* Renderiza as questÃµes populares. */
var questoes_populares = document.getElementById("lista_de_questoes_populares");

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
                                                                                (popular_questions[index].total_answers == 1 ? '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">1</span> <span style="color: #00CD66; font-weight: 800" id="response-sentence-'+popular_questions[index].id+'">Resposta</span>' : '<span style="color: #00CD66; font-weight: 800" id="response-counter-'+popular_questions[index].id+'">'+popular_questions[index].total_answers+'</span> <span style="color: #00CD66" id="response-sentence-'+popular_questions[index].id+'">Respostas</span>') + ' | ' + popular_questions[index].pub_date +
                                                                            '</small>' +                  
                                                                  
                                                                '</li>'; } catch (e) {
                                                                }
    }
}

renderizar_questoes_populares(popular_questions_);



if (mostrar_primeiro == 'popular') {
	document.getElementById('novas_questoes').style.display = 'none';
	document.getElementById('questoes_populares').style.display = 'block';
	document.getElementById('botao-popular').style.borderBottomWidth = '3px';
} else {
	document.getElementById('novas_questoes').style.display = 'block';
	document.getElementById('questoes_populares').style.display = 'none';
	document.getElementById('botao-recentes').style.borderBottomWidth = '3px';
}

document.getElementsByTagName('body')[0].style.display = 'block';

function load_more(button, icon) {
	button.style.display = 'none';
	icon.style.display = 'block';
	$.ajax({
			url: "/more_questions",
			type: "get",
			dataType: "json",
			data: {
					id_de_inicio: document.getElementById("novas_questoes").getElementsByClassName("questao")[document.getElementById("novas_questoes").getElementsByClassName("questao").length - 1].getAttribute("data-id") - 1,
			},
			complete: function(data) {
				icon.style.display = 'none';
				button.style.display = 'block';
				renderizar_questoes(data.responseJSON);
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
                    }
                } catch (e) {
                    console.log(e);
                }
			},
	});
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
