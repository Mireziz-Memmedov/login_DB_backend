import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import NewsUsers, Message

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Sender id URL-dən alınır
        self.sender_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.sender = await database_sync_to_async(NewsUsers.objects.get)(id=self.sender_id)

        # Connect zamanı hələ receiver məlum deyil, room_name yaradılmayacaq
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_text = data['message']
        receiver_name = data['receiver_name']

        # Sender və receiver obyektlərini DB-dən al
        receiver = await database_sync_to_async(NewsUsers.objects.get)(username=receiver_name)

        # Mesajı DB-də saxla
        await database_sync_to_async(Message.objects.create)(
            sender=self.sender,
            receiver=receiver,
            text=message_text
        )

        # Room adı yaradın (unikal: sender və receiver id-lərinə əsasən)
        room_name = f"{min(self.sender.id, receiver.id)}_{max(self.sender.id, receiver.id)}"
        room_group_name = f"chat_{room_name}"

        # Özünü və qarşı tərəfi qrupa əlavə et
        await self.channel_layer.group_add(room_group_name, self.channel_name)

        # Mesajı qrupa göndər
