# messaging/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.conf import settings
from .models import Conversation, Message, UserBlock, UserReport
from vintageapi.models import Item
from rest_framework.exceptions import ValidationError


MAX_IMAGE_MB = getattr(settings, "CHAT_MAX_IMAGE_MB", 5)
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "sender_username", "body", "image", "image_url", "created_at"]
        read_only_fields = ["sender", "sender_username", "created_at", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def validate(self, attrs):
        img = attrs.get("image")
        if img:
            # content type & size
            ctype = getattr(img, "content_type", "") or ""
            if ctype not in ALLOWED_IMAGE_MIME:
                raise serializers.ValidationError({"image": ["Unsupported image type."]})
            if img.size > MAX_IMAGE_MB * 1024 * 1024:
                raise serializers.ValidationError({"image": [f"Image must be ≤ {MAX_IMAGE_MB}MB."]})
        body = (attrs.get("body") or "").strip()
        if not body and not img and self.instance is None:
            raise serializers.ValidationError({"non_field_errors": ["Message must contain text or an image."]})
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    buyer_username = serializers.CharField(source="buyer.username", read_only=True)
    seller_username = serializers.CharField(source="seller.username", read_only=True)
    is_muted_for_me = serializers.SerializerMethodField()
    buyer = serializers.PrimaryKeyRelatedField(read_only=True)
    seller = serializers.PrimaryKeyRelatedField(read_only=True)
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())

    last_message_body = serializers.ReadOnlyField()
    last_message_sender_username = serializers.ReadOnlyField()
    last_message_at = serializers.DateTimeField(read_only=True)
    last_read_for_me = serializers.SerializerMethodField()
    unread_count_for_me = serializers.SerializerMethodField()
    other_last_read_for_me = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "item", "item_title",
            "buyer", "buyer_username",
            "seller", "seller_username",
            "created_at",
            "last_message_body", "last_message_sender_username",
            "last_message_at",
            "is_muted_for_me",
            "last_read_for_me",
            "unread_count_for_me",
            "other_last_read_for_me",
        ]
        read_only_fields = [
            "buyer", "seller", "created_at",
            "last_message_body", "last_message_sender_username",
            "last_message_at",
            "item_title", "buyer_username", "seller_username",
        ]

    def get_last_read_for_me(self, obj):
        u = self._get_for_user()
        ts = obj._last_read_for(u) if u else None
        return ts.isoformat() if ts else None

    def get_is_muted_for_me(self, obj):
        user = self._get_for_user()
        if not user:
            return False
        return obj.is_muted_for(user)

    def get_unread_count_for_me(self, obj):
        user = self._get_for_user()
        uid = getattr(user, "id", None)
        if not uid:
            return 0
        return obj.unread_count_for(user)


    def get_other_last_read_for_me(self, obj):
        u = self._get_for_user()
        uid = getattr(u, "id", None)
        ts = None
        if uid == obj.buyer_id:
            ts = obj.seller_last_read
        elif uid == obj.seller_id:
            ts = obj.buyer_last_read
        return ts.isoformat() if ts else None


    def _get_for_user(self):
        """
        Prefer explicit 'for_user' or 'for_user_id' (WS/broadcast),
        else fall back to request.user (HTTP).
        """
        user = self.context.get("for_user")
        if user is not None:
            return user

        user_id = self.context.get("for_user_id")
        if user_id is not None:
            # lightweight shim with attrs used by your methods
            class _U:
                def __init__(self, _id):
                    self.id = _id
                    self.pk = _id
                @property
                def is_authenticated(self):  # if anything checks this
                    return True
            return _U(user_id)

        req = self.context.get("request")
        return getattr(req, "user", None)


class UserBlockSerializer(serializers.ModelSerializer):
    blocker_username = serializers.CharField(source="blocker.username", read_only=True)
    blocked_username = serializers.CharField(source="blocked.username", read_only=True)
    blocked = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all()
    )

    class Meta:
        model = UserBlock
        fields = ["id", "blocker", "blocker_username", "blocked", "blocked_username", "created_at"]
        read_only_fields = ["blocker", "created_at", "blocker_username", "blocked_username"]

    def create(self, validated_data):
        validated_data["blocker"] = self.context["request"].user
        return super().create(validated_data)


class UserReportSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source="reporter.username", read_only=True)
    reported_username = serializers.CharField(source="reported.username", read_only=True)
    reported = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all()
    )

    class Meta:
        model = UserReport
        fields = [
            "id", "reporter", "reporter_username",
            "reported", "reported_username",
            "conversation", "message",
            "reason", "details",
            "created_at", "handled",
        ]
        read_only_fields = ["reporter", "created_at", "handled", "reporter_username", "reported_username"]

    def create(self, validated_data):
        validated_data["reporter"] = self.context["request"].user
        return super().create(validated_data)