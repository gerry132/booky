import io
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from vintageapi.models import Item
from messaging.models import Conversation, Message
from PIL import Image

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vintagemarketplace.settings_test")

import django
django.setup()


@pytest.fixture
@pytest.mark.django_db
def user_a():
    return User.objects.create_user(username="alice", password="pass123")


@pytest.fixture
@pytest.mark.django_db
def user_b():
    return User.objects.create_user(username="bob", password="pass123")


@pytest.fixture
@pytest.mark.django_db
def user_c():
    return User.objects.create_user(username="carl", password="pass123")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client_a(api_client, user_a, db):
    c = APIClient()                 # NEW instance
    c.force_authenticate(user=user_a)
    api_client.force_authenticate(user=user_a)
    return api_client


@pytest.fixture
def auth_client_b(api_client, user_b, db):
    c = APIClient()                 # NEW instance
    c.force_authenticate(user=user_b)    
    return api_client

@pytest.fixture
@pytest.mark.django_db
def item(user_b):
    # Bob sells an item
    return Item.objects.create(
        title="Vintage Jacket",
        description="Nice",
        price="49.99",
        seller=user_b,
    )


@pytest.fixture
@pytest.mark.django_db
def conversation(user_a, user_b, item):
    # buyer: alice, seller: bob
    return Conversation.objects.create(item=item, buyer=user_a, seller=user_b)


@pytest.fixture
def make_png_file():
    """
    Creates a tiny in-memory PNG for upload tests.
    """
    def _factory(name="test.png", size=(20, 20), color=(255, 0, 0, 0)):
        buf = io.BytesIO()
        img = Image.new("RGBA", size, color)
        img.save(buf, format="PNG")
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="image/png")
    return _factory


@pytest.fixture
@pytest.mark.django_db
def seed_messages(conversation, user_a, user_b):
    """
    Create a few messages in the conversation: older -> newer
    """
    Message.objects.create(conversation=conversation, sender=user_a, body="Hi")
    Message.objects.create(conversation=conversation, sender=user_b, body="Hello")
    Message.objects.create(conversation=conversation, sender=user_a, body="Interested!")
    return conversation
