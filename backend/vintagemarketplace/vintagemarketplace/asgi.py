# asgi.py
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vintagemarketplace.settings")
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messaging.routing import websocket_urlpatterns
from messaging.ws_jwt import JWTAuthMiddleware  # import the class, not the stack

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # AuthMiddlewareStack runs first (session/cookie auth),
    # then JWTAuthMiddleware runs and **overrides** scope['user'] if ?token=... is present.
    "websocket": AuthMiddlewareStack(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
