import pytest

MSG_CREATE = "/api/messages/messages/"


@pytest.mark.django_db
def test_non_participant_cannot_post_in_convo(api_client, user_c, conversation):
    api_client.force_authenticate(user=user_c)
    res = api_client.post(
        MSG_CREATE, {"conversation": conversation.id, "body": "hi"}, format="multipart"
    )
    assert res.status_code in (403, 404)
