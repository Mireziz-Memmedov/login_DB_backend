import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from users.routing import websocket_urlpatterns  # websocket URL-ləri

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "log.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

# application = get_asgi_application()
