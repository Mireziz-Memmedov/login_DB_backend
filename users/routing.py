from django.urls import re_path
from . import consumers  # consumers.py eyni app-də olmalıdır

websocket_urlpatterns = [
    # User-in id-si URL parametri kimi ötürülür
    re_path(r'ws/chat/(?P<user_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
