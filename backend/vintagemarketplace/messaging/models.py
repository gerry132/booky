from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from vintageapi.models import Item


class Conversation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE,
                             related_name='conversations')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name='conversations_as_buyer')
    seller = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='conversations_as_seller')
    created_at = models.DateTimeField(auto_now_add=True)
    buyer_last_read = models.DateTimeField(default=timezone.now)
    seller_last_read = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('item', 'buyer', 'seller')
        ordering = ['-created_at']

    def __str__(self):
        return f"Chat about '{self.item.title}' ({self.buyer} & {self.seller})"

    def unread_count_for(self, user):
        if user == self.buyer:
            last_read = self.buyer_last_read
        elif user == self.seller:
            last_read = self.seller_last_read
        else:
            return 0
        return self.messages.filter(
            created_at__gt=last_read
        ).exclude(sender=user).count()

    def mark_as_read(self, user):
        """Update the appropriate last_read timestamp for the user."""
        now = timezone.now()
        updated = False
        if user == self.buyer:
            self.buyer_last_read = now
            updated = True
        elif user == self.seller:
            self.seller_last_read = now
            updated = True
        if updated:
            self.save(update_fields=['buyer_last_read', 'seller_last_read'])
        return updated


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
