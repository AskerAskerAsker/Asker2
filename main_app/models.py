'''
    Modelos que representam os objetos do site, como:
        perguntas, respostas, comentários, etc.
'''

from django_project.general_rules import SECONDS_TO_CHOOSE_BEST_ANSWER
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturaltime


def make_embedded_content(text):
    urls = ('https://youtu.be/', 'youtube.com/watch?v=', 'https://voca.ro/', 'vocaroo.com/')
    if urls[0] in text or urls[1] in text:
        type = 0
        url_index = text.find(urls[0])
        if url_index == -1 or len(text) < url_index + len(urls[0]) + 11:
            type = 1
            url_index = text.find(urls[1])

        if len(text) < url_index + 11:
            return None
        url_index += len(urls[type])
        video_id = text[url_index:url_index + 11]
        if video_id:
            return """
                <div class="vid-container">
                    <iframe src="https://www.youtube.com/embed/{}?rel=0" class="yt-vid" frameborder="0" allowfullscreen="allowfullscreen">
                    </iframe>
                </div>
            """.format(
                    video_id)
    elif urls[2] in text or urls[3] in text:
        type = 2
        url_index = text.find(urls[2])
        if url_index == -1 or len(text) < url_index + len(urls[0]) + 4:
            type = 3
            url_index = text.find(urls[3])

        if len(text) < url_index + 4:
            return None
        url_end_index = text.find(' ', url_index)
        url_index += len(urls[type])
        if url_end_index > -1:
            
            ''' replace('"') p/ caso o link seja um src attr de uma
                tag <a> - necessário pois ha tags html guardadas formatadas no db '''
            audio_id = text[url_index:url_end_index].replace('"', '')
        else:
            
            ''' replace('"') p/ caso o link seja um src attr de uma
                tag <a> - necessário pois ha tags html guardadas formatadas no db '''
            audio_id = text[url_index:].replace('"', '')
        if audio_id:
            return """
                    <div class="voc-container">
                        <iframe width="300" height="60" src="https://vocaroo.com/embed/{}?autoplay=0" frameborder="0" allow="autoplay">
                        </iframe>
                        <br>
                    </div>
                    """.format(audio_id)


class UserProfile(models.Model):
    ip = models.TextField(null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(max_length=256, default='avatars/default-avatar.png', blank=True)
    bio = models.TextField(max_length=2048, blank=True)
    total_points = models.IntegerField(null=True, default=0, blank=True)
    cover_photo = models.ImageField(blank=True, default=None, null=True)

    '''
    pap: permissão para apagar perguntas
    par: permissão para apagar respostas
    pac: permissão para apagar comentários
    '''
    permissions = models.TextField(default='[]') # lista Python
    
    ''' total de visualizações desde o dia: 16/04/2021 '''
    total_views = models.IntegerField(default=0, blank=True)

    blocked_users = models.ManyToManyField(User, related_name='blocked_by', blank=True)

    active = models.BooleanField(default=False) # conta está ativa ou não.

    hide_activity = models.BooleanField(default=True)

    ban = models.BooleanField(default=False) # usuário está em shadow ban ou não

    silenced_users = models.ManyToManyField(User,
                                            through="SilencedUsers",
                                            related_name='silenced_by',
                                            blank=True)

    # informações diversas:
    infos = models.TextField(default='{}') # <- JSON aqui.
    
    new_notifications = models.IntegerField(default=0, null=False, blank=False)

    followable = models.BooleanField(default=True)
    followed_users = models.ManyToManyField(User, related_name='followed_by', blank=True)
    followed_questions = models.ManyToManyField('Question', related_name='q_followed_by', blank=True)
    
    allows_chat = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

    def total_questions(self):
        return Question.objects.filter(creator=self).count()

    def total_responses(self):
        return Response.objects.filter(creator=self).count()

    def points(self):
        total = self.total_responses() * 2
        total += self.total_questions()
        return total

class SilencedUsers(models.Model):
    silenced = models.ForeignKey(User, on_delete=models.CASCADE)
    silencer = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    expires = models.DateTimeField(default=timezone.now)


class Question(models.Model):
    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    text = models.TextField()
    description = models.TextField(null=True)
    pub_date = models.DateTimeField(default=timezone.now)
    image = models.ImageField(null=True, blank=True)
    total_likes = models.IntegerField(default=0, null=True)
    total_responses = models.IntegerField(default=0)
    total_views = models.IntegerField(null=True, default=0)
    best_answer = models.IntegerField(blank=True, null=True) # ID da melhor resposta.
    viewers = models.TextField(null=False, blank=True, default='set()')  # TODO: entry nao usada!
    stars = models.ManyToManyField(User)
    total_stars = models.IntegerField(default=0)

    def get_embedded_content(self):
        return make_embedded_content(self.description)

    def may_choose_answer(self):
        if self.best_answer is None:
            if (timezone.now() - self.pub_date).total_seconds() > SECONDS_TO_CHOOSE_BEST_ANSWER:
                return True
        return False

    def has_poll(self):
        return Poll.objects.filter(question=self).exists()

    def __str__(self):
        return self.text


class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    creator = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    text = models.TextField()
    pub_date = models.DateTimeField(default=timezone.now)
    likes = models.ManyToManyField(User)
    total_likes = models.IntegerField(default=0)
    image = models.ImageField(null=True, blank=True)

    def get_naturaltime(self):
        return correct_naturaltime(naturaltime(self.pub_date))

    def get_embedded_content(self):
        return make_embedded_content(self.text)

    def __str__(self):
        return self.text


class Comment(models.Model):
    response = models.ForeignKey(Response, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    pub_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text


class Notification(models.Model):
    receiver = models.ForeignKey(User, on_delete=models.CASCADE)
    
    '''tipos: question-answered, like-in-response, comment-in-response, got-best-answer'''
    type = models.TextField()
    text = models.TextField(null=True)
    creation_date = models.DateTimeField(default=timezone.now)

    '''os campos abaixo são usados caso a notificação seja do tipo like-in-response.'''
    
    # quem deu o like
    liker = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              null=True,
                              related_name='l')
    
    # qual é a resposta
    response = models.ForeignKey(Response,
                                 on_delete=models.CASCADE,
                                 null=True,
                                 related_name='r')

    read = models.BooleanField(default=False) # this.receiver clicou ou não na notificação.

    def prepare(self, answer_id=None, comment_id=None):
        receiver_p = UserProfile.objects.get(user=self.receiver)
        receiver_p.new_notifications += 1
        receiver_p.save()

        if self.text:
            return

        if self.type == 'like-in-response':
            self.text = '''
                            <p>Você recebeu um ❤️ na sua resposta <a href="/question/{}?n={}">"{}"</a>
                            </p>'''.format(Response.objects.get(id=answer_id).question.id,
                                           self.id,
                                           Response.objects.get(id=answer_id).text)
        elif self.type == 'question-answered':
            response = Response.objects.get(id=answer_id)
            self.text = '''
                            <p><a href="/user/{}">{}</a> respondeu sua pergunta <a href="/question/{}?n={}">"{}"</a>
                            </p>'''.format(response.creator.user.username,
                                           response.creator.user.username,
                                           response.question.id,
                                           self.id,
                                           response.question.text)

        elif self.type == 'comment-in-response':
            response = Response.objects.get(id=answer_id)
            comment = Comment.objects.get(response=response, id=comment_id)
            self.text = '''
                            <p><a href="/user/{}">{}</a> comentou na sua resposta na pergunta: <a href="/question/{}?n={}">"{}"</a></p>
                        '''.format(comment.creator.username,
                                   comment.creator.username,
                                   comment.response.question.id,
                                   self.id,
                                   comment.response.question.text)

        elif self.type == 'got-best-answer':
            response = Response.objects.get(id=answer_id)
            self.text = '''
                            <p>Sua resposta foi escolhida a melhor resposta da pergunta: <a href="/question/{}?n={}">"{}"</a></p>
                        '''.format(response.question.id,
                                   self.id,
                                   response.question.text)

class Ban(models.Model): # todos os IP's banidos:
    ip = models.TextField(null=False, primary_key=True)


class Poll(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_anonymous = models.BooleanField(default=True)
    multichoice = models.BooleanField()

    def may_vote(self):
        return (timezone.now() - self.question.pub_date).total_seconds() < 43200

class PollChoice(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    text = models.TextField()
    votes = models.IntegerField(default=0)

class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    choice = models.ForeignKey(PollChoice, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE)

class Report(models.Model):
    type = models.TextField(null=False) # tipos: q (question), r (response), c (comment), u (user)
    obj_id = models.IntegerField(null=False)
    reporters = models.ManyToManyField(User)
    text = models.CharField(max_length=1024, null=True)
    total_reports = models.IntegerField(default=0)

class ModActivity(models.Model):
    obj_id = models.IntegerField(null=False)
    obj_creator = models.ForeignKey(User, related_name='target_user', on_delete=models.CASCADE)
    mod = models.ForeignKey(User, related_name='mod_user', on_delete=models.CASCADE)
    type = models.TextField(null=False)  # tipos: q (question), r (response), c (comment)
    action_date = models.DateTimeField(default=timezone.now)
    obj_text = models.TextField(max_length=512, blank=True)
    obj_extra = models.TextField(max_length=512, blank=True, null=True)

class ConfirmationCode(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    code = models.CharField(max_length=256)

class Chat(models.Model):
    participant = models.ManyToManyField(User, related_name='made_by')
    last_viewed = models.IntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)  # qualquer um dos participantes pode 'bloquear' a conversa, desativando-a

class ChatMessage(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    pub_date = models.DateTimeField(default=timezone.now)
    text = models.TextField(null=False)
    image = models.ImageField(null=True, blank=True)
    hide = models.BooleanField(default=False)
    
