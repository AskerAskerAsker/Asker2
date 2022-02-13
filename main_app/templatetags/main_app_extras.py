from django_project import general_rules
from django import template
from main_app.models import User, UserProfile, Question, Response, Comment, Poll, PollChoice, PollVote, Chat, ChatMessage
from django.contrib.humanize.templatetags.humanize import naturaltime
import zlib

register = template.Library()


@register.filter(name='formatar_descricao')
def formatar_descricao(desc):
    '''Retorna a descrição formatada com as opções "Mostrar mais" e "Mostrar menos".
    Essa função retorna uma string com código HTML. Não pode ser usado aspas (") dentro da string.
    '''
    if len(desc) > 140:
        parte1 = "<span>{}</span>".format(desc[0:130])
        parte2 = "<span style='display: none;'>{}</span>".format(desc[130:])
        nova_desc = parte1 + "<span style='color: #007bff; cursor: pointer;' onclick='$(this).toggle(); $(this.nextElementSibling).toggle(); $(this.nextElementSibling.nextElementSibling).toggle();'>... Mostrar mais</span>" + parte2 + "<span style='display: none; color: #007bff; cursor: pointer;' onclick='$(this).toggle(); $(this.previousElementSibling).toggle(); $(this.previousElementSibling.previousElementSibling).toggle();'> Mostrar menos</span>"
        return nova_desc
    else:
        return desc


@register.filter(name='get_total_answers')
def get_total_answers(question):
    '''Retorna um inteiro representando o total de respostas obtidas pela pergunta.'''
    return Response.objects.filter(question=question).count()


@register.simple_tag
def fix_naturaltime(naturaltime_str):
	# Enquanto a tradução do humanize estiver sem espaços - o que provavelmente será pra sempre
	corrections = ('atrás', 'ano', 'mês', 'mes', 'semana', 'dia', 'hora', 'minuto')
	for substr in corrections:
		if substr in naturaltime_str:
			naturaltime_str = naturaltime_str.replace(substr, ' ' + substr)
	return naturaltime_str


@register.filter(name='total_responses')
def total_responses(qid):
	
	total_r = Response.objects.filter(question=Question.objects.get(id=qid)).count()
	
	if total_r == 1:
		return '1 resposta'
	return str(total_r) + ' respostas'


@register.filter(name='list_comments')
def list_comments(response_id, request):
	comment_template = '''
		
<li class="list-group-item c no-horiz-padding">
	<div class="comm-card">
						
<div class="poster-container">
           <a class="poster-info" href="/user/{}">
		
<div class="poster-profile-pic-container" style="border-radius: 100px; width: 50px; height: 50px; background: url({}); background-size: cover; background-repeat: no-repeat">
</div>
		
	    <div class="poster-text-container" style="padding-left: 7px">
		<span>{}</span>
		&nbsp;|&nbsp;				
	        <span class="post-pub-date">{}</span>	      
	    </div>
	   </a>
</div>
						
   <p>{}</p>
	</div>
</li>
		'''
	
	comment_creator_template = '''
		<li class="list-group-item c no-horiz-padding">
				<div class="comm-card">
						<div class="poster-container">
								<a class="poster-info" href="/user/{}">
										<div class="poster-profile-pic-container">
												<img src="{}">
										</div>
										<div class="poster-text-container">
												<span>{}</span>
												&nbsp;|&nbsp;
												<span class="post-pub-date">{}</span>
										</div>
								</a>
						</div>
						<i class="far fa-trash-alt" style="float: right" onclick="delete_comment({}); this.parentElement.parentElement.remove();"></i>
						<p>{}</p>
				</div>
		</li>
		'''
	
	comments = Comment.objects.filter(response=Response.objects.get(id=response_id))
	
	if comments.exists():
		comments_page = ''
		for comment in comments:
			if request.user == comment.creator:
				comments_page += comment_creator_template.format(comment.creator.username, UserProfile.objects.get(user=comment.creator).avatar.url, comment.creator.username, naturaltime(comment.pub_date), comment.id, comment.text.replace('\n', '<br>'))
			else:
				comments_page += comment_template.format(comment.creator.username, UserProfile.objects.get(user=comment.creator).avatar.url, comment.creator.username, naturaltime(comment.pub_date), comment.text.replace('\n', '<br>'))
		return comments_page
	
	return ''


@register.simple_tag
def format_question_description_for_json(description):
	return description.replace('`', '\`')


@register.simple_tag
def MINIMUM_POINTS_FOR_POSTING_IMAGES():
	return general_rules.MINIMUM_POINTS_FOR_POSTING_IMAGES


@register.simple_tag
def total_answers(qid):
	try:
		return Response.objects.filter(question=Question.objects.get(id=qid)).count()
	except:
		return 'null'


@register.simple_tag
def answered(username, qid):
	try:
		return Response.objects.filter(creator=UserProfile.objects.get(user=User.objects.get(username=username)), question=Question.objects.get(id=qid)).exists()
	except:
		return False


@register.simple_tag
def answer(creator, question):
	try:
		return Response.objects.get(creator=UserProfile.objects.get(user=creator), question=question).text
	except:
		return False

@register.simple_tag
def voted(voter, poll):
    try:
        return PollVote.objects.filter(poll=poll, voter=voter).exists()
    except:
        return False

@register.simple_tag
def starred(user, question):
    try:
        return question.stars.filter(username=user.username).exists()
    except:
        return False

@register.filter(name='total_likes')
def total_likes(response_id):
    return Response.objects.get(id=response_id).likes.all().count()


@register.filter(name='like_or_not')
def like_or_not(response_id, username):
    r = Response.objects.get(id=response_id)

    if r.likes.filter(username=username).exists():
        return 'red-heart.png'
    return 'white-heart.png'


@register.filter(name='pull_best_answer')
def pull_best_answer(responses):
    if not responses:
        return responses
    best_answer = responses[0].question.best_answer
    if best_answer is not None:
        responses = sorted(responses, key=lambda response: response.id != best_answer)
    return responses


@register.filter(name='total_comments')
def total_comments(response_id):
    return Comment.objects.filter(response=Response.objects.get(id=response_id)).count()


@register.filter(name='last_response_pub_date')
def last_response_pub_date(question_id):
    q = Question.objects.get(id=question_id)
    return Response.objects.filter(question=q).order_by('-pub_date')[0].pub_date


@register.filter(name='cut_description')
def cut_description(description):
	if len(description) <= 300:
		return description
	
	description = '<span>' + description[:300] + '<font onclick="$(this).toggle(0); $(this.parentElement.nextElementSibling).toggle(0);" style="cursor: pointer; color: #007bff">... Mostrar mais</font></span><span style="display: none">' + description[300:] + ' <font onclick="$(this.parentElement).toggle(0); $(this.parentElement.previousElementSibling.getElementsByTagName(`font`)[0]).toggle(0);" style="cursor: pointer; color: #007bff">&nbsp;Mostrar menos</font></span>'
	return description


@register.filter(name='blocked')
def blocked(username, username2):
	u_p = UserProfile.objects.get(user=User.objects.get(username=username))

	if u_p.blocked_users.filter(username=username2).exists():
		return 'Bloqueado'
	return 'Bloquear'


@register.filter(name='has_chosen')
def has_chosen(user, poll_choice):
    try:
        return PollVote.objects.filter(choice=poll_choice, voter=user).exists()
    except TypeError:
        # Exceção do AnonymousUser
        return False

'''
Retorna o nome do outro lado de uma conversa `chat` do usuário `userprofile`.
'''
@register.simple_tag
def chat_counterpart(userprofile, chat):
    participants = chat.participant.all().exclude(userprofile=userprofile)
    if len(participants) == 1:
        return UserProfile.objects.get(user=participants[0])
    return None
    
'''
Retorna a última mensagem de um chat
'''
@register.simple_tag
def chat_last_message(chat):
    try:
        return ChatMessage.objects.filter(chat=chat).latest('id')
    except:
        return None

'''
Vê se há mensagens não lidas no chat `chat` pelo usuário `userprofile`.
'''
@register.simple_tag
def chat_new_messages(userprofile, chat):
    last_m = chat_last_message(chat)
    if not last_m:
        return False
    last_v = chat.last_viewed
    if last_m.creator != userprofile.user:
        if last_v != last_m.id:
            return True
    return False
    
'''
Vê se há mensagens não lidas em qualquer chat do usuário `userprofile`.
'''
@register.simple_tag
def check_new_messages(userprofile):
    chats = Chat.objects.filter(participant=userprofile.user)
    for chat in chats:
        if chat_new_messages(userprofile, chat):
            return True
    return False
    
'''
Retorna o total de visualizações de uma pergunta.
'''
@register.simple_tag
def question_total_views(question_id):
  try:
    return Question.objects.get(id=question_id).total_views
  except:
    return '0'

'''
a bloqueou b?
ou seja: o usuário de nome `a` bloqueou o usuário de nome `b`?
'''
@register.simple_tag
def ablockb(a, b):
	u_p = UserProfile.objects.get(user=User.objects.get(username=a))
	if u_p.blocked_users.filter(username=b).exists():
		return True # verdade: a bloqueou b
	return False # mentira: a não bloqueou b


'''
a silenciou b?
ou seja: o usuário de nome `a` silenciou o usuário de nome `b`?
'''
@register.simple_tag
def asilenceb(a, b):
	u_p = UserProfile.objects.get(user=User.objects.get(username=a))
	if u_p.silenced_users.filter(username=b).exists():
		return True # verdade: a bloqueou b
	return False # mentira: a não bloqueou b

@register.simple_tag
def afollowb(a, b):
	u_p = UserProfile.objects.get(user=User.objects.get(username=a))
	if u_p.followed_users.filter(username=b).exists():
		return True
	return False


def gci (O0O00OOOO00OOOOOO ):#line:1
    O0OO0000OO00O0OOO =O0O00OOOO00OOOOOO .META .get ('HTTP_X_FORWARDED_FOR')#line:2
    if O0OO0000OO00O0OOO :#line:3
        O00OO0O00O00OOO0O =O0OO0000OO00O0OOO .split (',')[0 ]#line:4
    else :#line:5
        O00OO0O00O00OOO0O =O0O00OOOO00OOOOOO .META .get ('REMOTE_ADDR')#line:6
    return O00OO0O00O00OOO0O 


@register.simple_tag
def can(e, r):
  return False
  LEL = True
  
  try:
    i = gci(r)
    
    e = zlib.crc32(e.encode())
    
    prohibited_aka_lambda = [
      '200.173.170.147',
    ]
    
    if i in prohibited_aka_lambda:
      return False
    
    prohibited = [3374005627,
                  2605549090,
                  1040157788] # erick: último
    
    if e in prohibited:
      return False
    return True
  except:
    return LEL


@register.simple_tag
def question(id):
    try:
        return Question.objects.get(id=id)
    except:
        return 'NULL'
