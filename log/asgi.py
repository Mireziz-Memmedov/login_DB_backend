import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Django settings-i təyin et
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "log.settings")

# Django app-lərini yüklə
django.setup()

# İndi təhlükəsiz import
import users.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})


# application = get_asgi_application()
