from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import chat.routing  # chat app routing
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "log.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns  # chat app-dən endpoint
        )
    ),
})


# application = get_asgi_application()
