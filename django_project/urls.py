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
  path('feed', views.index, name='index'),
  path('question/<int:question_id>', views.question, name='question'),
  path('question/star', views.star, name='star'),
  path('answer/like', views.like, name='like'),
  path('answer/choose', views.choose_best_answer, name="choose_best_answer"),
  path('delete_response', views.delete_response, name='delete_response'),
  path('user/<str:username>', views.profile, name='profile'),
  path('user/<str:username>/edit', views.edit_profile, name='edit_profile'),
  path('user/<str:username>/block', views.block, name='block'),
  path('user/<str:username>/silence', views.silence, name='silence'),
  path('user/<str:username>/follow', views.follow_user, name='follow_user'),
  path('user/<str:username>/make_unfollow', views.make_user_unfollow, name='make_user_unfollow'),
  path('question/<int:question_id>/follow', views.follow_question, name='follow_question'),
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
  path('novadx', views.novadx, name='novadx'),
  path('edit-response', views.edit_response, name='edit_response'),
  path('get_more_questions', views.get_more_questions, name='get_more_questions'),
  path('get_more_responses', views.get_more_responses, name='get_more_responses'),
  path('get_index_feed_page', views.get_index_feed_page, name='get_index_feed_page'),
  path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
  path('save_answer', views.save_answer, name='save_answer'),
  path('poll/vote', views.vote_on_poll, name='vote_on_poll'),
  path('poll/undovote', views.undo_vote_on_poll, name='undo_vote_on_poll'),
  path('rules', views.rules, name='rules'),
  path('more_questions', views.more_questions, name='more_questions'),
  path('more_popular_questions', views.more_popular_questions, name='more_popular_questions'),
  path('report', views.report, name='report'),
  path('report_user', views.report_user, name='report_user'),
  path('delete_report_and_obj', views.delete_report_and_obj, name='delete_report_and_obj'),
  path('delete_report', views.delete_report, name='delete_report'),
  path('manage_reports', views.manage_reports, name='manage_reports'),
  path('confirm-account', views.confirm_account, name='confirm_account'),
  path('search', views.search, name='search'),
  path('modact', views.modactivity, name='modactivity'),
  path('new_activity_check', views.new_activity_check, name='new_activity_check'),
  path('update_index', views.update_index, name='update_index'),
  path('update_question', views.update_question, name='update_question'),
  path('chats', views.chats, name='chats'),
  path('chat', views.chat, name='chat'),
  path('sendmsg', views.sendmsg, name='sendmsg'),
  path('loadmsgs', views.loadmsgs, name='loadmsgs'),
  path('markviewed', views.markviewed, name='markviewed'),
  path('msgrm', views.remove_msg, name='msgrm'),
  path('open_chat', views.open_chat, name='open_chat'),
  path('toggle_ipch', views.toggle_ip_check, name='toggle_ipch'),
  path('admin/', admin.site.urls),
  path('promo', views.promo, name='promo'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
