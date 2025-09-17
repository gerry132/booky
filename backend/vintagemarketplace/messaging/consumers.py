import json
from channels.generic.websocket import (AsyncWebsocketConsumer,
                                        AsyncJsonWebsocketConsumer)
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Conversation
from urllib.parse import parse_qs
from rest_framework.authtoken.models import Token # or your JWT checker
from django.db.models import Q, Subquery, OuterRef
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
import logging


log = logging.getLogger(__name__)

class InboxConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        log.warning("InboxConsumer: ENTER connect()")
        user = self.scope.get("user")
        log.warning("InboxConsumer: user=%r auth=%r", getattr(user, "id", None), getattr(user, "is_authenticated", False))

        if not user or not user.is_authenticated:
            log.warning("InboxConsumer: closing 4001 (unauth)")
            await self.close(code=4001)
            return

        self.user = user
        self.group = f"inbox_user_{user.id}"

        try:
            log.warning("InboxConsumer: about to ACCEPT")
            await self.accept()
            log.warning("InboxConsumer: ACCEPTED")

            if not self.channel_layer:
                log.error("InboxConsumer: NO channel layer")
                await self.send_json({"type": "error", "detail": "no channel layer"})
                await self.close(code=1011)
                return

            log.warning("InboxConsumer: about to GROUP_ADD %s", self.group)
            await self.channel_layer.group_add(self.group, self.channel_name)
            log.warning("InboxConsumer: GROUP_ADD done")

            log.warning("InboxConsumer: about to SNAPSHOT")
            convos = await self._snapshot_conversations()
            log.warning("InboxConsumer: SNAPSHOT done (%d items)", len(convos))
            await self.send_json({"type": "conversations_snapshot", "conversations": convos})
            log.warning("InboxConsumer: SNAPSHOT sent")

        except Exception:
            log.exception("InboxConsumer.connect crashed")
            try:
                await self.send_json({"type": "error", "detail": "server error during connect"})
            except Exception:
                pass
            await self.close(code=1011)

    async def disconnect(self, code):
        try:
            if hasattr(self, "group"):
                await self.channel_layer.group_discard(self.group, self.channel_name)
        except Exception:
            log.exception("InboxConsumer.disconnect error")

    async def inbox_message_new(self, event):
        await self.send_json({"type": "message_new", **event})

    async def inbox_conversation_upsert(self, event):
        await self.send_json({"type": "conversation_upsert", **event})

    async def inbox_conversation_deleted(self, event):
        await self.send_json({"type": "conversation_deleted", **event})

    async def inbox_unread_counts(self, event):
        await self.send_json({"type": "unread_counts", **event})

    @database_sync_to_async
    def _snapshot_conversations(self):
        last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")
        qs = (
            Conversation.objects
            .filter(Q(buyer=self.user) | Q(seller=self.user))
            .annotate(
                last_message_body=Subquery(last.values("body")[:1]),
                last_message_sender_username=Subquery(last.values("sender__username")[:1]),
                last_message_at=Subquery(last.values("created_at")[:1]),
            )
            .order_by("-last_message_at", "-created_at")
            .select_related("item", "buyer", "seller")
        )

        def iso(dt): return dt.isoformat() if dt else None

        out = []
        for c in qs:
            out.append({
                "id": c.id,
                "item_title": getattr(getattr(c, "item", None), "title", "") or "",
                "buyer_id": c.buyer_id,
                "seller_id": c.seller_id,
                "unread_count_for_me": getattr(c, "unread_count_for_me", 0),
                "last_message_body": getattr(c, "last_message_body", None),
                "last_message_sender_username": getattr(c, "last_message_sender_username", None),
                "last_message_at": iso(getattr(c, "last_message_at", None)),
                "created_at": iso(getattr(c, "created_at", None)),
            })
        return out


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.convo_id = self.scope["url_route"]["kwargs"]["convo_id"]
        self.group = f"chat_{self.convo_id}"
        user = self.scope.get("user") or AnonymousUser()

        if not await self._user_is_participant(getattr(user, "id", None), self.convo_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"type": "hello", "room": self.convo_id}))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except Exception:
            return

        if payload.get("type") == "typing":
            await self.channel_layer.group_send(self.group, {
                "type": "typing.event",
                "username": getattr(self.scope.get("user"), "username", "anon"),
            })
            return

        msg = (payload.get("message") or "").strip()
        if not msg:
            return

        sender = getattr(self.scope.get("user"), "username", "anon")
        await self.channel_layer.group_send(self.group, {
            "type": "chat.message",
            "sender": sender,
            "message": msg,
        })

    async def chat_message(self, event):
        if "sender" not in event or "message" not in event:
            log.warning("chat.message missing fields (origin=%s): %r", event.get("origin"), event)

        sender = event.get("sender") or getattr(self.scope.get("user", None), "username", None) or "system"
        msg    = event.get("message")

        payload = msg if isinstance(msg, dict) else {
            "id": None,
            "body": msg or "",
            "image_url": None,
            "sender_username": sender,
            "created_at": None,
        }

        await self.send(json.dumps({"type": "chat_message", "message": payload}))
    async def typing_event(self, event):
        await self.send(json.dumps({
            "type": "typing",
            "username": event["username"],
        }))

    async def read_receipt(self, event):
        # fan out to both clients in this room
        await self.send_json({
            "type": "read_receipt",
            "conversation_id": event["conversation_id"],
            "reader_username": event["reader_username"],
            "last_read_at": event["last_read_at"],
        })

    @database_sync_to_async
    def _user_is_participant(self, user_id, convo_id):
        if not user_id:
            return False
        try:
            c = Conversation.objects.get(pk=convo_id)
            return c.buyer_id == user_id or c.seller_id == user_id
        except Conversation.DoesNotExist:
            return False
