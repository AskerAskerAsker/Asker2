function like(likeElement, response_id) {
	var like_image = likeElement.getElementsByTagName('img')[0];
	var span_like_counter = null;
	if (like_image.src.includes('white-heart.png')) {
		like_image.src = '/static/images/red-heart.png?version=3';
		span_like_counter = likeElement.getElementsByTagName('span')[0];
		span_like_counter.innerHTML = Number(span_like_counter.innerHTML) + 1;
	}
	else {
		like_image.src = '/static/images/white-heart.png?version=3';
		span_like_counter = likeElement.getElementsByTagName('span')[0];
		span_like_counter.innerHTML = Number(span_like_counter.innerHTML) - 1;
	}
	$.ajax({
		url: '/answer/like',
		data: {
			answer_id: response_id,
		},
		complete: function() {
			return;
		}
	});
}


function delete_response(response_button_dom_el, response_id) {
    if (confirm('Opa! Você tem certeza que deseja apagar sua resposta?')) {
	    $.ajax({
    		url: '/delete_response',
    		data: {
    			response_id: response_id,
    		},
    		complete: function() {
    			response_button_dom_el.parentElement.parentElement.parentElement.remove();
    		}
    	});
    }
}


function delete_comment(comment_id) {
	$.ajax({
		url: '/delete_comment',
		type: 'get',
		data: {
			comment_id: comment_id,
		},
		complete: function() {
			alert('Comentário deletado.');
		}
	});
}


function report_question(question_id, obj) {
	function ok() {
		obj.parentElement.innerHTML = '<p>Pergunta denunciada <i class="far fa-check-circle"></i></p>';
		obj.remove();
	}
	$.ajax({
		type: 'get',
		url: '/report',
		data: {
			type: 'question',
			id: question_id,
		},
		complete: function () {
			ok();
		}
	});
}


function chooseAnswer(id) {
	$.ajax({
		url: '/answer/choose',
		data: {
			answer_id: id,
		},
		complete: function() {
		    var btns = document.getElementsByClassName('choose-answer-btn');
    		for (var i = btns.length-1; i >= 0; i--) {
                btns[i].remove();
                location.reload();
    		}
		}
	});
}


function voteOnPoll() {
    let userChoicesEls = $("input[name='poll-option']:checked");
    let userChoices = [];
    if (userChoicesEls.length < 1) { return 0; }
    for (var i = 0; i < userChoicesEls.length; i++) {
        userChoices.push(userChoicesEls[i].value);
    }
    $.ajax({
      type: "POST",
      url: '/poll/vote',
      data: {
          poll: $("input[name=qpoll]").val(),
          choices: userChoices,
          csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
      },
      success: function() {
          window.location.reload();
      }
    });
}


function undoVote() {
    $.ajax({
      type: "POST",
      url: '/poll/undovote',
      data: {
          poll: $("input[name=qpoll]").val(),
          csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
      },
      success: function() {
          window.location.reload();
      }
    });
}


function openChooser() {
    let chooser = document.getElementsByClassName('poll-chooser')[0];
    let shower = document.getElementsByClassName('poll-shower')[0];
    shower.style.display = 'none';
    chooser.style.display = 'block';
}


function openShower() {
    let chooser = document.getElementsByClassName('poll-chooser')[0];
    let shower = document.getElementsByClassName('poll-shower')[0];
    chooser.style.display = 'none';
    shower.style.display = 'block';
}


function setPollPercentages() {
    if (document.getElementsByClassName('poll-shower').length == 0) { return 0; }
    let els = document.getElementsByClassName('choice-show');
    var totalVotes = 0;
    var votes = [];
    for (var i=0; i < els.length; i++) {
        let choiceVotes = Number(els[i].getElementsByClassName('vote-count')[0].textContent);
        totalVotes = totalVotes + choiceVotes;
        votes.push(choiceVotes);
    }

    for (var ind=0; ind < els.length; ind++) {
        let progressBar = els[ind].getElementsByClassName('progress-bar')[0];
        let percentage = (votes[ind] / totalVotes) * 100;
        let percentageString = Math.round(percentage) + '%';
        if (percentage >= 15) { progressBar.textContent = percentageString; }
        progressBar.title = percentageString;
        progressBar.style = 'width: ' + percentageString + ';';
    }
}
setPollPercentages();

if (document.getElementsByClassName('poll-chooser').length == 1) {
   openChooser();
}


function make_comment(form) {
	$(form.previousElementSibling).toggle(0);
	var formData = $(form).serialize();
	$.ajax({
		url: '/comment',
		type: 'post',
		dataType: 'json',
		data: formData,
		complete: function(data) {
			var new_comment = data.responseText;
			form.parentElement.getElementsByTagName('ul')[0].innerHTML += new_comment;
			form.text.value = '';
			$(form.previousElementSibling).toggle(0);
		}
	});
}


/* Js p/ upload de imagem em respostas */
document.getElementById('upload-photo').onchange = function () {
	var text = document.getElementById('upload-photo-text');
	var delete_photo_icon = document.getElementById('delete-photo-icon');
	var input = document.getElementById('upload-photo');
	text.innerText = input.value.slice(12);
	delete_photo_icon.style.display = 'inline';
};

document.getElementById('delete-photo-icon').onclick = function () {
	var delete_photo_icon = document.getElementById('delete-photo-icon');
	var input = document.getElementById('upload-photo');
	var text = document.getElementById('upload-photo-text');
	delete_photo_icon.style.display = 'none';
	text.innerText = '';
	input.value = null;
};
/* Fim: Js p/ upload de imagem em respostas */


function delete_question(id) {
    if (confirm('Opa! Tem certeza que deseja apagar sua resposta?')) {
		$.ajax({
			url: '/delete_question',
			type: 'post',
			data: {
				csrfmiddlewaretoken: csrf_token,
				question_id: id,
			},
			complete: function() {
				window.location = window.location.href.match(/^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i)[0] + 'news';
			}
		});
	}
}


var formbgcolor='bg-white'; var bgcolor='bg-white'; var textcolor='text-dark';
var commentformbgcolor='bg-white'; var commentbgcolor='bg-light';
if (getDarkCookie() == 'true') {
	document.getElementsByClassName('navbar')[0].classList.remove("navbar-light");
	document.getElementsByClassName('navbar')[0].classList.add("navbar-dark");
}




var formulario_de_resposta = document.getElementById("formulario_de_resposta");

formulario_de_resposta.onsubmit = function() {
	
	/* Desativa o botão de enviar resposta para evitar spam. */
	document.getElementById("botao_enviar_resposta").disabled = true;
	
	var formData = new FormData(this);
	
	$.ajax({
		url: "/save_answer",
		method: "post",
		data: formData,
		cache:false,
		contentType: false,
		processData: false,
		complete: function(data) {
			document.getElementsByClassName("responses")[0].innerHTML += data.responseText;
			formulario_de_resposta.remove();
		},
	});
	
	return false;
};

try {
    var description = document.getElementsByClassName('description')[0];
    description.innerText = description.innerText.replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>');
} catch (e) {
    console.log(e);
}
