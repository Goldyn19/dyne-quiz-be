import os
from django.core.asgi import get_asgi_application

# Set the default settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DyneQuiz.settings')

# Get the ASGI application for HTTP
django_asgi_app = get_asgi_application()


import django
django.setup()


from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


from quiz.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
