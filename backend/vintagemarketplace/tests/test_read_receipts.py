import time
import pytest
from django.utils import timezone

CONV_LIST = "/api/messages/conversations/"
CONV_MSGS = "/api/messages/conversations/{id}/messages/"
MARK_READ = "/api/messages/conversations/{id}/read/"


@pytest.mark.django_db
def test_unread_count_changes_on_mark_read(auth_client_a, auth_client_b, conversation, user_b):
    # Bob sends two messages after a small delay to ensure created_at ordering
    from messaging.models import Message
    time.sleep(0.05)
    Message.objects.create(conversation=conversation, sender=user_b, body="msg1")
    time.sleep(0.05)
    Message.objects.create(conversation=conversation, sender=user_b, body="msg2")

    print("buyer_last_read:", conversation.buyer_last_read, "seller_last_read:", conversation.seller_last_read)
    print("msg times:", list(conversation.messages.values_list("created_at", flat=True)))
    # Alice (buyer) sees unread_count_for_me > 0
    convs = auth_client_a.get(CONV_LIST).data["results"]
    conv = next(x for x in convs if x["id"] == conversation.id)
    assert conv["unread_count_for_me"] >= 2

    # Alice marks read
    res = auth_client_a.post(MARK_READ.format(id=conversation.id))
    assert res.status_code in (200, 204)

    # unread should drop to 0
    convs = auth_client_a.get(CONV_LIST).data["results"]
    conv = next(x for x in convs if x["id"] == conversation.id)
    assert conv["unread_count_for_me"] == 0
