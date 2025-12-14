import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import NewsUsers, Message

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Sender id URL-dən alınır
        self.sender_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.sender = await database_sync_to_async(NewsUsers.objects.get)(id=self.sender_id)
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')
        
        if msg_type == "chat_message":
            await self.handle_chat_message(data)
        elif msg_type == "load_messages":
            await self.handle_load_messages(data)

    async def handle_chat_message(self, data):
        message_text = data['message']
        receiver_name = data['receiver_name']

        receiver = await database_sync_to_async(NewsUsers.objects.get)(username=receiver_name)

        # Mesajı DB-də saxla
        await database_sync_to_async(Message.objects.create)(
            sender=self.sender,
            receiver=receiver,
            text=message_text
        )

        # Room adı yaradın
        room_name = f"{min(self.sender.id, receiver.id)}_{max(self.sender.id, receiver.id)}"
        room_group_name = f"chat_{room_name}"

        # Özünü qrupa əlavə et
        await self.channel_layer.group_add(room_group_name, self.channel_name)

        # Mesajı qrupa göndər
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender': self.sender.username
            }
        )

    async def handle_load_messages(self, data):
        target_user = data['target_user']
        receiver = await database_sync_to_async(NewsUsers.objects.get)(username=target_user)

        # Mesajları DB-dən al
        messages = await database_sync_to_async(
            lambda: list(Message.objects.filter(
                sender__in=[self.sender, receiver],
                receiver__in=[self.sender, receiver]
            ).order_by('id').values('sender__username', 'text'))
        )()

        formatted_messages = [{'sender': m['sender__username'], 'text': m['text']} for m in messages]

        await self.send(text_data=json.dumps({
            'type': 'load_messages',
            'messages': formatted_messages
        }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender']
        }))