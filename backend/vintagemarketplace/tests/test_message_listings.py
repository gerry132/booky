import pytest

CONV_MSGS = "/api/messages/conversations/{id}/messages/"


@pytest.mark.django_db
def test_messages_list_default_order_is_newest_last(auth_client_a, seed_messages, conversation):
    """
    The API should return messages oldest→newest by default,
    i.e., newest-last (good for chat scroll).
    """
    res = auth_client_a.get(CONV_MSGS.format(id=conversation.id))
    assert res.status_code == 200
    assert {"count", "results"}.issubset(res.data.keys())
    texts = [m["body"] for m in res.data["results"]]

    assert texts == ["Hi", "Hello", "Interested!"]


@pytest.mark.django_db
def test_messages_list_newest_first_when_toggled(auth_client_a, seed_messages, conversation):
    """
    If you support ?newest_last=false (or ?ordering=-created_at),
    newest message should come first.
    """
    # Try both – adjust to your implementation
    res = auth_client_a.get(CONV_MSGS.format(id=conversation.id) + "?newest_last=false")
    if res.status_code == 200 and "results" in res.data:
        texts = [m["body"] for m in res.data["results"]]
        assert texts == ["Interested!", "Hello", "Hi"]
        return

    # fallback to ordering
    res = auth_client_a.get(CONV_MSGS.format(id=conversation.id) + "?ordering=-created_at")
    assert res.status_code == 200
    texts = [m["body"] for m in res.data["results"]]
    assert texts == ["Interested!", "Hello", "Hi"]


@pytest.mark.django_db
def test_messages_pagination_page_size_and_next(auth_client_a, conversation, user_a):
    # create multiple messages to force pagination
    from messaging.models import Message
    for i in range(35):
        Message.objects.create(conversation=conversation, sender=user_a, body=f"m{i}")

    res = auth_client_a.get(CONV_MSGS.format(id=conversation.id) + "?page_size=20")
    assert res.status_code == 200
    assert res.data["count"] == 35 + 0  # plus any from seed if you used it here
    assert len(res.data["results"]) == 20
    assert res.data["next"]  # should be a URL
