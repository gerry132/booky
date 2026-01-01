# messaging/utils.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .serializers import ConversationSerializer, MessageSerializer
from .models import UserBlock  # (unchanged)

channel_layer = get_channel_layer()

def broadcast_conversation_upsert(convo, for_user_id: int):
    """
    Send an upsert of a conversation to the user's inbox group.
    Serializer gets per-user context so fields like other_last_read_for_me are correct.
    """
    data = ConversationSerializer(
        convo,
        context={"for_user_id": for_user_id},
    ).data

    # ✅ align with InboxConsumer group name
    group_name = f"inbox_user_{for_user_id}"

    # ✅ align with InboxConsumer handler name (dot -> underscore)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "inbox.conversation_upsert",  # maps to InboxConsumer.inbox_conversation_upsert
            "conversation": data,
        },
    )


def broadcast_conversation_deleted(convo_id, user_ids):
    for uid in user_ids:
        async_to_sync(channel_layer.group_send)(
            f"inbox_user_{uid}",
            {"type": "inbox.conversation_deleted", "id": convo_id},
        )

def broadcast_unread_counts(user, counts_dict):
    async_to_sync(channel_layer.group_send)(
        f"inbox_user_{user.id}",
        {"type": "inbox.unread_counts", "counts": counts_dict},
    )

def broadcast_message_new(message):
    convo = message.conversation
    data = MessageSerializer(message).data
    for uid in (convo.buyer_id, convo.seller_id):
        async_to_sync(channel_layer.group_send)(
            f"inbox_user_{uid}",
            {"type": "inbox.message_new", "conversation": convo.id, "message": data},
        )

def _is_blocked(a, b):
    return UserBlock.objects.filter(
        blocker=a,
        blocked=b).exists() or UserBlock.objects.filter(
        blocker=b, blocked=a).exists()
