from rest_framework import serializers
from django.db.models import Avg
from orders.models import Review
from .models import Item, ItemImage, Wishlist, WishlistItem


class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'image']


class ItemSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username',
                                            read_only=True)
    seller_rating = serializers.SerializerMethodField()
    seller_rating_count = serializers.SerializerMethodField()
    images = ItemImageSerializer(many=True, read_only=True)

    def get_seller_rating(self, obj):
        avg = Review.objects.filter(seller=obj.seller).aggregate(avg=Avg('rating'))['avg']
        return round(avg, 2) if avg else None

    def get_seller_rating_count(self, obj):
        return Review.objects.filter(seller=obj.seller).count()

    class Meta:
        model = Item
        fields = ['id', 'title', 'description', 'seller_rating', 'seller_rating_count',
                  'price', 'seller', 'seller_username', 'is_sold', 'images']
        read_only_fields = ['seller']


class WishlistItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "item", "note", "quantity", "added_at"]


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "items", "created_at"]