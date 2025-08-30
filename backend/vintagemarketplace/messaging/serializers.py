from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(
        source='sender.username', read_only=True)
    image = serializers.ImageField(read_only=False, 
                                   required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_username', 'body',
                  'created_at', 'image']
        read_only_fields = ['sender', 'sender_username', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source='item.title', read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'item', 'item_title', 'buyer', 'seller', 'created_at',
            'unread_count'
        ]
        read_only_fields = ['buyer', 'seller', 'created_at', 'unread_count']

    def get_unread_count(self, obj):
        """Return unread messages for the current user."""
        user = self.context.get('request').user
        # Don't return for unauthenticated users (shouldn't happen in chat)
        if not user or user.is_anonymous:
            return 0
        return obj.unread_count_for(user)
