"""django_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.shortcuts import render
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

from main_app import views

urlpatterns = [
  path('', views.index, name='index'),
  path('news', views.index, name='index'),
  path('popular', views.index, name='index'),
  path('question/<int:question_id>', views.question, name='question'),
  path('answer/like', views.like, name='like'),
  path('answer/choose', views.choose_best_answer, name="choose_best_answer"),
  path('delete_response', views.delete_response, name='delete_response'),
  path('user/activity', views.activity, name='activity'),
  path('user/<str:username>', views.profile, name='profile'),
  path('user/<str:username>/edit', views.edit_profile, name='edit_profile'),
  path('user/<str:username>/block', views.block, name='block'),
  path('user/<str:username>/silence', views.silence, name='silence'),
  path('ask', views.ask, name='ask'),
  path('signin', views.signin, name='signin'),
  path('signup', views.signup, name='signup'),
  path('logout', views.logout, name='logout'),
  path('notifications', views.notification, name='notification'),
  path('delete_question', views.delete_question, name='delete_question'),
  path('delete_response', views.delete_response, name='delete_response'),
  path('comment', views.comment, name='comment'),
  path('delete_comment', views.delete_comment, name='delete_comment'),
  path('rank', views.rank, name='rank'),
  path('edit-response', views.edit_response, name='edit_response'),
  path('get_more_questions', views.get_more_questions, name='get_more_questions'),
  path('get_more_responses', views.get_more_responses, name='get_more_responses'),
  path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
  path('save_answer', views.save_answer, name='save_answer'),
  path('poll/vote', views.vote_on_poll, name='vote_on_poll'),
  path('poll/undovote', views.undo_vote_on_poll, name='undo_vote_on_poll'),
  path('rules', views.rules, name='rules'),
path('menu', lambda request: render(request, 'menu.html')),
  path('more_questions', views.more_questions, name='more_questions'),
  path('more_popular_questions', views.more_popular_questions, name='more_popular_questions'),
  path('report', views.report, name='report'),
  path('delete_report_and_obj', views.delete_report_and_obj, name='delete_report_and_obj'),
  path('delete_report', views.delete_report, name='delete_report'),
  path('manage_reports', views.manage_reports, name='manage_reports'),
  path('confirm-account', views.confirm_account, name='confirm_account'),
  path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
