var pollChoices = 2;

function addPollChoice() {
    if (pollChoices == 12) { return 0; }
    pollChoices += 1;
    var choicesDiv = document.getElementById('poll-choices');

    var newChoiceDiv = document.createElement('div');
    newChoiceDiv.class = 'poll-choice';
    newChoiceDiv.id = 'choice-' + pollChoices;
    newChoiceDiv.innerHTML += '<span>Opção '+ pollChoices +':</span><br><input class="form-control poll-choice-text bg-outer-when-dark" type="text" name="choice-'+ pollChoices +'" autocomplete="off" maxlength="60" required>';
    choicesDiv.appendChild(newChoiceDiv);

    document.getElementById('choices-counter').value = pollChoices;
}

function removePollChoice() {
    if (pollChoices == 2) { return 0; }
    let choiceDiv = document.getElementById('choice-' + pollChoices);
    choiceDiv.remove();
    pollChoices -= 1;
    document.getElementById('choices-counter').value = pollChoices;
}

function togglePoll() {
    let counter = document.getElementById('choices-counter');
    let pollBox = document.getElementById('poll-box');
    let pollChoicesTexts = document.getElementsByClassName('poll-choice-text');
    if (counter.value == 0) {
        pollBox.style = 'display: flex;';
        counter.value = pollChoices;
        for (var i = 0; i < pollChoicesTexts.length; i++) {
            pollChoicesTexts[i].required = true;
        }
    } else {
        pollBox.style = 'display: none;';
        counter.value = 0;
        for (var i = 0; i < pollChoicesTexts.length; i++) {
            pollChoicesTexts[i].required = false;
        }
    }
}

function enviar_pergunta(form) {
    form.submit();
    format_form(form);
    botao_perguntar = document.getElementById("botao_fazer_pergunta");
    botao_perguntar.disabled = true;
}

function check_vid_size(el) {
    var s = el.files[0].size;
    if (s > 3100000) {
	    alert('Tamanho máximo de vídeo excedido.');
	    el.value = null;
    }
}

// O CÓDIGO ABAIXO (NSFW DETECTOR) DEPENDE DA BIBLIOTECA deepai.min.js!
deepai.setApiKey("2826d443-8d49-4d03-aaab-6cf13a6f86fe");

function analisar_imagem() {
    document.getElementById("carregando-imagem").style.display = "block";
    
    (async function nsfw_detector() {
        try {
            var resp = await deepai.callStandardApi("nsfw-detector", {
                            image: document.getElementById("image"),
            });
            nsfw_score = resp["output"]["nsfw_score"];
            /*
             * nsfw_score > 0.8: imagem não vai ser enviada.
             * nsfw_score <= 0.6: imagem vai ser enviada.
             */
            if (nsfw_score > 0.8) {
                document.getElementById("image").value = null;
                alert("Impossível enviar imagem.");
                document.getElementById("carregando-imagem").style.display = "none";
                botao_perguntar.disabled = false;
                return;
            }
            document.getElementById("img_nsfw_score").value = nsfw_score;
            document.getElementById("carregando-imagem").style.display = "none";
            botao_perguntar.disabled = false;
            return;
            
        } catch (e) {
            document.getElementById("carregando-imagem").style.display = "none";
            botao_perguntar.disabled = false;
            return;
        }
    })();
}
/* Analisa a imagem quando o usuário preenche o campo de imagem no formulário. */
document.getElementById("image").onchange = analisar_imagem;
// O CODIGO DO NSFW DETECTOR ACABA AQUI
