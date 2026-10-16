"""
WebSocket Consumers – Hackathon Web Template
Poskytuje 2 základní consumer typy:

1. EchoConsumer   – /ws/echo/          – Echo zpráv (testování)
2. RoomConsumer   – /ws/room/<room>/   – Skupinový broadcast (chat, kolaborace)

Oba consumery vyžadují JWT autentizaci (nastaveno v middleware).
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class EchoConsumer(AsyncWebsocketConsumer):
    """
    Jednoduchý echo consumer pro testování WebSocket spojení.
    Každou přijatou zprávu odešle zpět odesílateli.

    Připojení: ws://localhost:8000/ws/echo/
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)  # Unauthorized
            return

        await self.accept()
        logger.info(f"WS Echo connected: user={user.username}")
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'WebSocket echo spojení navázáno. Přihlášen jako: {user.username}',
        }))

    async def disconnect(self, close_code):
        user = self.scope.get('user')
        logger.info(f"WS Echo disconnected: user={getattr(user, 'username', 'anonymous')}, code={close_code}")

    async def receive(self, text_data):
        """Přijme zprávu a odešle ji zpět (echo)."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Neplatný JSON formát.',
            }))
            return

        user = self.scope['user']
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'user': user.username,
            'data': data,
        }))


class RoomConsumer(AsyncWebsocketConsumer):
    """
    Skupinový consumer pro broadcast zpráv do místnosti.
    Ideální pro: chat, real-time notifikace, kolaboraci, live updates.

    Připojení: ws://localhost:8000/ws/room/<room_name>/
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Sanitizace názvu místnosti
        self.room_name = ''.join(c for c in self.room_name if c.isalnum() or c in '-_')[:50]
        self.room_group_name = f'room_{self.room_name}'

        # Připojení do skupiny (channel layer)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        logger.info(f"WS Room connected: user={user.username}, room={self.room_name}")

        # Oznámit ostatním v místnosti
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': user.username,
                'message': f'{user.username} se připojil/a.',
            }
        )

    async def disconnect(self, close_code):
        user = self.scope.get('user')
        username = getattr(user, 'username', 'anonymous')

        # Oznámit ostatním v místnosti
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user': username,
                    'message': f'{username} opustil/a místnost.',
                }
            )
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        logger.info(f"WS Room disconnected: user={username}, room={getattr(self, 'room_name', '?')}")

    async def receive(self, text_data):
        """Přijme zprávu a broadcast ji všem v místnosti."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Neplatný JSON formát.',
            }))
            return

        user = self.scope['user']
        message_type = data.get('type', 'message')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'room_message',
                'message_type': message_type,
                'user': user.username,
                'user_id': user.id,
                'payload': data.get('payload', data),
            }
        )

    # ── Channel Layer event handlers ──────────────────────────────────────────

    async def room_message(self, event):
        """Handler pro broadcast zprávy do místnosti."""
        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'user': event['user'],
            'user_id': event['user_id'],
            'payload': event['payload'],
        }))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'message': event['message'],
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'message': event['message'],
        }))
