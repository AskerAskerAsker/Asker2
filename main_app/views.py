from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.contrib.auth import authenticate, login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime
from django.core.cache import cache
from main_app.models import UserProfile, Question, Response, Comment, Notification, Poll, PollChoice, PollVote, Ban, Report, ConfirmationCode, ModActivity, Chat, ChatMessage, UserIP, Setting
from main_app.templatetags.main_app_extras import fix_naturaltime, formatar_descricao, get_total_answers, chat_counterpart
from main_app.forms import UploadFileForm
from django_project import general_rules
from urllib.parse import unquote
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
import secret
import random
import json
import time
import os
import html
import ast
import io
import subprocess
import ipinfo
from PIL import Image, ImageFile, UnidentifiedImageError, ImageSequence, ImageOps
from random import SystemRandom
from django.core.mail import send_mail

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

        alpha_mask = compressed_f.getchannel('A')  # Máscara de transparência
        compressed_f = compressed_f.convert('RGB').convert('P', colors=255)  # Converte para P
        mask = Image.eval(alpha_mask, lambda a: 255 if a <= 128 else 0)  # Eleva pixels transparentes
        compressed_f.paste(255, mask)  # Aplica a máscara
        compressed_f.info['transparency'] = 255  # O valor da transparência, na paleta, é o 255
        if max(im.size[0], im.size[1]) > min_size:
            compressed_f.thumbnail(max_size)
        frames.append(compressed_f)
        frame_count += 1
    dur = im.info['duration']
    im_final = frames[0]
    obio = io.BytesIO()
    im_final.save(obio, format='GIF', save_all=True, append_images=frames[1:], duration=dur, optimize=False, disposal=2)
    # print('Antes: {}, Depois: {}. Redução: {}%'.format(str(bio.tell()), str(obio.tell()), str(100 - int((obio.tell()*100) / bio.tell())) ))
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
        final_path = file_path + '.' + im.format
        if im.format in ('GIF', 'WEBP') and im.is_animated:
            bio = compress_animated(io.BytesIO(img_data), max_size, 80)
            with open(final_path, 'wb+') as destination:
                destination.write(bio.getbuffer())
        else:
            im_transp = ImageOps.exif_transpose(im)
            im = im_transp or im
            im.thumbnail(max_size)
            im.save(final_path, im.format)
    except UnidentifiedImageError:
        return False
    return final_path[final_path.find('media/') + len('media/'):]

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def calculate_popular_questions():
    last_id = Question.objects.all().last().id
    id_range = (last_id - 150, last_id)
    popular_questions = Question.objects.filter(id__range=id_range, active=True).order_by('-total_responses')[:40]
    return popular_questions

def register_ip(ip_addr):
    h = ipinfo.getHandler(secret.IPINFO_TOKEN)
    details = h.getDetails(ip_addr)
    UserIP.objects.create(ip=ip_addr, type=details.country)

def toggle_ip_check(request):
    user_p = UserProfile.objects.get(user=request.user)
    permissions = ast.literal_eval(user_p.permissions)
    if not request.user.is_superuser:
        if 'pap' not in permissions:
            return HttpResponse('OK')

    try:
        check_ip = Setting.objects.get(setting='check_ip_location')
    except Setting.DoesNotExist:
        check_ip = Setting.objects.create(setting='check_ip_location', value=1)
    check_ip.value = 1 - check_ip.value
    check_ip.save()

    return HttpResponse(str(check_ip.value == 1), content_type='text/plain')

def should_ip_check():
    try:
        check_ip = Setting.objects.get(setting='check_ip_location').value
        return check_ip == True
    except Setting.DoesNotExist:
        return False

def validate_ip(request):
    try:
        uip_obj = UserIP.objects.get(ip=get_client_ip(request))
    except UserIP.DoesNotExist:
        uip_obj = None
    if not uip_obj:
        register_ip(get_client_ip(request))
        uip_obj = UserIP.objects.get(ip=get_client_ip(request))
    if uip_obj.type not in general_rules.ALLOWED_IP_TYPES:
        return False
    return True

def save_answer(request):
    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return HttpResponse('Você não pode responder perguntas.', content_type='text/plain', status=406)
    elif should_ip_check():
        if not validate_ip(request):
            return HttpResponse('Você não pode responder perguntas.', content_type='text/plain', status=406)
    try:
        q = Question.objects.get(id=request.POST.get('question_id'))
    except Question.DoesNotExist:
        q = None
    if q is None or not q.active:
        return HttpResponse('Pergunta não encontrada. Talvez ela tenha sido apagada pelo criador da pergunta.',
                            content_type='text/plain', status=406)

    response_creator = UserProfile.objects.get(user=request.user)  # criador da nova resposta.

    '''
    Testa se o usuário já respondeu a pergunta:
    '''
    if Response.objects.filter(creator=response_creator, question=q).exists():
        return HttpResponse('Você já respondeu essa pergunta.', content_type='text/plain', status=406)

    if q.creator.blocked_users.filter(username=request.user.username).exists():
        return HttpResponse('Você não pode responder essa pergunta.', content_type='text/plain', status=406)

    response = Response.objects.create(question=q, creator=response_creator, text=request.POST.get('text'))

    q.total_responses += 1
    q.save()

    response_creator.total_points += 2
    response_creator.save()

    if response_creator.user not in q.creator.silenced_users.all():
        n = Notification.objects.create(receiver=q.creator.user, type='question-answered')
        n.prepare(response.id)
        n.save()

    form = UploadFileForm(request.POST, request.FILES)
    if form.is_valid():
        f = request.FILES['file']

        now = timezone.now()

        file_name = 'rpic-{}{}'.format(now.date(), now.time()).replace(':', '')

        success = save_img_file(f, 'media/responses/' + file_name, (850, 850))
        if success:
            response.image = success

        response.save()

    if request.POST.get('from') == 'index':
        return render(request, 'base/response-content-index.html', {
            'question': q,
            'ANSWER': response,
        })

    return render(request, 'base/response-content.html', {
        'question': q,
        'responses': Response.objects.filter(id=response.id),
        'user_p': response_creator,
        'user_permissions': ast.literal_eval(response_creator.permissions),
    })

def index(request):
    context = dict()

    context['initial'] = 'popular'
    if request.path == '/news':
        context['initial'] = 'recentes'
    elif request.path == '/feed':
        if request.user.is_authenticated:
            context['initial'] = 'feed'

    try:
        context['popular_questions'] = cache.get('p_questions')
        if not context['popular_questions']:
            context['popular_questions'] = calculate_popular_questions()
            cache.set('p_questions', context['popular_questions'], 600)
        context['popular_questions'] = context['popular_questions'][:15]
    except:
        pass

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up
        context['feed_questions'] = get_feed_content(up, 1, 0)

    return render(request, 'index.html', context)

def question(request, question_id):
    try:
        q = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        q = None
        
    context = dict()
    silenced = []
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_permissions'] = ast.literal_eval(up.permissions)
        context['user_p'] = up
        silenced = [UserProfile.objects.get(user=u) for u in up.silenced_users.all()]

    if q is None or not q.active:
        return_to = request.META.get("HTTP_REFERER") if request.META.get("HTTP_REFERER") is not None else '/'
        context = {'error': 'Pergunta não encontrada',
                   'err_msg': 'Talvez ela tenha sido apagada pelo criador da pergunta.', 'redirect': return_to}
        return render(request, 'error.html', context)

    q.total_views += 1
    q.save()
    responses = Response.objects.filter(question=q, active=True).exclude(creator__in=silenced).order_by('-total_likes', 'id')

    context['question'] = q
    context['responses'] = responses

    if request.user.is_authenticated:
        context['answered'] = False
        for response in responses:
            if response.id == request.user.id:
                context['answered'] = True
                break

    if q.has_poll():
        context['poll'] = Poll.objects.get(question=q)
        context['poll_choices'] = PollChoice.objects.filter(poll=context['poll'])
        context['poll_votes'] = PollVote.objects.filter(poll=context['poll'])

    return render(request, 'question.html', context)

def like(request):
    answer_id = request.GET.get('answer_id')
    r = Response.objects.get(id=answer_id)
    if r.creator.user == request.user:
        return HttpResponse('Proibido', content_type='text/plain')

    q = r.question
    if r.likes.filter(username=request.user.username).exists():
        r.likes.remove(request.user)
        r.total_likes = r.likes.count()
        r.save()
        # diminui total de likes da pergunta:
        q.total_likes -= 1
        q.save()
        try:
            n = Notification.objects.get(type='like-in-response', liker=request.user, response=r)
            n.activate(False)
        except Notification.DoesNotExist:
            pass
    else:
        r.likes.add(request.user)
        r.total_likes = r.likes.count()
        r.save()
        # aumenta total de likes da pergunta:
        q.total_likes += 1
        q.save()

        try:
            n = Notification.objects.get(type='like-in-response', liker=request.user, response=r)
            n.activate()
        except Notification.DoesNotExist:
            n = Notification.objects.create(receiver=Response.objects.get(id=answer_id).creator.user,
                                            type='like-in-response', liker=request.user, response=r)
            n.prepare(answer_id)
            n.save()

    return HttpResponse('OK', content_type='text/plain')

def delete_response(request):
    user_profile = UserProfile.objects.get(user=request.user)
    r = Response.objects.get(id=request.POST.get('response_id', request.GET.get('response_id')))
    creator = r.creator
    q = r.question

    q.total_responses -= 1
    q.save()

    if user_profile != r.creator:
        # checa se modera:
        if 'pap' in ast.literal_eval(user_profile.permissions):
            ModActivity.objects.create(obj_id=r.id, obj_creator=creator.user, mod=user_profile.user,
                                       type='r', obj_text=r.text, obj_extra=q.text)
            r.active = False
            r.save()
            return HttpResponse('OK', content_type='text/plain')
        return HttpResponse('NOK', content_type='text/plain')

    creator.total_points -= 3
    creator.save()

    try:
        os.system('rm ' + r.image.path)
    except:
        pass
    r.delete()
    return HttpResponse('OK', content_type='text/plain')

def signin(request):
    r = request.GET.get('redirect', '/')

    if request.method == 'POST':
        r = request.POST.get('redirect')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # testa se o email existe:
        if not User.objects.filter(email=email).exists():
            return render(request, 'auth.html', {'error': 'Ops! Dados de login incorretos.', 'redirect': r,
                                                 'type': 'signin'})

        user = authenticate(username=User.objects.get(email=email).username, password=password)

        if user is None:
            return render(request, 'auth.html', {'error': 'Ops! Dados de login incorretos.', 'redirect': r,
                                                 'type': 'signin'})
        login(request, user)
        return redirect(r)

    return render(request, 'auth.html', {'redirect': r})

def signup(request):
    from .tor_ips import tor_ips
    client_ip = get_client_ip(request)
    if client_ip in tor_ips:
        return HttpResponse()

    if request.method == 'POST':
        r = request.POST.get('redirect', '/')
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

            html = 'O nome de usuário deve conter apenas caracteres alfanuméricos, hífens, underscores e espaços.'
            return render(request, 'auth.html', {'error': html, 'username': username, 'email': email,
                                                 'redirect': r, 'username_error': ' is-invalid', 'type': 'signup'})
        if '  ' in username:
            html = 'O nome de usuário não pode conter espaços concomitantes.'
            return render(request, 'auth.html', {'error': html, 'username': username, 'email': email,
                                                 'redirect': r, 'username_error': ' is-invalid', 'type': 'signup'})

        ''' Validação das credenciais: '''
        is_valid = is_a_valid_user(username, email, password)
        if not is_valid[0]:
            msg = 'O {} inserido é inválido. Por favor, tente novamente.'.format(is_valid[1])
            return render(request, 'auth.html', {'error': msg, 'username': username, 'email': email,
                                                 'redirect': r, 'username_error': ' is-invalid', 'type': 'signup'})

        if User.objects.filter(username=username).exists():
            return render(request, 'auth.html', {
                'error': 'Ops! Nome de usuário em uso. Por favor, escolha outro.',
                'username': username, 'type': 'signup', 'email': email, 'redirect': r, 'username_error': ' is-invalid'})

        if User.objects.filter(email=email).exists():
            return render(request, 'auth.html', {
                'error': 'Email em uso. Por favor, faça login ou recupere sua senha.',
                'username': username, 'email': email, 'redirect': r, 'type': 'signup', 'email_error': ' is-invalid'})

        u = User.objects.create_user(username=username, email=email, password=password)
        login(request, u)

        new_user_profile = UserProfile.objects.create(user=u)
        new_user_profile.ip = get_client_ip(request)
        new_user_profile.cover_photo = None
        new_user_profile.active = True
        new_user_profile.save()

        return redirect(r)

    context = {
        'redirect': request.GET.get('redirect', '/'),
    }

    return render(request, 'auth.html', context)

def recover(request):
    if request.method == 'POST':
        email = request.POST.get('email', '')
        r = request.POST.get('redirect', '/')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user is not None:
            up = UserProfile.objects.get(user=user)
            sr = SystemRandom()
            chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

            code = ''
            i = 0
            while i < general_rules.RECOVER_PW_CODE_LENGTH:
                code += sr.choice(chars)
                i += 1

            try:
                cc = ConfirmationCode.objects.get(user=up)
                cc.code = code
                cc.retries += 1
                cc.save()
            except ConfirmationCode.DoesNotExist:
                cc = ConfirmationCode.objects.create(user=up, code=code, retries=1)

            if cc.retries < 4:
                mail_text = f'Olá, {user.username}! Você solicitou a alteração da senha da sua conta Asker. ' +\
                            f'Para continuar, acesse o endereço a seguir: https://asker.fun/auth?t=change_pw&c={code}'
                send_mail('Alteração de senha | Asker', mail_text, 'noreply.mail.asker.fun@gmail.com', [user.email],
                          fail_silently=False)
            else:
                return render(request, 'auth.html', {
                    'error': 'Limite de tentativas de alteração de senha excedido. Contate a administração para continuar.',
                    'email': email, 'redirect': r, 'type': 'recover'})

        return render(request, 'auth.html', {
            'msg': 'Se o endereço de e-mail estiver cadastrado, enviaremos um e-mail com um endereço. Acesse-o para alterar sua senha.',
            'email': email, 'redirect': r, 'type': 'recover'})

def change_password(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        pw = request.POST.get('p')
        r = request.POST.get('redirect')
        confirm_pw = request.POST.get('confirm')

        if pw != confirm_pw:
            return render(request, 'auth.html', {
                'error': 'As senhas digitadas são conferem. Por favor, tente novamente.',
                'redirect': r, 'type': 'change_pw', 'code': code})

        try:
            cc = ConfirmationCode.objects.get(code=code)
        except ConfirmationCode.DoesNotExist:
            return render(request, 'auth.html', {'error': 'Um erro inesperado ocorreu. Por favor, tente novamente.',
                                                 'redirect': r, 'type': 'recover'})

        user = cc.user.user
        user.set_password(pw)
        user.save()
        return render(request, 'auth.html', {
            'msg': 'Senha alterada com sucesso. Faça login para continuar.', 'redirect': r, 'type': 'signin'})

def auth(request):
    if request.method == 'POST':
        type = request.POST.get('type')
        if type == 'signup':
            return signup(request)
        elif type == 'signin':
            return signin(request)
        elif type == 'recover':
            return recover(request)
        elif type == 'change_pw':
            return change_password(request)

    type = request.GET.get('t', 'signin')
    r = request.GET.get('redirect', '/')
    context = {'type': type, 'redirect': r}

    if type == 'change_pw':
        code = request.GET.get('c')
        context['code'] = code
        if not code:
            context['type'] = 'recover'
            return render(request, 'auth.html', context)

        if len(code) != general_rules.RECOVER_PW_CODE_LENGTH:
            return render(request, 'auth.html', {
                'error': 'Seu código não é válido. Por favor, tente novamente.',
                'redirect': r, 'type': 'recover'})

        try:
            ConfirmationCode.objects.get(code=code)
        except ConfirmationCode.DoesNotExist:
            return render(request, 'auth.html', {
                'error': 'Seu código não é válido. Por favor, tente novamente.',
                'redirect': r, 'type': 'recover'})

    return render(request, 'auth.html', context)

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

    context['followers'] = user.followed_by.all()

    if request.user.username == username:
        user_p = UserProfile.objects.get(user=request.user)
        user_p.ip = get_client_ip(request)
        user_p.save()

        fq_page = request.GET.get('fq-page', 1)
        context['followed_questions'] = Paginator(user_p.followed_questions.filter(
            active=True).order_by('-id'), 10).page(fq_page).object_list

    if request.user.username != username:
        up.total_views += 1
        up.save()

    if request.user.is_authenticated:
        context['user_p'] = UserProfile.objects.get(user=request.user)

    context['target_user_p'] = up
    context['change_profile_picture_form'] = UploadFileForm()

    try:
        if request.user.username == username or not up.hide_activity or 'pap' in context['permissoes_usuario_logado'] or request.user.is_superuser:
            q_page = request.GET.get('q-page', 1)
            r_page = request.GET.get('r-page', 1)

            context['questions'] = Paginator(Question.objects.filter(
                creator=up, active=True).order_by('-pub_date'), 10).page(q_page).object_list
            context['responses'] = Paginator(Response.objects.filter(
                creator=up, active=True).order_by('-pub_date'), 10).page(r_page).object_list
    except KeyError:
        pass

    context['total_followers'] = up.user.followed_by.all().count()

    return render(request, 'profile.html', context)

def ask(request):
    if request.user.is_anonymous:
        return redirect('/news')

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/news')
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/news')

    '''
    Controle de spam
    '''
    try:
        last_q = Question.objects.filter(creator=UserProfile.objects.get(user=request.user))
        last_q = last_q[last_q.count() - 1]  # pega a última questão feita pelo usuário.
        wait_count = (timezone.now() - last_q.pub_date).seconds
        if wait_count < 25:
            return_to = request.META.get("HTTP_REFERER") if request.META.get("HTTP_REFERER") is not None else '/'
            context = {'error': 'Ação não autorizada',
                       'err_msg': 'Você deve esperar {} segundos para perguntar novamente.'.format(25 - wait_count),
                       'redirect': return_to}
            return render(request, 'error.html', context)
    except:
        pass

    if request.method == 'POST':
        description = request.POST.get('description')
        description = description.replace('\r', '')

        text = request.POST.get('question')

        if len(text) > 181 or len(description) > 5000 or text[-1] != '?':
            return redirect('/news')

        video = None
        try:
            video = request.FILES['video']
        except:
            pass

        if video:
            if video.size > 3200000:
                context = {'error': 'Arquivo não suportado', 'redirect': '/ask',
                           'err_msg': 'O arquivo que você enviou excede o tamanho máximo de um vídeo: 3mb.'}
                return render(request, 'error.html', context)

        q = Question.objects.create(creator=UserProfile.objects.get(user=request.user), text=text,
                                    description=description.replace('\\', '\\\\'))

        if video:
            video_name = 'media-{}{}'.format(timezone.now().date(), timezone.now().time()).replace(':', '')

            with open('media/videos/' + video_name, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)

            q.videofile = 'videos/' + video_name

            video_path = 'media/videos/' + video_name
            thumb_path = 'videos/' + video_name + '.jpg'
            try:
                subprocess.call(['ffmpeg', '-i', video_path, '-ss', '00:00:00.000', '-vf', 'scale=320:-2',
                                 '-hide_banner', '-loglevel', 'warning', '-vframes', '1', 'media/' + thumb_path])
                q.videothumb = thumb_path
            except FileNotFoundError:
                pass
            q.save()

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']

            file_name = 'media-{}{}'.format(timezone.now().date(), timezone.now().time()).replace(':', '')

            success = save_img_file(f, 'media/questions/' + file_name, (850, 850))
            if success:
                q.image = success

            q.save()

        ccount = request.POST.get('choices-count')
        if ccount.isdigit():
            is_multichoice = request.POST.get('is-multichoice') is not None
            ccount = int(ccount)
            if ccount <= general_rules.MAXIMUM_POLL_CHOICES and ccount > 1:  # Proteção de POST manual
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

    page = request.GET.get('page', 1)
    up = UserProfile.objects.get(user=request.user)

    query = Notification.objects.filter(receiver=request.user, active=True)
    p = Paginator(query.order_by('-creation_date'), 15)

    if page == 1 and query:
        up.last_read_notification_id = query.last().id
    if up.new_notifications > 0:
        up.new_notifications = 0
    up.save()

    context = {
        'notifications': p.page(page),
        'user_p': up,
    }

    return render(request, 'notification.html', context)

def comment(request):
    if not request.user.is_authenticated:
        return None

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return HttpResponse('<p>Você não pode comentar.</p>', content_type='text/plain')
    elif should_ip_check():
        if not validate_ip(request):
            return HttpResponse('<p>Você não pode comentar.</p>', content_type='text/plain')

    up = UserProfile.objects.get(user=request.user)
    if Comment.objects.filter(creator=up.user).exists():
        if (timezone.now() - Comment.objects.filter(creator=up.user).latest('id').pub_date).seconds < 2:
            comment_creator_template = '''
                    <li class="list-group-item c no-horiz-padding">
                        <div class="comm-card" style="background-color: rgba(255,155,155,0.25); padding-left: 10px; padding-right: 10px; padding-bottom: 5px;">
                            <p>O comentário a seguir não pôde ser enviado: </p>
                            <p>{}</p>
                        </div>
                    </li>
                    '''.format(html.escape(request.POST.get('text')).replace('\n', '<br>'))

            return HttpResponse(comment_creator_template, content_type='text/plain')

    c = Comment.objects.create(response=Response.objects.get(id=request.POST.get('response_id')), creator=request.user,
                               text=html.escape(request.POST.get('text')), pub_date=timezone.now())

    if not request.user == c.response.creator.user:
        n = Notification.objects.create(receiver=c.response.creator.user, type='comment-in-response',
                                        text='<p><a href="/user/{}">{}</a> comentou na sua resposta na pergunta: <a href="/question/{}">"{}"</a></p>'.format(
                                            c.creator.username, c.creator.username, c.response.question.id,
                                            c.response.question.text), liker_id=request.user.id)
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
            '''.format(c.creator.username, UserProfile.objects.get(user=request.user).avatar.url,
                       c.creator.username, naturaltime(c.pub_date), c.id,
                       c.text.replace('\n', '<br>'))

    return HttpResponse(comment_creator_template)

def rank(request):
    order = UserProfile.objects.order_by('-total_points')[:50]
    context = {'rank': [{'pos': i + 1, 'user': order[i]} for i in range(len(order))]}

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up

    return render(request, 'rank.html', context)

def edit_response(request):
    response = Response.objects.get(creator=UserProfile.objects.get(user=request.user),
                                    id=request.POST.get('response_id'))
    response.text = request.POST.get('text')
    response.save()

    return redirect('/question/' + str(response.question.id))

def delete_question(request):
    user_profile = UserProfile.objects.get(user=request.user)
    question = Question.objects.get(id=request.POST.get('question_id'))

    if user_profile != question.creator:
        if 'pap' in ast.literal_eval(user_profile.permissions):
            ModActivity.objects.create(obj_id=question.id, obj_creator=question.creator.user, mod=user_profile.user,
                                       type='q', obj_text=question.text, obj_extra=question.description)
            question.active = False
            question.save()
            return redirect('/news')
        return HttpResponse('NOK', content_type='text/plain')

    if question.image:
        os.system('rm ' + question.image.path)
    if question.videofile:
        os.system('rm ' + question.videofile.path)
    question.delete()

    return redirect('/news')

def delete_comment(request):
    c = Comment.objects.get(id=request.GET.get('comment_id'))

    if request.user != c.creator:
        return HttpResponse('Proibido.', content_type='text/plain')

    c.delete()
    return HttpResponse('OK', content_type='text/plain')

def edit_profile(request, username):
    from urllib.parse import unquote
    username = unquote(username)

    if request.user.is_anonymous or request.user.username != username:
        return redirect('/news')

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
                file_name = '{}-{}-{}'.format(request.user.username, timezone.now().date(),
                                              timezone.now().time()).replace(':', '')

                success = save_img_file(f, 'media/avatars/' + file_name, (192, 192))
                if not success:
                    return redirect('/user/' + request.user.username + '/edit')

                u.avatar = success
                u.save()
            return redirect('/user/' + username)
        if request.POST.get('type') == 'bio':
            u = UserProfile.objects.get(user=request.user)
            u.bio = request.POST.get('bio')
            u.save()
            return redirect('/user/' + username)
        if request.POST.get('type') == 'username':
            new_username = request.POST.get('username').strip()

            '''
            Validação do nome de usuário: é permitido apenas letras, números, hífens, undercores e espaços.
            '''
            # verificando caractere por caractere:
            pode = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúâêôäëïöüãõçñÁÉÍÓÚÂÊÔÄËÏÖÜÃÕÇÑ0123456789-_ '

            for ch in new_username:
                if ch in pode:
                    continue

                html = '<div class="alert alert-danger"><p>O nome de usuário deve conter apenas caracteres alfanuméricos, hífens, underscores e espaços.</p></div>'
                return render(request, 'edit-profile.html', {'invalid_username_text': html, 'username': new_username,
                                                             'invalid_username': ' is-invalid'})

            if '  ' in new_username:
                html = '<div class="alert alert-danger"><p>O nome de usuário não pode conter espaços concomitantes.</p></div>'
                return render(request, 'edit-profile.html', {'invalid_username_text': html, 'username': new_username,
                                                             'invalid_username': ' is-invalid'})

            if len(new_username) > 30:
                return HttpResponse('Erro.', content_type='text/plain')

            if User.objects.filter(username=new_username).exists():
                return render(request, 'edit-profile.html',
                              {'user_p': UserProfile.objects.get(user=request.user), 'username_display': 'block',
                               'invalid_username': ' is-invalid'})

            password = request.POST.get('password')
            user = authenticate(username=request.user.username, password=password)
            if user is None:
                if not User.objects.filter(username=request.POST.get('username')).exists():
                    return render(request, 'edit-profile.html',
                                  {'user_p': UserProfile.objects.get(user=request.user), 'password_display': 'block',
                                   'invalid_password': ' is-invalid'})
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
            if request.POST.get('followable') is not None:
                u.followable = True
            else:
                u.followable = False
            if request.POST.get('allows-chat') is not None:
                u.allows_chat = True
            else:
                u.allows_chat = False
            u.save()
            return redirect('/user/' + username)
        elif request.POST.get('type') == 'cover-pic':
            '''
            Troca a foto de capa do usuário.
            Retorno: redirect para o perfil do usuário.
            '''
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():

                u = UserProfile.objects.get(user=request.user)

                '''
                Já que vai trocar de foto de capa, apaga a foto antiga se houver.
                '''
                if u.cover_photo:
                    os.system('rm ' + u.cover_photo.path)

                f = request.FILES['file']
                '''
                Nome da imagem do usuário no sistema de arquivos: nome de usuário atual, data de alteração e horário da alteração.
                '''
                file_name = '{}-{}-{}'.format(request.user.username, timezone.now().date(),
                                              timezone.now().time()).replace(':', '')

                success = save_img_file(f, 'media/cover_photos/' + file_name, (900, 300))
                if not success:
                    return redirect('/user/' + request.user.username + '/edit')

                u.cover_photo = success
                u.save()
            return redirect('/user/' + username)
        elif request.POST.get('type') == 'remove-cover':
            '''
            Remove a foto de capa do usuário.
            Retorno: redirect para o perfil do usuário.
            '''
            u = UserProfile.objects.get(user=request.user)
            if u.cover_photo:
                os.system('rm ' + u.cover_photo.path)
                u.cover_photo = None
                u.save()

            return redirect('/user/' + request.user.username)
    return render(request, 'edit-profile.html',
                  {'user_p': UserProfile.objects.get(user=User.objects.get(username=username))})

def block(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    bcount = u_p.blocked_users.count()
    if u_p.blocked_users.filter(username=username).exists():
        u_p.blocked_users.remove(User.objects.get(username=username))
        return HttpResponse('Bloquear', content_type='text/plain')
    if username == u_p.user.username or bcount >= general_rules.MAXIMUM_BLOCKED_USERS:
        return HttpResponse('Proibido', content_type='text/plain')
    u_p.blocked_users.add(User.objects.get(username=username))
    return HttpResponse('Bloqueado', content_type='text/plain')

def silence(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    scount = u_p.silenced_users.count()
    if u_p.silenced_users.filter(username=username).exists():
        u_p.silenced_users.remove(User.objects.get(username=username))
        return HttpResponse('Removed', content_type='text/plain')
    if username == u_p.user.username or scount >= general_rules.MAXIMUM_SILENCED_USERS:
        return HttpResponse('Proibido', content_type='text/plain')
    u_p.silenced_users.add(User.objects.get(username=username))
    return HttpResponse('Added', content_type='text/plain')

def make_user_unfollow(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    target = UserProfile.objects.get(user=User.objects.get(username=username))

    if target.followed_users.filter(username=request.user.username).exists():
        target.followed_users.remove(u_p.user)
        return HttpResponse('Removed', content_type='text/plain')
    return HttpResponse('Proibido', content_type='text/plain')

def follow_user(request, username):
    username = unquote(username)
    u_p = UserProfile.objects.get(user=request.user)
    target = UserProfile.objects.get(user=User.objects.get(username=username))

    if u_p.followed_users.filter(username=username).exists():
        u_p.followed_users.remove(target.user)
        return HttpResponse('Removed', content_type='text/plain')
    if username == u_p.user.username or not target.followable:
        return HttpResponse('Proibido', content_type='text/plain')
    u_p.followed_users.add(target.user)
    return HttpResponse('Added', content_type='text/plain')

def follow_question(request, question_id):
    q = Question.objects.get(id=question_id)
    u_p = UserProfile.objects.get(user=request.user)
    if u_p == q.creator:
        return HttpResponse('Proibido', content_type='text/plain')

    if u_p.followed_questions.filter(id=question_id).exists():
        u_p.followed_questions.remove(q)

        return HttpResponse('Removed', content_type='text/plain')

    u_p.followed_questions.add(q)
    return HttpResponse('Added', content_type='text/plain')

''' A função abaixo faz a validação das credenciais de novos usuários. '''
def is_a_valid_user(username, email, password):
    if len(username) > 30 or not username:
        return False, 'nome de usuário'
    elif len(email) > 60 or not email:
        return False, 'e-mail'
    elif len(password) < 6 or len(password) > 256:
        return False, 'código/senha'

    emails = ['mail', 'hotmail', 'outlook', 'live', 'msn', 'yahoo', 'icloud', 'gmail', 'bol', 'aol', 'uol', 'terra',
              'protonmail', 'tutanota', 'yandex', 'net']
    try:
        start = email.index('@') + 1
        end = email.index('.', start)
    except ValueError:
        return False, 'e-mail'

    email = email[start:end]
    if email not in emails:
        return False, 'e-mail'
    return True, None

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

    return HttpResponse('OK', content_type='text/plain')

def rules(request):
    context = {}

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up

    return render(request, 'rules.html', context)

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
        c_query = PollChoice.objects.filter(id=choice, poll=p)
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

def get_feed_content(user_p, page, subpage):
    followed_users = UserProfile.objects.filter(user_id__in=user_p.followed_users.all())

    fuq_fur_fqr_proportion = (45, 15, 40)
    followed_u_questions = Paginator(Question.objects.filter(creator__in=followed_users, active=True).order_by('-id'),
                                     fuq_fur_fqr_proportion[0]).page(page).object_list
    followed_u_responses = Paginator(Response.objects.filter(creator__in=followed_users, active=True).order_by('-id'),
                                     fuq_fur_fqr_proportion[1]).page(page).object_list
    followed_questions = user_p.followed_questions.all()
    followed_q_responses = Paginator(
        Response.objects.filter(question__in=followed_questions, active=True).order_by('-id'),
        fuq_fur_fqr_proportion[2]).page(page).object_list

    '''
    0: Respostas de perguntas seguidas
    1: Respostas de usuários seguidos
    2: Perguntas de usuários seguidos
    '''
    feed_page = [{'type': 0, 'pub_date': r.pub_date, 'obj': r} for r in followed_q_responses] + [
        {'type': 1, 'pub_date': r.pub_date, 'obj': r} for r in followed_u_responses] + [
                    {'type': 2, 'pub_date': q.pub_date, 'obj': q} for q in followed_u_questions]
    feed_page = sorted(feed_page, key=lambda x: x['pub_date'], reverse=True)

    return feed_page[subpage * 20:subpage * 20 + 20]

def get_index_feed_page(request):
    page = request.GET.get('page')
    subpage = request.GET.get('sp')
    up = UserProfile.objects.get(user=request.user)
    try:
        items = get_feed_content(up, int(page), int(subpage))
    except EmptyPage:
        return HttpResponse('-1', content_type='text/plain')

    if len(items) == 0:
        return HttpResponse('0', content_type='text/plain')

    context = {
        'items': items,
    }

    return render(request, 'base/index-feed-page.html', context)

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
                    "question_creator_avatar": q.creator.avatar.url,
                    "user_answer": "False",
                },
            )
    else:
        for q in questions:
            r = Response.objects.filter(creator=UserProfile.objects.get(user=request.user), question=q, active=True)
            answer = 'False' if not r.exists() else r[0].text

            para_retornar.append(
                {
                    "id": q.id,
                    "text": q.text,
                    "description": q.description,
                    "total_answers": q.total_responses,
                    "pub_date": fix_naturaltime(naturaltime(q.pub_date)),
                    "creator": q.creator.user.username,
                    "question_creator_avatar": q.creator.avatar.url,
                    "user_answer": answer,
                },
            )

    return JsonResponse(para_retornar, safe=False)

def more_questions(request):
    # Para a página inicial
    id_de_inicio = int(request.GET.get('id_de_inicio'))
    context = dict()

    silenced = []
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up
        silenced = [UserProfile.objects.get(user=u) for u in up.silenced_users.all()]

    if id_de_inicio > 0:
        questions = Question.objects.filter(id__lte=id_de_inicio, active=True).exclude(
            creator__in=silenced).order_by('-id')[:20]
    else:
        questions = Question.objects.filter(active=True).exclude(creator__in=silenced).order_by('-id')[:20]

    context['questions'] = questions

    return render(request, 'base/index-recent-q-page.html', context)

def update_index(request):
    up = None
    silenced = []
    if not request.user.is_anonymous:
        up = UserProfile.objects.get(user=request.user)
        silenced = [UserProfile.objects.get(user=u) for u in up.silenced_users.all()]

    last_known_q = int(request.GET.get('last_known_q'))
    last_q = Question.objects.last().id
    if last_q - last_known_q > 200:
        return HttpResponse('-1')

    nq = Question.objects.filter(id__gt=last_known_q, active=True).exclude(creator__in=silenced).order_by("-id")
    if len(nq) == 0:
        return HttpResponse('-1')
    elif len(nq) > 29:
        return HttpResponse('-1')

    nq_context = {'questions': nq, 'user_p': up}

    return render(request, 'base/index-recent-q-page.html', nq_context)

def update_question(request):
    qid = int(request.GET.get('qid'))
    last_r = int(request.GET.get('lr'))
    q = Question.objects.get(id=qid)
    context = {'question': q, }
    excluded = []
    if not request.user.is_anonymous:
        up = UserProfile.objects.get(user=request.user)
        excluded = [up] + [UserProfile.objects.get(user=u) for u in up.silenced_users.all()]
        context['user_permissions'] = ast.literal_eval(up.permissions)
        context['user_p'] = up
    nr = Response.objects.filter(question=q, id__gt=last_r, active=True).exclude(creator__in=excluded).order_by(
        '-total_likes', 'id')

    if len(nr) < 1:
        return HttpResponse('-1')

    context['responses'] = nr

    return render(request, 'base/response-content.html', context)

def new_activity_check(request):
    nn = 0
    up = None
    silenced = []
    if not request.user.is_anonymous:
        up = UserProfile.objects.get(user=request.user)
        nn = up.new_notifications

        silenced = [UserProfile.objects.get(user=u) for u in up.silenced_users.all()]

    try:
        last_known_id = int(request.GET.get('last_known_q'))
        obj_type = 'q'
    except:
        last_known_id = int(request.GET.get('last_known_r'))
        obj_type = 'r'

    if obj_type == 'r':
        qid = int(request.GET.get('qid'))
        q = Question.objects.get(id=qid)

        # OBS.: Este sistema deve ser atualizado caso alguma pergunta chegue a ter mais de 200 respostas
        # para evitar sobrecarregamentos, conforme já é o caso do if-statement no check para novas perguntas!
        if up is not None:
            responses = len(Response.objects.filter(question=q, id__gt=last_known_id,
                                                    active=True).exclude(creator__in=[up] + silenced))
        else:
            responses = len(Response.objects.filter(question=q, id__gt=last_known_id, active=True))
        return JsonResponse({'nn': nn, 'nr': responses})

    elif obj_type == 'q':
        last_q = Question.objects.last().id
        if last_q - last_known_id > 200 or last_known_id < 1:
            return JsonResponse({'nn': nn, 'nq': -1})
        nq = Question.objects.filter(id__gt=last_known_id, active=True).exclude(creator__in=silenced).order_by('id')

        return JsonResponse({'nn': nn, 'nq': len(nq)})

def get_more_questions(request):
    # Para o profile.html
    page = request.GET.get('q_page', 2)
    user_id = request.GET.get('user_id')
    qtype = request.GET.get('qtype')

    target = UserProfile.objects.get(user=User.objects.get(id=user_id))
    if target.hide_activity and not request.user.is_superuser and 'pap' not in ast.literal_eval(
            UserProfile.objects.get(user=request.user).permissions):
        if target.user.id != request.user.id:
            return 'Proibido.'

    if qtype == 'fq':
        q = target.followed_questions.filter(active=True).order_by('-id')
    else:
        q = Question.objects.filter(creator=target, active=True).order_by('-pub_date')

    p = Paginator(q, 10)
    json = dict()
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
    # Para o profile.html
    page = request.GET.get('r_page', 2)
    user_id = request.GET.get('user_id')
    target = UserProfile.objects.get(user=User.objects.get(id=user_id))
    if target.hide_activity and not request.user.is_superuser and 'pap' not in ast.literal_eval(
            UserProfile.objects.get(user=request.user).permissions):
        if target.user.id != request.user.id:
            return 'Proibido.'
    r = Response.objects.filter(creator=target, active=True).order_by('-pub_date')
    p = Paginator(r, 10)

    json = dict()
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
    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/news')
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/news')

    type = request.GET.get('type')
    obj_id = request.GET.get('obj_id')
    reporter = request.user

    r = Report.objects.filter(obj_id=obj_id)

    if r.exists():
        r = r.first()
    else:
        r = Report.objects.create(type=type, obj_id=obj_id)

    if not r.reporters.filter(username=reporter.username).exists():
        r.reporters.add(reporter)
        r.total_reports += 1
        r.save()

    return HttpResponse('OK')

def report_user(request):
    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/news')
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/news')

    type = 'u'
    obj_id = User.objects.get(username=request.POST.get('username')).id
    text = request.POST.get('text')

    r = Report.objects.create(type=type, obj_id=obj_id, text=text, total_reports=1)
    r.reporters.add(request.user)
    r.save()

    return HttpResponse('OK')

def manage_reports(request):
    user_profile = UserProfile.objects.get(user=request.user)
    user_permissions = ast.literal_eval(user_profile.permissions)

    if not request.user.is_superuser:
        if 'pap' not in user_permissions:
            return HttpResponse('{}, você não tem permissão administrativa.'.format(request.user.username))

    reports = list(Report.objects.all())
    reports.sort(key=lambda x: x.total_reports, reverse=True)

    context = {
        'reports': reports,
    }

    return render(request, 'manage_reports.html', context)

def delete_report_and_obj(request):
    if not request.user.is_superuser:
        return HttpResponse('Proibido.', content_type='text/plain')

    r = Report.objects.get(obj_id=request.GET.get('obj_id'))

    if r.type == 'q':
        '''Tratando report do tipo "pergunta" (obj_id é o ID de uma pergunta, a pergunta foi reportada).'''
        q = Question.objects.filter(id=r.obj_id)
        if q.exists():
            q = q.first()
            q.delete()
        r.delete()

    return HttpResponse('OK', content_type='text/plain')

def delete_report(request):
    r = Report.objects.get(obj_id=request.GET.get('obj_id'))
    r.delete()
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

class SearchRankCD(SearchRank):
    function = 'ts_rank_cd'

    def __init__(self, vector, query, normalization=0, **extra):
        super(SearchRank, self).__init__(
            vector, query, normalization, **extra)

def search(request):
    time = timezone.now()
    user_ip = get_client_ip(request)
    searcher_ips = cache.get('searcher_ids')
    if not searcher_ips:
        cache.set('searcher_ids', {user_ip: time})
    elif user_ip in searcher_ips:
        last_search = time - searcher_ips[user_ip]
        searcher_ips[user_ip] = time
        cache.set('searcher_ids', searcher_ips)
        if last_search < timedelta(seconds=3):
            context = {'error': 'Sua busca falhou', 'err_msg': 'Por favor, tente novamente.'}
            return render(request, 'error.html', context)
    else:
        searcher_ips[user_ip] = time
        cache.set('searcher_ids', searcher_ips)

    userquery = request.GET.get('q')
    page = request.GET.get('page', 1)

    '''
    Pode ser ordenada por, por exemplo, os dois fatores a seguir:
        1. "-rank" (maior ranking -> mais fidelidade)
        2. "-pub_date" (maior pub_date -> mais recente)

    O ideal no futuro é ativar ambas opções na página de busca
    '''
    order_factor = "-pub_date"
    '''
    # Mais resultados, menos omissões, porém usa mais recursos e gera muitos resultados irrelevantes.
    res_q = Question.objects.annotate(rank=SearchRank(SearchVector('text', 'description'), SearchQuery(userquery))).order_by(order_factor)
    res_r = Response.objects.annotate(rank=SearchRank(SearchVector('text'), SearchQuery(userquery))).order_by(order_factor)
    '''
    # Menos resultados, mais omissões, porém usa menos recursos e gera menos resultados irrelevantes:
    res_q = Question.objects.annotate(
        rank=SearchRank(SearchVector('text', weight='A') + SearchVector('description', weight='B'),
                        SearchQuery(userquery))).filter(rank__gte=0.3, active=True).order_by(order_factor)
    res_r = Response.objects.annotate(rank=SearchRank(SearchVector('text', weight='A'), SearchQuery(userquery))).filter(
        rank__gte=0.3, active=True).order_by(order_factor)

    ITEMS_PER_PAGE = 40
    qrcount = ITEMS_PER_PAGE // 2

    try:
        pq = Paginator(res_q, qrcount).page(page)
        pr = Paginator(res_r, qrcount).page(page)
    except InvalidPage:
        context = {'error': 'Esta página não existe', 'err_msg': 'A página da sua busca não existe.'}
        return render(request, 'error.html', context)

    if not userquery:
        userquery = 'Busca:'  # TODO: provisorio - posteriormente passar a resp ao template

    context = {
        'questions': pq,
        'responses': pr,
        'q': userquery,
        'next': int(page) + 1,
        'previous': int(page) - 1,
    }

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up

    return render(request, 'search.html', context)

def open_chat(request):
    context = dict()
    uname = request.GET.get('u')
    target_up = UserProfile.objects.get(user=User.objects.get(username=uname))

    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/user/' + target_up.user.username)
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/user/' + target_up.user.username)

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up
    else:
        return redirect('/news')

    if target_up.blocked_users.filter(userprofile=up).exists() or not target_up.allows_chat:
        context = {'error': 'A página não pode ser exibida', 'err_msg': 'A conversa não existe ou está indisponível.'}
        return render(request, 'error.html', context)

    # TODO: adicionar handling para users silenciados!

    c = Chat.objects.filter(participant=up.user).filter(participant=target_up.user)
    if not c:
        c = Chat.objects.create()
        c.participant.add(up.user, target_up.user)
        c.save()
    elif len(c) == 1:
        c = c[0]

    return redirect('/chat?c=' + str(c.id))

def chats(request):
    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/user/' + request.user.username)
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/user/' + request.user.username)

    context = dict()
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up
    else:
        return redirect('/news')

    context['chats'] = Chat.objects.filter(participant=up.user).order_by('-last_activity')

    return render(request, 'chats.html', context)

def chat(request):
    client_ip = get_client_ip(request)
    if Ban.objects.filter(ip=client_ip).exists():
        return redirect('/news')
    elif should_ip_check():
        if not validate_ip(request):
            return redirect('/news')

    context = dict()
    chat_id = request.GET.get('c', -1)
    try:
        c = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        context = {'error': 'A página não pode ser exibida', 'err_msg': 'A conversa não existe ou está indisponível.'}
        return render(request, 'error.html', context)

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        context['user_p'] = up
        if not c.participant.filter(userprofile=up).exists():
            context = {'error': 'A página não pode ser exibida',
                       'err_msg': 'A conversa não existe ou está indisponível.'}
            return render(request, 'error.html', context)
    else:
        return redirect('/news')

    counterpart = chat_counterpart(up, c)
    context['counterpart'] = counterpart

    last_received = ChatMessage.objects.filter(chat=c, creator=counterpart.user).last()

    if last_received:
        if last_received.id > c.last_viewed:
            c.last_viewed = last_received.id
            c.save()

    messages = list(reversed(list(ChatMessage.objects.filter(chat=c).order_by('-id')[:10])))
    context['messages'] = messages

    context['cid'] = c.id
    context['last_viewed'] = c.last_viewed

    return render(request, 'chat.html', context)

def sendmsg(request):
    chat_id = request.POST.get('c')
    text = request.POST.get('text')

    try:
        c = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse('Proibido', content_type='text/plain')

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        try:
            if (timezone.now() - ChatMessage.objects.filter(creator=up.user).latest('id').pub_date).seconds < 1:
                return HttpResponse('Proibido', content_type='text/plain')
        except ChatMessage.DoesNotExist:
            pass
        if chat_counterpart(up, c).blocked_users.filter(userprofile=up).exists():
            return HttpResponse('Proibido', content_type='text/plain')

        if not c.participant.filter(userprofile=up).exists():
            return HttpResponse('Proibido', content_type='text/plain')
    else:
        return HttpResponse('Proibido', content_type='text/plain')

    message = ChatMessage.objects.create(chat=c, creator=up.user)

    message.text = text
    if not text:
        if up.total_points < 500:
            message.text = 'Você precisa de pelo menos 500 pontos para enviar fotos.'
        else:
            message.text = 'Foto'
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                f = request.FILES['file']

                chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_)(0123456789'
                file_name = ''.join(random.choice(chars) for i in range(32))

                success = save_img_file(f, 'media/chat_photos/' + file_name, (1200, 1200))
                if success:
                    message.image = success

    message.save()

    c.last_activity = timezone.now()
    c.save()

    return HttpResponse('OK', content_type='text/plain')

def loadmsgs(request):
    chat_id = request.GET.get('c')
    type = request.GET.get('type')  # old, new
    last_loaded = request.GET.get('last')
    last_known_viewed = request.GET.get('lkv')

    try:
        c = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse('Proibido', content_type='text/plain')

    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        if not c.participant.filter(userprofile=up).exists():
            return HttpResponse('Proibido', content_type='text/plain')
    else:
        return HttpResponse('Proibido', content_type='text/plain')

    last_viewed_new = None
    last_del = None
    if type == 'old':
        messages = list(reversed(list(ChatMessage.objects.filter(id__lt=last_loaded, chat=c).order_by('-id')[:50])))
    elif type == 'new':
        messages = list(reversed(list(ChatMessage.objects.filter(id__gt=last_loaded, chat=c).order_by('-id')[:50])))
        if c.last_viewed > int(last_known_viewed):
            last_viewed_new = c.last_viewed
        last_del = ChatMessage.objects.filter(chat=c, hide=True, creator=chat_counterpart(up, c).user,
                                              pub_date__gte=timezone.now() - timedelta(hours=1)).order_by('-id')[:5]

    return render(request, 'base/chat-messages.html', {'messages': messages, 'last_viewed': last_viewed_new,
                                                       'user_p': up, 'last_deletions': last_del})

def markviewed(request):
    chat_id = request.GET.get('c')
    msg_id = request.GET.get('m')

    try:
        c = Chat.objects.get(id=chat_id)
        m = ChatMessage.objects.get(id=msg_id)
    except:
        return HttpResponse('Proibido', content_type='text/plain')

    if m.chat != c:
        return HttpResponse('Proibido', content_type='text/plain')
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        counterpart = chat_counterpart(up, c)
        if counterpart is None:
            return HttpResponse('Proibido', content_type='text/plain')
        if not m.creator == counterpart.user:
            return HttpResponse('Proibido', content_type='text/plain')
    else:
        return HttpResponse('Proibido', content_type='text/plain')

    c.last_viewed = msg_id
    c.save()

    return HttpResponse('OK', content_type='text/plain')

def remove_msg(request):
    chat_id = request.GET.get('c')
    msg_id = request.GET.get('m')

    try:
        c = Chat.objects.get(id=chat_id)
        m = ChatMessage.objects.get(id=msg_id)
    except:
        return HttpResponse('Proibido', content_type='text/plain')

    if m.chat != c:
        return HttpResponse('Proibido', content_type='text/plain')
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        if m.creator != up.user:
            return HttpResponse('Proibido', content_type='text/plain')
    else:
        return HttpResponse('Proibido', content_type='text/plain')

    m.hide = True
    m.save()

    return HttpResponse('OK', content_type='text/plain')

def modactivity(request):
    if not request.user.is_superuser:
        # Nega acesso a usuários
        return redirect('/news')

    page = request.GET.get('page', 1)
    activities = ModActivity.objects.order_by('-action_date')

    ITEMS_PER_PAGE = 40
    try:
        paged_act = Paginator(activities, ITEMS_PER_PAGE).page(page)
    except InvalidPage:
        context = {'error': 'Esta página não existe', 'err_msg': 'A página da sua busca não existe.'}
        return render(request, 'error.html', context)

    context = {
        'activities': paged_act,
        'next': int(page) + 1,
        'previous': int(page) - 1,
    }
    return render(request, 'modactivity.html', context)

def star(request):
    qid = request.GET.get('qid')
    q = Question.objects.get(id=qid)
    if q.creator.user == request.user:
        return HttpResponse('Proibido', content_type='text/plain')

    if q.stars.filter(username=request.user.username).exists():
        q.stars.remove(request.user)
        q.total_stars = q.stars.count()
        q.save()
        try:
            n = Notification.objects.get(liker=request.user, type='start', question=q)
            n.activate(False)
        except Notification.DoesNotExist:
            pass
    else:
        q.stars.add(request.user)
        q.total_stars = q.stars.count()
        q.save()

        who_gave_a_star = request.user.username
        qid = q.id
        qtext = q.text

        try:
            n = Notification.objects.get(liker=request.user, type='start', question=q)
            n.activate()
        except Notification.DoesNotExist:
            n = Notification.objects.create(receiver=q.creator.user, type='start', question=q, liker=request.user,
                                            text=f'<a href="/user/{who_gave_a_star}">{who_gave_a_star}</a> curtiu sua pergunta <a href="/question/{qid}">"{qtext}"</a>.')
            n.prepare()
            n.save()

    return HttpResponse(str(q.total_stars), content_type='text/plain')

def promo(request):
    return render(request, 'promo.html')

def novadx(request):
    return render(request, 'novadx.html')
