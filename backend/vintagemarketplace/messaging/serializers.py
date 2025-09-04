# messaging/serializers.py
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Conversation, Message, UserBlock, UserReport
from vintageapi.models import Item
from rest_framework.exceptions import ValidationError


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



class ConversationSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True)
    buyer_username = serializers.CharField(source="buyer.username", read_only=True)
    seller_username = serializers.CharField(source="seller.username", read_only=True)
    is_muted_for_me = serializers.SerializerMethodField()
    # Make PKs read-only so DRF never asks for them in POST
    buyer = serializers.PrimaryKeyRelatedField(read_only=True)
    seller = serializers.PrimaryKeyRelatedField(read_only=True)

    # Make item explicitly writable (so validated_data has an Item instance)
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())

    last_message_body = serializers.ReadOnlyField()
    last_message_sender_username = serializers.ReadOnlyField()
    last_message_at = serializers.ReadOnlyField()
    unread_count_for_me = serializers.SerializerMethodField()

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
            "unread_count_for_me",
        ]
        read_only_fields = [
            "buyer", "seller", "created_at",
            "last_message_body", "last_message_sender_username",
            "last_message_at",
            "item_title", "buyer_username", "seller_username",
        ]

    def get_is_muted_for_me(self, obj):
        user = self.context["request"].user
        return obj.is_muted_for(user)

    def get_unread_count_for_me(self, obj):
        user = self.context["request"].user
        return 0 if not user.is_authenticated else obj.unread_count_for(user)

    def validate(self, attrs):
        # Optional early self-convo guard
        request = self.context.get("request")
        item = attrs.get("item")
        if request and item and getattr(item, "owner", None) == request.user:
            raise ValidationError("You cannot start a conversation with yourself.")
        return attrs

    def create(self, validated_data):
        """Derive buyer/seller here so POST never needs them."""
        request = self.context["request"]
        item = validated_data["item"]
        buyer = request.user
        seller = getattr(item, "owner", None) or getattr(item, "seller", None)
        if seller is None:
            raise ValidationError({"item": ["Item has no seller/owner configured."]})
        if buyer == seller:
            raise ValidationError({"detail": "You cannot start a conversation with yourself."})
        convo, _ = Conversation.objects.get_or_create(item=item, buyer=buyer, seller=seller)
        return convo


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