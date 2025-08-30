from rest_framework import serializers
from .models import Order, OrderItem, Review
from vintageapi.serializers import ItemSerializer
from vintageapi.models import Item


class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=OrderItem.objects.all(), source='item', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'item_id', 'price']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    order_items_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'buyer', 'status', 'created_at', 'updated_at',
            'total_amount', 'payment_reference', 'order_items', 'order_items_data'
        ]
        read_only_fields = ['buyer', 'created_at', 'updated_at', 'total_amount', 'payment_reference', 'order_items']

    def create(self, validated_data):
        buyer = self.context['request'].user
        items_data = self.initial_data.get('order_items_data', [])
        order = Order.objects.create(buyer=buyer)
        total = 0
        for item_data in items_data:
            item = Item.objects.get(pk=item_data['item_id'])
            price = item.price  # or use a "final price" field if items can change price later
            OrderItem.objects.create(order=order, item=item, price=price)
            total += price
        order.total_amount = total
        order.save()
        return order


class ReviewSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    item_title = serializers.CharField(source='item.title', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'order', 'item', 'seller', 'buyer', 'rating', 'comment', 'created_at',
            'buyer_username', 'seller_username', 'item_title'
        ]
        read_only_fields = ['buyer', 'seller', 'order', 'item', 'created_at']
