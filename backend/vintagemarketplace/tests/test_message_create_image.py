import pytest

MSG_CREATE = "/api/messages/messages/"
CONV_MSGS = "/api/messages/conversations/{id}/messages/"


@pytest.mark.django_db
def test_create_text_message(auth_client_a, conversation):
    res = auth_client_a.post(
        MSG_CREATE, {"conversation": conversation.id, "body": "Hello!"}, format="multipart"
    )
    assert res.status_code == 201
    assert res.data["body"] == "Hello!"
    assert res.data["sender_username"] == "alice"


@pytest.mark.django_db
def test_create_image_message_builds_image_url(auth_client_a, conversation, make_png_file):
    img = make_png_file()
    res = auth_client_a.post(
        MSG_CREATE,
        {"conversation": conversation.id, "image": img},
        format="multipart",
    )
    assert res.status_code == 201
    assert res.data["image"]  # file path
    assert res.data["image_url"]  # absolute URL built in serializer

    # Verify it round-trips in the list endpoint
    list_res = auth_client_a.get(CONV_MSGS.format(id=conversation.id))
    assert list_res.status_code == 200
    found = any(m.get("image_url") for m in list_res.data["results"])
    assert found
