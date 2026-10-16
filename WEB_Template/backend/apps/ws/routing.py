"""WebSocket URL routing"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/echo/$', consumers.EchoConsumer.as_asgi()),
    re_path(r'^ws/room/(?P<room_name>[a-zA-Z0-9_-]+)/$', consumers.RoomConsumer.as_asgi()),
]
