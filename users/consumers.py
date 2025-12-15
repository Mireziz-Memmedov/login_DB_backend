import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import NewsUsers, Message

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.sender_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.sender = await database_sync_to_async(NewsUsers.objects.get)(id=self.sender_id)

        # Room adı: iki user üçün unikal, frontend-in `target_user` göndərəcəyi ilə match
        self.rooms = set()  # user qoşulduğu room-ları saxlamaq üçün

        await self.accept()
        print(f"User {self.sender.username} WebSocket-ə qoşuldu")

    async def disconnect(self, close_code):
        # Disconnect zamanı bütün qoşulduğu room-lardan çıx
        for room_group_name in self.rooms:
            await self.channel_layer.group_discard(room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == "chat_message":
            await self.handle_chat_message(data)
        elif msg_type == "load_messages":
            await self.handle_load_messages(data)

    async def handle_chat_message(self, data):
        message_text = data.get('message')
        receiver_name = data.get('receiver_name')
        if not message_text or not receiver_name:
            return

        try:
            receiver = await database_sync_to_async(NewsUsers.objects.get)(username=receiver_name)
        except NewsUsers.DoesNotExist:
            return

        # Mesajı DB-də saxla
        await database_sync_to_async(Message.objects.create)(
            sender=self.sender,
            receiver=receiver,
            text=message_text
        )

        # Room adı (iki user üçün unikal)
        room_name = f"{min(self.sender.id, receiver.id)}_{max(self.sender.id, receiver.id)}"
        room_group_name = f"chat_{room_name}"

        # Qrupa əlavə et yalnız əgər artıq qoşulmayıbsa
        if room_group_name not in self.rooms:
            await self.channel_layer.group_add(room_group_name, self.channel_name)
            self.rooms.add(room_group_name)

        # Mesajı qrupa göndər
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'chat_message_event',
                'message': message_text,
                'sender': self.sender.username
            }
        )

    async def handle_load_messages(self, data):
        target_user_name = data.get('target_user')
        if not target_user_name:
            return

        try:
            target_user = await database_sync_to_async(NewsUsers.objects.get)(username=target_user_name)
        except NewsUsers.DoesNotExist:
            return

        # Room adı
        room_name = f"{min(self.sender.id, target_user.id)}_{max(self.sender.id, target_user.id)}"
        room_group_name = f"chat_{room_name}"

        # Qrupa əlavə et yalnız əgər artıq qoşulmayıbsa
        if room_group_name not in self.rooms:
            await self.channel_layer.group_add(room_group_name, self.channel_name)
            self.rooms.add(room_group_name)

        # DB-dən mesajları al
        messages = await database_sync_to_async(
            lambda: list(
                Message.objects.filter(
                    sender__in=[self.sender, target_user],
                    receiver__in=[self.sender, target_user]
                ).order_by('timestamp').values('sender__username', 'text', 'timestamp')
            )
        )()

        formatted_messages = [
            {'sender': m['sender__username'], 'text': m['text'], 'timestamp': m['timestamp'].isoformat()}
            for m in messages
        ]

        await self.send(text_data=json.dumps({
            'type': 'load_messages',
            'messages': formatted_messages
        }))

    async def chat_message_event(self, event):
        # Qrupdan gələn mesajları frontend-ə göndər
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender']
        }))
