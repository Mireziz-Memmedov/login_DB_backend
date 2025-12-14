import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import NewsUsers, Message

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # 1️⃣ Sender id URL-dən alınır
        self.sender_id = self.scope['url_route']['kwargs']['user_id']

        # 2️⃣ Receiver adı frontend-dən gələn query param və ya JSON olacaq
        #    Amma connect zamanı hələ məlum deyil, receive-də alacağıq
        
        # 3️⃣ Qoşulma zamanı room_name yaradılır, burada sadəcə self.room_group_name saxlayırıq
        #    Dəqiq room_name receive-də sender/receiver məlum olduqda təkrar hesablanacaq
        await self.accept()  # WebSocket connection-u qəbul et

    async def receive(self, text_data):
        # 1️⃣ Frontend-dən JSON-u parse et
        data = json.loads(text_data)
        message_text = data['message']
        receiver_name = data['receiver_name']

        # 2️⃣ Sender və receiver obyektlərini DB-dən al (async)
        sender = await database_sync_to_async(NewsUsers.objects.get)(id=self.sender_id)
        receiver = await database_sync_to_async(NewsUsers.objects.get)(username=receiver_name)

        # 3️⃣ Mesajı DB-də saxla
        await database_sync_to_async(Message.objects.create)(
            sender=sender,
            receiver=receiver,
            text=message_text
        )

        # 4️⃣ Room adı yaradın (unikal)
        room_name = f"{min(sender.id, receiver.id)}_{max(sender.id, receiver.id)}"
        self.room_group_name = f"chat_{room_name}"

        # 5️⃣ Qrupa göndər
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender': sender.username
            }
        )

    async def chat_message(self, event):
        # 6️⃣ Qrupdan gələn mesajı WebSocket-ə göndər
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender']
        }))
