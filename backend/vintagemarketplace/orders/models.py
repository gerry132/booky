from django.db import models
from django.contrib.auth.models import User
from vintageapi.models import Item
from django.conf import settings


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_reference = models.CharField(max_length=128, blank=True, null=True)  # Stripe payment intent ID, etc.

    def __str__(self):
        return f"Order #{self.id} by {self.buyer.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item.title}"


class Review(models.Model):
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='reviews')
    item = models.ForeignKey('vintageapi.Item', on_delete=models.CASCADE, related_name='reviews')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL,
                               on_delete=models.CASCADE, related_name='received_reviews')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE, related_name='written_reviews')
    rating = models.PositiveSmallIntegerField()  # e.g. 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('order', 'item', 'buyer')  # Prevent duplicate reviews for same purchase

    def __str__(self):
        return f"{self.buyer} → {self.seller} ({self.rating})"
