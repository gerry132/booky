import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Conversation, Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_name}"
        logger.info("WS connect %s path=%s", self.scope.get("client"), self.scope.get("path"))

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # --- SEND MESSAGE HISTORY HERE ---
        messages = await self.get_history(self.room_name)
        await self.send(text_data=json.dumps({
            "type": "chat_history",
            "messages": messages
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        sender = data.get("sender")

        # (Optional) Save to DB
        msg_obj = await self.save_message(self.room_name, sender, message)

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": msg_obj.id,
                    "body": msg_obj.body,
                    "sender_username": msg_obj.sender.username,
                    "created_at": msg_obj.created_at.isoformat(),
                }
            }
        )

    # Receive message from group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"]
        }))

    # --- DB helper to fetch history as dicts ---
    @staticmethod
    async def get_history(room_name):
        from channels.db import database_sync_to_async
        @database_sync_to_async
        def fetch():
            try:
                convo = Conversation.objects.get(id=room_name)
                qs = Message.objects.filter(conversation=convo).order_by("created_at")
                return MessageSerializer(qs, many=True).data
            except Conversation.DoesNotExist:
                return []
        return await fetch()

    # --- DB helper to save message ---
    @staticmethod
    async def save_message(room_name, sender_username, message):
        from channels.db import database_sync_to_async
        @database_sync_to_async
        def save():
            convo = Conversation.objects.get(id=room_name)
            from django.contrib.auth.models import User
            user = User.objects.get(username=sender_username)
            return Message.objects.create(conversation=convo, sender=user, body=message)
        return await save()
