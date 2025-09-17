from .models import UserBlock
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .serializers import ConversationSerializer, MessageSerializer

channel_layer = get_channel_layer()


def broadcast_conversation_upsert(convo, for_user_id=None):
    """
    Send an upsert of a conversation to the user's inbox group.
    If for_user_id is supplied, serializer computes per-user fields correctly.
    """
    channel_layer = get_channel_layer()
    data = ConversationSerializer(
        convo,
        context={"for_user_id": for_user_id},  # <-- critical
    ).data

    group_name = f"user_inbox_{for_user_id}" if for_user_id else None
    if group_name:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "inbox.upsert",
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
