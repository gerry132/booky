import pytest

CONV_LIST = "/api/messages/conversations/"
CONV_DETAIL = "/api/messages/conversations/{id}/"
CONV_MSGS = "/api/messages/conversations/{id}/messages/"
MSG_CREATE = "/api/messages/messages/"


@pytest.mark.django_db
def test_only_participants_can_view_conversation(
    api_client, auth_client_a, user_c, conversation
):
    # Alice (participant) can access
    res = auth_client_a.get(CONV_DETAIL.format(id=conversation.id))
    assert res.status_code == 200

    # Carl (not participant) cannot
    api_client.force_authenticate(user=user_c)
    res = api_client.get(CONV_DETAIL.format(id=conversation.id))
    assert res.status_code in (403, 404)  # depending on how you implemented permission denial


@pytest.mark.django_db
def test_only_participants_can_list_messages(
    api_client, auth_client_a, conversation, user_c
):
    # Alice OK
    res = auth_client_a.get(CONV_MSGS.format(id=conversation.id))
    assert res.status_code == 200

    # Carl denied
    api_client.force_authenticate(user=user_c)
    res = api_client.get(CONV_MSGS.format(id=conversation.id))
    assert res.status_code in (403, 404)


@pytest.mark.django_db
def test_sender_is_ignored_from_payload(auth_client_a, conversation):
    # Try to spoof sender in POST — backend should override with request.user
    res = auth_client_a.post(
        MSG_CREATE,
        {"conversation": conversation.id, "body": "Sneaky", "sender": 999},
        format="multipart",
    )
    assert res.status_code == 201
    assert res.data["sender_username"] == "alice"
