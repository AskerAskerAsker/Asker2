userTabs = [];
tabsSections = [];

function switchTabs(tabIndex) {
    newTab = userTabs[tabIndex];
    newSection = tabsSections[tabIndex];
    for (i = 0; i < userTabs.length; i++) {
        if (userTabs[i] == newTab) {
            userTabs[i].classList.add("active");
            userTabs[i].classList.remove("disabled");
        } else {
            userTabs[i].classList.remove("active");
            userTabs[i].classList.add("disabled");
        }
    }
    for (i = 0; i < tabsSections.length; i++) {
        if (tabsSections[i] == newSection) {
            tabsSections[i].style.display = "block";
        } else {
            tabsSections[i].style.display = "none";
        }
    }
}

function addTab(tabId, tabSectionId) {
    tabElement = document.getElementById(tabId);
    tabSectionElement = document.getElementById(tabSectionId);
    if (tabElement && tabSectionElement) {
        var currIndex = userTabs.length;
        tabElement.onclick = function() { switchTabs(currIndex); };
        userTabs.push(tabElement);
        tabsSections.push(tabSectionElement);
    }
}

addTab('questions', 'questions-section');
addTab('responses', 'responses-section');
addTab('blocked', 'blocked-section');
addTab('silenced', 'silenced-section');

q_page = 1;
function show_more_questions(button, uid) {
	questions = document.getElementById('qs');
	
	$.ajax({
		type: 'get',
		dataType: 'json',
		url: '/get_more_questions',
		data: {
			q_page: ++q_page,
			user_id: uid,
		},
		complete: function(data) {
			
			if (data.responseText == "False") {
				button.style.display = "none";
			}
			
			data = JSON.parse(data.responseText);
			
			$.each(data.questions, function(i, val) {
			        var newLi = '<li class="list-group-item bg-main"><div class="question card-body"><a href="/question/'+val.id+'">'+val.text+'</a><br><span style="color: #888; font-size: 80%;">Perguntada '+val.naturalday+'</span>';
                    if (!val.best_answer) {
                        /* val.best_answer será -1 se proibido, a qid se existir, e null se não existir */
                        newLi += '<br><span style="color: #888; font-size: 80%;">Sem melhor resposta</span>';
                    }
					newLi += '</div></li>';

				questions.innerHTML += newLi;
			});
			
			if(!data.has_next) {
				button.remove();
			}
		}
	});
}

r_page = 1;
function show_more_responses(button, uid) {
	responses = document.getElementById('rs');
	
	$.ajax({
		type: 'get',
		dataType: 'json',
		url: '/get_more_responses',
		data: {
			r_page: ++r_page,
			user_id: uid,
		},
		complete: function(data) {
			data = JSON.parse(data.responseText);
			
			$.each(data.responses, function(i, val) {
			    var newLi = '<li class="list-group-item bg-main"><div class="response card-body"><a href="/question/'+val.question_id+'">'+val.question_text+'</a><br><p>';
			    if (val.best_answer) {
			        newLi += '<span class="badge badge-pill badge-primary">🏆 Melhor resposta</span> ';
			    }
			    newLi += val.text + '</p><span style="color: #888; font-size: 80%;">Perguntada por <a href="/user/'+val.creator+'">'+val.creator+'</a> '+val.naturalday+'</span></div></li>';
			    responses.innerHTML += newLi;
			});
			
			if(!data.has_next) {
				button.remove();
			}
		}
	});
}

/* Linkify */
$('#bio').linkify();
