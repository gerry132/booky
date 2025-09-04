import pytest

CONV_LIST = "/api/messages/conversations/"
CONV_DETAIL = "/api/messages/conversations/{id}/"


@pytest.mark.django_db
def test_conversations_list_pagination_and_annotations(auth_client_a, seed_messages, conversation):
    # Expect pagination dict shape + annotations present
    res = auth_client_a.get(CONV_LIST)
    assert res.status_code == 200
    # paginated?
    assert {"count", "results"}.issubset(set(res.data.keys()))

    # our conv present
    conv = next(x for x in res.data["results"] if x["id"] == conversation.id)
    # annotation fields:
    assert "last_message_body" in conv
    assert "last_message_sender_username" in conv
    assert "last_message_at" in conv
    # unread count field:
    assert "unread_count_for_me" in conv
    # sanity: should be >= 0
    assert conv["unread_count_for_me"] >= 0


@pytest.mark.django_db
def test_conversation_detail_contains_usernames(auth_client_a, conversation):
    res = auth_client_a.get(CONV_DETAIL.format(id=conversation.id))
    assert res.status_code == 200
    assert res.data["buyer_username"] == "alice"
    assert res.data["seller_username"] == "bob"
    assert res.data["item_title"] == "Vintage Jacket"
