from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('search-user/', views.search_user, name='search_user'),
    path('recent-chats/', views.recent_chats, name='recent_chats'),
    path('send-message/', views.send_message, name='send_message'),
    path('get-messages/', views.get_messages, name='get_messages'),
    path('user_status/', views.user_status, name='user_status'),
    path('logout/', views.logout, name='logout'),
    path('forgot-check/', views.forgot_check, name='forgot_check'),
    path('verify-code/', views.verify_code, name='verify_code'),
]