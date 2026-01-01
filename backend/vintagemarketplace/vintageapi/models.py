from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone

from catalog.models import Category, Brand, Tag

User = get_user_model()


class Item(models.Model):
    title = models.CharField(max_length=100)
    is_sold = models.BooleanField(default=False)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items")

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items", null=True)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)

    condition = models.CharField(max_length=24, null=True, choices=[
        ("NWT", "New with tags"), ("LN", "Like new"), ("G", "Good"), ("F", "Fair")
    ])
    size = models.CharField(max_length=24, blank=True)
    colors = models.JSONField(default=list, blank=True)
    materials = models.JSONField(default=list, blank=True)
    styles = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title


class ItemImage(models.Model):
    item = models.ForeignKey(
        'Item', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='item_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Wishlist(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Wishlist<{self.user.id}>"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "vintageapi.Item", on_delete=models.CASCADE, related_name="wishlisted_in")
    note = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)  # optional
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["wishlist", "product"],
                                    name="uniq_wishlist_product")
        ]

    def __str__(self):
        return f"{self.wishlist.id}:{self.item.id}"