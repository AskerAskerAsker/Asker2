var success_str = 'kfO1wMuva3hNgh0AhIviPyhEGyoRjDdX';

var resp_count = document.getElementsByClassName('resposta').length;
document.getElementById('total-de-respostas').innerText = resp_count
document.getElementById('total-de-respostas-sentence').innerText = (resp_count == 1 ? 'Resposta' : 'Respostas');

var description = document.getElementsByClassName('description');
if (description.length === 1) {
    fix_double_escape(description[0]);
    anchor_urls(description[0]);
}
function anchor_responses() {
    var r_els = document.getElementsByClassName('r-p');
    for (var i = 0; i < r_els.length; i++) {
        anchor_urls(r_els[i]);
    }
}
anchor_responses();

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
                    off['classList'].remove('hidden');
                    on['classList'].add('hidden');
                } else {
                    off['classList'].add('hidden');
                    on['classList'].remove('hidden');
                }
            }
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

var upload_photo_btn = document.getElementById('upload-photo');
if (upload_photo_btn) {
    document.getElementById('upload-photo').onchange = function () {
        var text = document.getElementById('upload-photo-text');
        var delete_photo_icon = document.getElementById('delete-photo-icon');
        var input = document.getElementById('upload-photo');
        text.innerText = input.value.slice(12);
        delete_photo_icon.style.display = 'inline';
    };
}

var delete_photo_btn = document.getElementById('delete-photo-icon');
if (delete_photo_btn) {
    document.getElementById('delete-photo-icon').onclick = function () {
        var delete_photo_icon = document.getElementById('delete-photo-icon');
        var input = document.getElementById('upload-photo');
        var text = document.getElementById('upload-photo-text');
        delete_photo_icon.style.display = 'none';
        text.innerText = '';
        input.value = null;
    };
}

function delete_question(id) {
    if (confirm('Opa! Tem certeza que deseja apagar sua pergunta?')) {
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

var formulario_de_resposta = document.getElementById("formulario_de_resposta");
if (formulario_de_resposta) {
    formulario_de_resposta.onsubmit = function() {
        document.getElementById("botao_enviar_resposta").disabled = true;
        last_response = get_last_response();
        var formData = new FormData(this);
        $.ajax({
            url: "/save_answer",
            method: "post",
            data: formData,
            cache:false,
            contentType: false,
            processData: false,
            success: function(data) {
                document.getElementsByClassName("responses")[0].innerHTML += data;
                formulario_de_resposta.remove();
            },
            error: function(data, text, err) {
                var err_msg = "Um erro temporário ocorreu. Por favor, tente novamente."
                if (data.status == 406) {
                    err_msg = data.responseText;
                }
                document.getElementById("r-ctrls").innerHTML = err_msg;
            }
        });
        return false;
    };
}

function report_question(id) {
    var report = confirm('Você tem certeza de que deseja reportar esta pergunta?');
    
    if (report) {
        $.ajax({
            url: '/report?type=q&obj_id=' + id,
            type: 'post',
            data: {
                csrfmiddlewaretoken: csrf_token,
            },
            complete: function () {
                alert('Pergunta Reportada.');
            }
        });
    }
}

function follow_question(id) {
    $.ajax({
        url: '/question/' + id + '/follow',
        type: 'post',
        data: {
            csrfmiddlewaretoken: csrf_token,
        },
        complete: function (data) {
            if (data.responseText == 'Removed') {
                alert('Você já estava seguindo a pergunta. Você deixou de segui-la.');
            }
            document.getElementById('unfqa').classList.remove('hidden');
            document.getElementById('fqa').classList.add('hidden');
        }
    });
}

function unfollow_question(id) {
    $.ajax({
        url: '/question/' + id + '/follow',
        type: 'post',
        data: {
            csrfmiddlewaretoken: csrf_token,
        },
        complete: function (data) {
            if (data.responseText == 'Added') {
                alert('Você não estava seguindo a pergunta. Você passou a segui-la.');
            }
            document.getElementById('unfqa').classList.add('hidden');
            document.getElementById('fqa').classList.remove('hidden');
        }
    });
}

var last_response = 0;
function get_last_response() {
    rlist = document.getElementsByClassName('resposta');
    var last = 0;
    for (var i=0;i<rlist.length;i++) {
        var id = rlist[i].getAttribute('data-id');
        if (id > last) { last = id; };
    }
    return last;
}

var UPD_INTERVAL = 0;
var upd_count = 0;
async function new_activity_check() {
    upd_count++;
    if (upd_count > 15) { clearInterval(UPD_INTERVAL); }
    var notif_badge = document.getElementById('notif-badge');
    if (!last_response) {
        last_response = get_last_response();
    }
	var button = document.getElementById('new-r-btn');
	var btn_count = document.getElementById('new-r-count');
	$.ajax({
        url: "/new_activity_check",
        type: "get",
        dataType: "json",
        data: {
            last_known_r: last_response,
            qid: qid,
        },
        complete: function(data) {
            new_notifications = data.responseJSON['nn'];
            new_responses = data.responseJSON['nr'];
            if (new_notifications > 0) {
                notif_badge.innerHTML = new_notifications;
                notif_badge.style.display = 'block';
                document.title = "(" + new_notifications + ") " + org_title;
            } else {
                notif_badge.style.display = 'none';
                document.title = org_title;
            }
            if (new_responses > 0) {
                button.style.display = 'table';
                btn_count.innerHTML = new_responses;
            }
        },
	});
}

function load_responses() {
    var button = document.getElementById('new-r-btn');
	button.style.display = 'none';
	var rl = document.getElementsByClassName('resposta');
	for (var i=0;i<rl.length;i++) {
        if (rl[i].classList.contains('new')) { rl[i].classList.remove('new'); }
	    rl[i].classList.add('old');
	}
	$.ajax({
			url: "/update_question",
			type: "get",
			dataType: "html",
			data: {
				lr: last_response,
				qid: qid,
			},
			complete: function(data) {
                if (data.responseText == '-1') {
                    icon.style.display = 'none';
                } else if (data.responseText.includes(success_str)) {
                    r_list = document.getElementById('responses');
                    r_list.innerHTML = r_list.innerHTML + data.responseText;
                    var rl = document.getElementsByClassName('resposta');
                    for (var i=0;i<rl.length;i++) {
                        if (rl[i].classList.contains('old')) {
                            rl[i].classList.remove('old');
                        } else { rl[i].classList.add('new'); }
                    }
                    anchor_responses();
                    window.scrollTo(0,document.body.scrollHeight);
                    last_response = get_last_response();
                }
                icon.style.display = 'none';
			},
	});
}
