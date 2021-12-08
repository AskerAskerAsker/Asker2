from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.contrib.auth import authenticate, login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime
from django.core.cache import cache
from main_app.models import UserProfile, Question, Response, Comment, Notification, Poll, PollChoice, PollVote, Ban, Report, ConfirmationCode
from main_app.templatetags.main_app_extras import fix_naturaltime, formatar_descricao, get_total_answers
from main_app.forms import UploadFileForm
from django_project import general_rules
from urllib.parse import unquote
import random
import json
import time
import os
import html
import ast


import io
from PIL import Image, ImageFile, UnidentifiedImageError, ImageSequence


def compress_animated(bio, max_size, max_frames):
    im = Image.open(bio)
    frames = list()
    min_size = min(max_size)
    frame_count = 0
    for frame in ImageSequence.Iterator(im):
        if frame_count > max_frames:
            break

        ''' PIL não salvará o canal A! Workaround: salvar em P-mode '''
        compressed_f = frame.convert('RGBA')

        alpha_mask = compressed_f.getchannel('A') # Máscara de transparência
        compressed_f = compressed_f.convert('RGB').convert('P', colors=255) # Converte para P
        mask = Image.eval(alpha_mask, lambda a: 255 if a <= 128 else 0) # Eleva pixels transparentes
        compressed_f.paste(255, mask) # Aplica a máscara
        compressed_f.info['transparency'] = 255 # O valor da transparência, na paleta, é o 255
        if max(im.size[0], im.size[1]) > min_size:
            compressed_f.thumbnail(max_size)
        frames.append(compressed_f)
        frame_count += 1
    dur = im.info['duration']
    im_final = frames[0]
    obio = io.BytesIO()
    im_final.save(obio, format='GIF', save_all=True, append_images=frames[1:], duration=dur, optimize=False, disposal=2)
    #print('Antes: {}, Depois: {}. Redução: {}%'.format(str(bio.tell()), str(obio.tell()), str(100 - int((obio.tell()*100) / bio.tell())) ))
    if obio.tell() < bio.tell():
        return obio
    return bio

def save_img_file(post_file, file_path, max_size):
    img_data = b''
    for chunk in post_file.chunks():
        img_data += chunk

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        im = Image.open(io.BytesIO(img_data))
        if im.format in ('GIF', 'WEBP') and im.is_animated:
            bio = compress_animated(io.BytesIO(img_data), max_size, 80)
            with open(file_path, 'wb+') as destination:
                destination.write(bio.getbuffer())
        else:
            im.thumbnail(max_size)
            im.save(file_path, im.format)
    except UnidentifiedImageError:
        return False
    return True


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def calculate_popular_questions():
    last_id = Question.objects.all().last().id
    id_range = (last_id - 100, last_id)
    popular_questions = Question.objects.filter(id__range=id_range).order_by('-total_views')[:40]
    return popular_questions


'''
 Essa função salva uma resposta. Sempre quando um usuário
envia uma resposta para uma pergunta, a resposta passa por aqui
para ser salva (no banco de dados).
'''
def save_answer(request):

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return HttpResponse('Você não pode responder perguntas.', content_type='text/plain')

    question = Question.objects.get(id=request.POST.get('question_id'))

    response_creator = UserProfile.objects.get(user=request.user) # criador da nova resposta.

    '''
    Testa se o usuário já respondeu a pergunta:
    '''
    if Response.objects.filter(creator=response_creator, question=question).exists():
        return HttpResponse('Você já respondeu essa pergunta.', content_type='text/plain')

    if question.creator.blocked_users.filter(username=request.user.username).exists():
        return HttpResponse('Você não pode responder essa pergunta.', content_type='text/plain')

    response = Response.objects.create(question=question, creator=response_creator, text=request.POST.get('text'))

    question.total_responses += 1
    question.save()

    response_creator.total_points += 2
    response_creator.save()

    if response_creator.user not in question.creator.silenced_users.all():
        notification = Notification.objects.create(receiver=question.creator.user,
                                                                                           type='question-answered')
        notification.prepare(response.id)
        notification.save()

    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
        f = request.FILES['file']

        now = timezone.now()

        file_name = 'rpic-{}{}'.format(now.date(), now.time())

        success = save_img_file(f, '/home/asker/asker/media/responses/' + file_name, 
(850, 850))
        if success:
            response.image = 'responses/' + file_name

        response.save()

    if request.POST.get('from') == 'index':
        return render(request, 'base/response-content-index.html', {
                'question': question,
                'ANSWER': response,
        })

    return render(request, 'base/response-content.html', {
            'question': question,
            'response': response,
    })


def index(request):

    context = {}

    if request.path == '/news':
        context['NEWS'] = True
    else:
        context['POPULAR'] = True

    context['questoes_recentes'] = Question.objects.order_by('-id')[:15]

    try:
        context['popular_questions'] = cache.get('p_questions')
        if not context['popular_questions']:
            context['popular_questions'] = calculate_popular_questions()
            cache.set('p_questions', context['popular_questions'], 600)
        context['popular_questions'] = context['popular_questions'][:15]
    except:
        pass

    if request.user.is_authenticated:
        context['user_p'] = UserProfile.objects.get(user=request.user)

    return render(request, 'index.html', context)


def question(request, question_id):
    q = Question.objects.filter(id=question_id)
    if q.exists():
        q = q.first()
        q.total_views += 1
        q.save()
    else:
        return_to = request.META.get("HTTP_REFERER") if request.META.get("HTTP_REFERER") is not None else '/'
        context = {'error': 'Pergunta não encontrada',
                                 'err_msg': 'Talvez ela tenha sido apagada pelo criador da pergunta.',
                                 'redirect': return_to}
        return render(request, 'error.html', context)

    responses = Response.objects.filter(question=q).order_by('-total_likes')

    context = {'question': q,
                                             'responses': responses}

    if not request.user.is_anonymous:
        user_p = UserProfile.objects.get(user=request.user)
        context['user_permissions'] = ast.literal_eval(user_p.permissions)
        context['user_p'] = user_p
        context['answered'] = False

        # verifica se já é possível mostrar o anúncio de notificação.
        infos = json.loads(user_p.infos)

        if 'ultima_visualizacao_de_anuncio_notificacao' in infos.keys():
            if time.time() - infos['ultima_visualizacao_de_anuncio_notificacao'] > 345600: # só mostra o anúncio em forma de notificação de 4 em 4 dias.
                context['PODE_MOSTRAR_ANUNCIO_NOTIFICACAO'] = True
                infos['ultima_visualizacao_de_anuncio_notificacao'] = time.time()
                infos['ultima_visualizacao_de_anuncio_notificacao_contagem'] += 1
        else:
            context['PODE_MOSTRAR_ANUNCIO_NOTIFICACAO'] = True
            infos['ultima_visualizacao_de_anuncio_notificacao'] = time.time()
            infos['ultima_visualizacao_de_anuncio_notificacao_contagem'] = 1

        # salva as informações (UserProfile.infos) atualizadas do usuário.
        user_p.infos = json.dumps(infos)
        user_p.save()


        for response in responses:
            if response.id == request.user.id:
                context['answered'] = True
                break

    if q.has_poll():
        context['poll'] = Poll.objects.get(question=q)
        context['poll_choices'] = PollChoice.objects.filter(poll=context['poll'])
        context['poll_votes'] = PollVote.objects.filter(poll=context['poll'])

    if request.GET.get('nabift') == 'y':
        context['NO_SHOW_ADS'] = True

    return render(request, 'question.html', context)


def like(request):

    answer_id = request.GET.get('answer_id')

    r = Response.objects.get(id=answer_id)

    q = r.question
    if r.likes.filter(username=request.user.username).exists():
        r.likes.remove(request.user)
        r.total_likes = r.likes.count()
        r.save()
        # diminui total de likes da pergunta:
        q.total_likes -= 1
        q.save()
    else:
        r.likes.add(request.user)
        r.total_likes = r.likes.count()
        r.save()
        # aumenta total de likes da pergunta:
        q.total_likes += 1
        q.save()

        if not Notification.objects.filter(type='like-in-response', liker=request.user, response=r).exists():
            # cria uma notificação para o like (quem recebeu o like será notificado):
            n = Notification.objects.create(receiver=Response.objects.get(id=answer_id).creator.user,
                                            type='like-in-response',
                                            liker=request.user,
                                            response=r)
            n.prepare(answer_id)
            n.save()

    return HttpResponse('OK', content_type='text/plain')


def delete_response(request):
    user_profile = UserProfile.objects.get(user=request.user)
    r = Response.objects.get(id=request.POST.get('response_id', request.GET.get('response_id')))

    if user_profile != r.creator:
        # checa se modera:
        if 'pap' not in ast.literal_eval(user_profile.permissions):
            return HttpResponse('NOK', content_type='text/plain')

    ''' Tira 2 pontos do criador da resposta, já que a resposta vai ser apagada por ele mesmo. '''
    creator = r.creator
    creator.total_points -= 3 # por enquanto vai tirar 3, para alertar trolls.
    creator.save()

    try:
        ''' Deleta também a imagem do sistema de arquivos para liberar espaço. '''
        os.system('rm ' + r.image.path)
    except:
        pass

    q = r.question
    q.total_responses -= 1
    q.save()
    r.delete()

    return HttpResponse('OK', content_type='text/plain')


def signin(request):

    r = request.GET.get('redirect')

    if r == None:
        r = '/'

    if request.method == 'POST':
        r = request.POST.get('redirect')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # testa se o email existe:
        if not User.objects.filter(email=email).exists():
            return render(request, 'signin.html', {'login_error': '''<div class="alert alert-danger error-alert" role="alert"><h4 class="alert-heading">Ops!</h4>Dados de login incorretos.</div>''',
                                                                                       'redirect': r})

        user = authenticate(username=User.objects.get(email=email).username, password=password)

        if user is None:
            return render(request, 'signin.html', {'login_error': '''<div class="alert alert-danger error-alert" role="alert"><h4 class="alert-heading">Ops!</h4>Dados de login incorretos.</div>''',
                                                                                       'redirect': r})
        login(request, user)
        return redirect(r)

    return render(request, 'signin.html', {'redirect': r})


def signup(request):

    '''
    Bloqueia criação de conta pelo navegador TOR.
    '''
    from .tor_ips import tor_ips
    client_ip = get_client_ip(request)
    if client_ip in tor_ips:
        return HttpResponse()


    if request.method == 'POST':
        r = request.POST.get('redirect')
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        password = request.POST.get('password')

        '''
        Validação do nome de usuário: é permitido apenas letras, números, hífens, undercores e espaços.
        '''
        # verificando caractere por caractere:
        pode = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúâêôäëïöüãõçñÁÉÍÓÚÂÊÔÄËÏÖÜÃÕÇÑ0123456789-_ '
        for ch in username:
            if ch in pode:
                continue

            html = '<div class="alert alert-danger"><p>O nome de usuário deve conter apenas caracteres alfanuméricos, hífens, underscores e espaços.</p></div>'
            return render(request, 'signup.html', {'invalid_username': html,
													 'username': username,
													 'email': email,
													 'redirect': r,
													 'username_error': ' is-invalid'})
        if '  ' in username:
            html = '<div class="alert alert-danger"><p>O nome de usuário não pode conter espaços concomitantes.</p></div>'
            return render(request, 'signup.html', {'invalid_username': html,
													 'username': username,
													 'email': email,
													 'redirect': r,
													 'username_error': ' is-invalid'})

        ''' Validação das credenciais: '''
        if not is_a_valid_user(username, email, password):
            return HttpResponse('Proibido.', content_type='text/plain')

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': '''<div class="alert alert-danger error-alert" role="alert"><h4 class="alert-heading">Ops!</h4>Nome de usuário em uso.</div>''',
                                                                                       'username': username,
                                                                                       'email': email,
                                                                                       'redirect': r,
                                                                                       'username_error': ' is-invalid'})

        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': '''<div class="alert alert-danger error-alert" role="alert"><h4 class="alert-heading">Ops!</h4>Email em uso. Faça login <a href="/signin">aqui</a>.</div>''',
                                                                                       'username': username,
                                                                                       'email': email,
                                                                                       'redirect': r,
                                                                                       'email_error': ' is-invalid'})

        u = User.objects.create_user(username=username, email=email, password=password)
        login(request, u)

        new_user_profile = UserProfile.objects.create(user=u)
        new_user_profile.ip = get_client_ip(request)
        new_user_profile.active = False
        new_user_profile.save()
        
        # geração do código de confirmação:
        from random import SystemRandom
        sr = SystemRandom()
        
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        code = ''
        i = 0
        while i < 100:
            code += sr.choice(chars)
            i += 1
        
        ConfirmationCode.objects.create(user=new_user_profile, code=code)

        # envia o e-mail de confirmação de conta.
        from django.core.mail import send_mail
        send_mail(
            'Confirmação de conta | Asker',
            f'Olá! Um Registro no Asker Foi Associada ao Seu Email. Para Confirmar Sua Conta, Copie e Cole Este URL no Seu Navegador: https://asker.fun/confirm-account?code={code}',
            'noreply.mail.asker.fun@gmail.com',
            [u.email],
            fail_silently=False,
        )

        return redirect(r)

    context = {
            'redirect': request.GET.get('redirect', '/'),
    }

    return render(request, 'signup.html', context)


def user_does_not_exists(request):
    return_to = request.META.get("HTTP_REFERER") if request.META.get("HTTP_REFERER") is not None else '/'
    context = {'error': 'Usuário não encontrado', 'err_msg': 'Este usuário não existe ou alterou seu nome.',
                       'redirect': return_to}
    return render(request, 'error.html', context)


def profile(request, username):

    username = unquote(username)

    user = User.objects.get(username=username)
    up = UserProfile.objects.get(user=user)

    context = {}

    if request.user.is_authenticated:
        context['permissoes_usuario_logado'] = ast.literal_eval(UserProfile.objects.get(user=request.user).permissions)

    if request.user.username == username:
        user_p = UserProfile.objects.get(user=request.user)
        user_p.ip = get_client_ip(request)
        user_p.save()

    if request.user.username != username:
        up.total_views += 1
        up.save()

    context['user_p'] = up
    context['change_profile_picture_form'] = UploadFileForm()

    try:
        if request.user.username == username or not up.hide_activity or 'pap' in context['permissoes_usuario_logado'] or request.user.is_superuser:
            q_page = request.GET.get('q-page', 1)
            r_page = request.GET.get('r-page', 1)

            context['questions'] = Paginator(Question.objects.filter(creator=up).order_by('-pub_date'), 10).page(q_page).object_list
            context['responses'] = Paginator(Response.objects.filter(creator=up).order_by('-pub_date'), 10).page(r_page).object_list
    except KeyError:
        pass

    return render(request, 'profile.html', context)


def ask(request):

    if request.user.is_anonymous:
        return redirect('/question/%d' % Question.objects.all().last().id)

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/question/%d' % Question.objects.all().last().id)

    '''
    Controle de spam
    '''
    try:
        last_q = Question.objects.filter(creator=UserProfile.objects.get(user=request.user))
        last_q = last_q[last_q.count()-1] # pega a última questão feita pelo usuário.
        if (timezone.now() - last_q.pub_date).seconds < 25:
            return_to = request.META.get("HTTP_REFERER") if request.META.get("HTTP_REFERER") is not None else '/'
            context = {'error': 'Ação não autorizada',
                               'err_msg': 'Você deve esperar {} segundos para perguntar novamente.'.format(25 - (timezone.now() - last_q.pub_date).seconds),
                               'redirect': return_to}
            return render(request, 'error.html', context)
    except:
        pass

    if request.method == 'POST':
        description = request.POST.get('description')
        description = description.replace('\r', '')
        description = html.escape(description)

        text = request.POST.get('question')

        if len(text) > 181:
            return HttpResponse('Proibido.', content_type='text/plain')

        q = Question.objects.create(creator=UserProfile.objects.get(user=request.user), text=text, description=description.replace('\\', '\\\\'))

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']

            file_name = 'qpic-{}{}'.format(timezone.now().date(), timezone.now().time())

            success = save_img_file(f, '/home/asker/asker/media/questions/' + 
file_name, (850, 850))
            if success:
                q.image = 'questions/' + file_name

            q.save()

        ccount = request.POST.get('choices-count')
        if ccount.isdigit():
            is_multichoice = request.POST.get('is-multichoice') is not None
            ccount = int(ccount)
            if ccount <= general_rules.MAXIMUM_POLL_CHOICES and ccount > 1: # Proteção de POST manual
                qpoll = Poll.objects.create(question=q, is_anonymous=True, multichoice=is_multichoice)
                for i in range(1, ccount + 1):
                    choice = request.POST.get('choice-' + str(i))
                    if len(choice) <= 60 and len(choice) >= 1 and choice.replace(' ', '') != '':
                        PollChoice.objects.create(poll=qpoll, text=choice)
                    else:
                        PollChoice.objects.create(poll=qpoll, text="...")


        u = UserProfile.objects.get(user=request.user)
        u.total_points += 1
        u.save()

        return redirect('/question/' + str(q.id))

    return render(request, 'ask.html', {'user_p': UserProfile.objects.get(user=request.user)})


def logout(request):
    django_logout(request)
    return redirect('/')


def notification(request):

    if request.user.is_anonymous:
        return redirect('/question/%d' % Question.objects.all().last().id)

    p = Paginator(Notification.objects.filter(receiver=request.user).order_by('-creation_date'), 15)

    page = request.GET.get('page', 1)

    context = {
            'notifications': p.page(page),
    }

    up = UserProfile.objects.get(user=request.user)
    if up.new_notifications > 0:
        up.new_notifications = 0
        up.save()

    return render(request, 'notification.html', context)


def comment(request):

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return HttpResponse('Você não pode comentar.', content_type='text/plain')

    comment = Comment.objects.create(response=Response.objects.get(id=request.POST.get('response_id')),
                                                                                             creator=request.user,
                                                                                             text=html.escape(request.POST.get('text')),
                                                                                             pub_date=timezone.now())

    n = Notification.objects.create(receiver=comment.response.creator.user,
                                                                                                                    type='comment-in-response',
                                                                                                                    text='<p><a href="/user/{}">{}</a> comentou na sua resposta na pergunta: <a href="/question/{}">"{}"</a></p>'.format(comment.creator.username, comment.creator.username, comment.response.question.id, comment.response.question.text))
    n.prepare()

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
            '''.format(comment.creator.username, UserProfile.objects.get(user=request.user).avatar.url, comment.creator.username, naturaltime(comment.pub_date), comment.id, comment.text.replace('\n', '<br>'))

    return HttpResponse(comment_creator_template)


def rank(request):
    rank = UserProfile.objects.order_by('-total_points')[:50]
    count = 0
    for user in rank:
        count += 1
        user.rank = count
    return render(request,'rank.html',{'rank':rank})


def edit_response(request):

    response = Response.objects.get(creator=UserProfile.objects.get(user=request.user), id=request.POST.get('response_id'))
    response.text = request.POST.get('text')
    response.save()

    return redirect('/question/' + str(response.question.id))


def delete_question(request):
    
    user_profile = UserProfile.objects.get(user=request.user)
    
    question = Question.objects.get(id=request.POST.get('question_id'))
    if (question.creator.user == request.user) or ('pap' in ast.literal_eval(user_profile.permissions)):

        '''
        Deleta também a imagem do sistema de arquivos:
        '''

        if question.image:
            os.system('rm ' + question.image.path)

        question.delete()
    return redirect('/news')


def delete_response_pap(request):
    # delete_response alternativo, so funciona se for pap, caso contrario, buga

    user_profile = UserProfile.objects.get(user=request.user)

    q_id = r.question.id

    if 'pap' in ast.literal_eval(user_profile.permissions):

        r = Response.objects.get(id=request.POST.get('response_id'))
        r.delete()

    return redirect(f'/question/{q_id}')


def delete_comment(request):
    c = Comment.objects.get(id=request.GET.get('comment_id'))

    if request.user != c.creator:
        return HttpResponse('Proibido.', content_type='text/plain')

    c.delete()
    return HttpResponse('OK', content_type='text/plain')


def edit_profile(request, username):

    from urllib.parse import unquote
    username = unquote(username)

    if request.method == 'POST':
        if request.POST.get('type') == 'profile-pic':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():

                u = UserProfile.objects.get(user=request.user)

                '''
                Já que vai trocar de avatar, apaga o avatar antigo se tiver.
                '''
                if u.avatar and u.avatar.name != 'avatars/default-avatar.png':
                    os.system('rm ' + u.avatar.path)

                f = request.FILES['file']
                '''
                Nome da imagem do usuário no sistema de arquivos: nome de usuário atual, data de alteração e horário da alteração.
                '''
                file_name = '{}-{}-{}'.format(request.user.username, timezone.now().date(), timezone.now().time())

                success = save_img_file(f, '/home/asker/asker/media/avatars/' +
file_name, (192, 192))
                if not success:
                    return redirect('/user/' + request.user.username + '/edit')

                u.avatar = 'avatars/' + file_name
                u.save()
            return redirect('/user/' + username)
        if request.POST.get('type') == 'bio':
            u = UserProfile.objects.get(user=request.user)
            u.bio = request.POST.get('bio')
            u.save()
            return redirect('/user/' + username)
        if request.POST.get('type') == 'username':

            username = request.POST.get('username')

            '''
            Validação do nome de usuário: é permitido apenas letras, números, hífens, undercores e espaços.
            '''
            # verificando caractere por caractere:
            pode = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ '
            for ch in username:
                if ch in pode:
                    continue

                html = '<div class="alert alert-danger"><p>O nome de usuário deve conter apenas caracteres alfanuméricos, hífens, underscores e espaços.</p></div>'
                return render(request, 'edit-profile.html', {'invalid_username_text': html,
                                                             'username': username,
                                                             'invalid_username': ' is-invalid'})

            if '  ' in username:
                html = '<div class="alert alert-danger"><p>O nome de usuário não pode conter espaços concomitantes.</p></div>'
                return render(request, 'edit-profile.html', {'invalid_username_text': html,
                                                             'username': username,
                                                             'invalid_username': ' is-invalid'})

            if len(username) > 30:
                return HttpResponse('Erro.', content_type='text/plain')

            if User.objects.filter(username=username).exists():
                return render(request, 'edit-profile.html', {'user_p': UserProfile.objects.get(user=User.objects.get(username=username)), 'username_display': 'block', 'invalid_username': ' is-invalid'})

            password = request.POST.get('password')
            user = authenticate(username=request.user.username, password=password)
            if user is None:
                if not User.objects.filter(username=request.POST.get('username')).exists():
                    try:
                        return render(request, 'edit-profile.html', {'user_p': UserProfile.objects.get(user=User.objects.get(username=username)), 'password_display': 'block', 'invalid_password': ' is-invalid'})
                    except:
                        return render(request, 'edit-profile.html',
                                                  {'user_p': UserProfile.objects.get(user=User.objects.get(username=request.user.username)),
                                                   'password_display': 'block', 'invalid_password': ' is-invalid'})
            user.username = request.POST.get('username').strip()
            user.save()
            login(request, user)
            return redirect('/user/' + user.username)
        if request.POST.get('type') == 'privacy':
            u = UserProfile.objects.get(user=request.user)
            if request.POST.get('hide-activity') is not None:
                u.hide_activity = True
            else:
                u.hide_activity = False
            u.save()
            return redirect('/user/' + username)

    return render(request, 'edit-profile.html', {'user_p': UserProfile.objects.get(user=User.objects.get(username=username))})


def block(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    if u_p.blocked_users.filter(username=username).exists():
        u_p.blocked_users.remove(User.objects.get(username=username))
        return HttpResponse('Bloquear', content_type='text/plain')
    u_p.blocked_users.add(User.objects.get(username=username))
    return HttpResponse('Bloqueado', content_type='text/plain')

def silence(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    if username == u_p.user.username:
        return HttpResponse('Proibido', content_type='text/plain')
    if u_p.silenced_users.filter(username=username).exists():
        u_p.silenced_users.remove(User.objects.get(username=username))
        return HttpResponse('Removed', content_type='text/plain')
    u_p.silenced_users.add(User.objects.get(username=username))
    return HttpResponse('Added', content_type='text/plain')

''' A função abaixo faz a validação das credenciais de novos usuários. '''
def is_a_valid_user(username, email, password):
    if len(username) > 30:
        return False
    elif len(email) > 60:
        return False
    elif len(password) < 6 or len(password) > 256:
        return False
    return True


''' A função abaixo faz a validação de um novo comentário. '''
def is_a_valid_comment(text):
    if len(text) > 300:
        return False
    return True


def choose_best_answer(request):

    answer_id = request.GET.get('answer_id')
    r = Response.objects.get(id=answer_id)
    q = r.question
    user = request.user
    quser = q.creator
    if user.id == quser.id and r.creator.user.id == user.id:
        return HttpResponse('Proibido.', content_type='text/plain')
    if r.creator.user.id == quser.id:
        return HttpResponse('Proibido.', content_type='text/plain')
    if q.may_choose_answer():
        q.best_answer = answer_id
        q.save()
        n = Notification.objects.create(receiver=r.creator.user, type='got-best-answer', response=r)
        n.prepare(answer_id)
        n.save()
        rcuserp = UserProfile.objects.get(user=r.creator.user)
        quserp = UserProfile.objects.get(user=request.user)
        rcuserp.total_points += 10
        quserp.total_points += 2
        rcuserp.save()
        quserp.save()
    #else: # P/ testes rápidos - desfaz a MR
    #    q.best_answer = None
    #    q.save()

    return HttpResponse('OK', content_type='text/plain')


def delete_account(request):
    if not request.user.is_authenticated:
        return HttpResponse('Proibido.', content_type='text/plain')

    if request.method == 'POST':
        try:
            user = request.user
            user.delete()
        except:
            return False

    return render(request, 'delete-account.html')


def rules(request):
    return render(request, 'rules.html')


def activity(request):
    return redirect('/user/' + request.user.username)


def vote_on_poll(request):
    if request.method != 'POST':
        return HttpResponse('Ok.', content_type='text/plain')

    poll_id = request.POST.get('poll')
    user_choices = request.POST.getlist('choices[]')
    p = Poll.objects.get(id=poll_id)
    has_voted = PollVote.objects.filter(poll=p, voter=request.user).exists()

    if has_voted:
        return HttpResponse('Proibido.', content_type='text/plain')
    if not p.multichoice:
        if len(user_choices) > 1:
            return HttpResponse('Proibido.', content_type='text/plain')
    if len(user_choices) > general_rules.MAXIMUM_POLL_CHOICES:
        return HttpResponse('Proibido.', content_type='text/plain')
    if not p.may_vote():
        return HttpResponse('Proibido.', content_type='text/plain')

    for choice in user_choices:
        c_query = PollChoice.objects.filter(id=choice, poll=p) # pollchoice.poll == req.poll (poll=p) p/ evitar manipulação de POST
        if c_query.exists():
            c = c_query[0]
            PollVote.objects.create(poll=p, choice=c, voter=request.user)
            c.votes += 1
            c.save()

    return HttpResponse('Ok.', content_type='text/plain')

def undo_vote_on_poll(request):
    if request.method != 'POST':
        return HttpResponse('Ok.', content_type='text/plain')
    poll_id = request.POST.get('poll')
    p = Poll.objects.get(id=poll_id)
    votes = PollVote.objects.filter(poll=p, voter=request.user)

    if not p.may_vote():
        return HttpResponse('Proibido.', content_type='text/plain')

    for vote in votes:
        c = vote.choice
        c.votes -= 1
        c.save()
        vote.delete()

    return HttpResponse('Ok.', content_type='text/plain')


def more_popular_questions(request):

    page = request.GET.get('page')

    questions = cache.get('p_questions')

    if not questions:
        questions = calculate_popular_questions()
        cache.set('p_questions', questions, 600)

    paginator = Paginator(questions, 15)

    try:
        questions = paginator.page(page)
    except EmptyPage:
        return JsonResponse({'empty': 'true'})

    para_retornar = []

    if request.user.is_anonymous:
        for q in questions:
            para_retornar.append(
              {
                "id": q.id,
                "text": q.text,
                "description": q.description,
                "total_answers": q.total_responses,
                "pub_date": fix_naturaltime(naturaltime(q.pub_date)),
                "creator": q.creator.user.username,
                "user_answer": "False",
              },
            )
    else:
        for q in questions:
            r = Response.objects.filter(creator=UserProfile.objects.get(user=request.user), question=q)
            answer = 'False' if not r.exists() else r[0].text

            para_retornar.append(
              {
                "id": q.id,
                "text": q.text,
                "description": q.description,
                "total_answers": q.total_responses,
                "pub_date": fix_naturaltime(naturaltime(q.pub_date)),
                "creator": q.creator.user.username,
                "user_answer": answer,
              },
            )

    return JsonResponse(para_retornar, safe=False)


def more_questions(request):

    id_de_inicio = int(request.GET.get('id_de_inicio')) - 20
    questions = list(Question.objects.filter(id__range=(id_de_inicio, id_de_inicio + 20)))
    questions.reverse()

    para_retornar = []

    if request.user.is_anonymous:
        for q in questions:
            para_retornar.append(
                    {
                            "id": q.id,
                            "text": q.text,
                            "description": formatar_descricao(q.description),
                            "total_answers": get_total_answers(q),
                            "pub_date": fix_naturaltime(naturaltime(q.pub_date)),
                            "creator": q.creator.user.username,
                            "user_answer": "False",
                            "question_creator_avatar": q.creator.avatar.url,
                    },
            )
    else:
        for q in questions:
            r = Response.objects.filter(creator=UserProfile.objects.get(user=request.user), question=q)
            answer = 'False' if not r.exists() else r[0].text

            para_retornar.append(
                    {
                            "id": q.id,
                            "text": q.text,
                            "description": formatar_descricao(q.description),
                            "total_answers": get_total_answers(q),
                            "pub_date": fix_naturaltime(naturaltime(q.pub_date)),
                            "creator": q.creator.user.username,
                            "user_answer": answer,
                            "question_creator_avatar": q.creator.avatar.url,
                    },
            )

    return JsonResponse(para_retornar, safe=False)


def get_more_questions(request):
    page = request.GET.get('q_page', 2)
    user_id = request.GET.get('user_id')
    target = UserProfile.objects.get(user=User.objects.get(id=user_id))
    if target.hide_activity and not request.user.is_superuser and 'pap' not in ast.literal_eval(UserProfile.objects.get(user=request.user).permissions):
        if target.user.id != request.user.id:
            return 'Proibido.'
    q = Question.objects.filter(creator=target).order_by('-pub_date')

    p = Paginator(q, 10)

    json = {
    }

    json['questions'] = {}

    count = 1

    try:
        p.page(page)
    except:
        return HttpResponse(False)

    for q in p.page(page):
        if target.user.id == request.user.id:
            best_answer = q.best_answer
        else:
            best_answer = -1
        json['questions'][count] = {
                'text': q.text,
                'id': q.id,
                'naturalday': naturalday(q.pub_date),
                'best_answer': best_answer
        }
        count += 1

    json['has_next'] = p.page(page).has_next()

    return JsonResponse(json)


def get_more_responses(request):
    page = request.GET.get('r_page', 2)
    user_id = request.GET.get('user_id')
    target = UserProfile.objects.get(user=User.objects.get(id=user_id))
    if target.hide_activity and not request.user.is_superuser and 'pap' not in ast.literal_eval(UserProfile.objects.get(user=request.user).permissions):
        if target.user.id != request.user.id:
            return 'Proibido.'
    r = Response.objects.filter(creator=target).order_by('-pub_date')
    p = Paginator(r, 10)

    json = {
    }

    json['responses'] = {}

    count = 1
    for r in p.page(page):
        json['responses'][count] = {
                'text': r.text,
                'question_text': r.question.text,
                'question_id': r.question.id,
                'best_answer': r.id == r.question.best_answer,
                'creator': r.question.creator.user.username,
                'naturalday': naturalday(r.question.pub_date)
        }
        count += 1

    json['has_next'] = p.page(page).has_next()

    return JsonResponse(json)


def report(request):
    type = request.GET.get('type')
    obj_id = request.GET.get('obj_id')
    reporter = request.user
    
    report = Report.objects.filter(obj_id=obj_id)
    
    if report.exists():
        report = report.first()
    else:
        report = Report.objects.create(type=type, obj_id=obj_id)
    
    if not report.reporters.filter(username=reporter.username).exists():
        report.reporters.add(reporter)
        report.total_reports += 1
        report.save()
    
    return HttpResponse('OK')


def manage_reports(request):
    
    if not request.user.is_superuser:
        return HttpResponse('Você está logado como {}. Este usuário não tem permissão administrativa.'.format(request.user.username))
    
    reports = list(Report.objects.all())
    reports.sort(key=lambda x: x.total_reports, reverse=True)
    
    context = {
        'reports': reports,
    }
    
    return render(request, 'manage_reports.html', context)


def delete_report_and_obj(request):
    if not request.user.is_superuser:
        return HttpResponse('Proibido.', content_type='text/plain')
    
    report = Report.objects.get(obj_id=request.GET.get('obj_id'))
    
    if report.type == 'q':
        '''Tratando report do tipo "pergunta" (obj_id é o ID de uma pergunta, a pergunta foi reportada).'''
        q = Question.objects.filter(id=report.obj_id)
        if q.exists():
            q = q.first()
            q.delete()
        report.delete()
    
    return HttpResponse('OK', content_type='text/plain')


def delete_report(request):
    report = Report.objects.get(obj_id=request.GET.get('obj_id'))
    report.delete()
    return HttpResponse('OK', content_type='text/plain')


def confirm_account(request):
    code = request.GET.get('code')
    result = ConfirmationCode.objects.filter(code=code)
    
    if result.exists():
        user_profile = result.first().user
        user_profile.active = True
        user_profile.save()
        result.delete()
        return redirect('/')
    
    return HttpResponse('Erro.')
