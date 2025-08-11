from django.urls import re_path
from .consumers import GameSessionConsumer, GameRoomConsumer

websocket_urlpatterns = [
    re_path(r'ws/quiz/(?P<game_pin>\w+)/lobby/$', GameSessionConsumer.as_asgi()),
    re_path(r'^ws/game/(?P<game_pin>\w+)/play/$', GameRoomConsumer.as_asgi()),
]
