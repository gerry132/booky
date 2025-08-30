from rest_framework import serializers
from django.contrib.auth.models import User
from orders.models import Review
from .models import Profile
from django.db.models import Avg


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'display_name', 'bio', 'profile_image', 'location',
            'average_rating', 'review_count', 'items'
        ]

    def get_average_rating(self, obj):
        user = obj.user
        avg = Review.objects.filter(seller=user).aggregate(avg=Avg('rating'))['avg']
        return round(avg, 2) if avg else None

    def get_review_count(self, obj):
        user = obj.user
        return Review.objects.filter(seller=user).count()

    def get_items(self, obj):
        from vintageapi.serializers import ItemSerializer
        items = obj.user.items.all()
        return ItemSerializer(items, many=True).data