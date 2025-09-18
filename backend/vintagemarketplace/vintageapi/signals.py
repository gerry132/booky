# backend/app/shop/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wishlist


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_wishlist(sender, instance, created, **kwargs):
    if created:
        Wishlist.objects.get_or_create(user=instance)
