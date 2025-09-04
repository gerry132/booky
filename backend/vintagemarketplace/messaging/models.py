from django.utils import timezone
from django.db.models import Max
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
    buyer_last_read = models.DateTimeField(null=True, blank=True, default=None)
    seller_last_read = models.DateTimeField(null=True, blank=True, default=None)

    is_muted_by_buyer = models.BooleanField(default=False)
    is_muted_by_seller = models.BooleanField(default=False)

    buyer_deleted = models.BooleanField(default=False)
    seller_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('item', 'buyer', 'seller')
        ordering = ['-created_at']

    def __str__(self):
        return f"Chat about '{self.item.title}' ({self.buyer} & {self.seller})"

    def _last_read_for(self, user):
        uid = getattr(user, "id", None)
        if not uid:
            return None
        if uid == self.buyer_id:
            return self.buyer_last_read
        if uid == self.seller_id:
            return self.seller_last_read
        return None

    def unread_count_for(self, user):
        """
        Count messages from the *other* participant strictly after my last-read time.
        Never pass None values into queryset lookups.
        """
        uid = getattr(user, "id", None)
        if not uid:
            return 0  # anonymous / no user -> nothing unread

        if self.is_muted_for(user):
            return 0

        qs = self.messages.filter(is_deleted=False).exclude(sender_id=uid)

        last_read = self._last_read_for(user)
        if last_read is not None:
            qs = qs.filter(created_at__gt=last_read)  # only add comparison when value exists

        return qs.count()

    def is_muted_for(self, user) -> bool:
        if user.id == self.buyer_id:
            return self.is_muted_by_buyer
        if user.id == self.seller_id:
            return self.is_muted_by_seller
        return False

    def set_muted(self, user, value: bool):
        if user.id == self.buyer_id:
            self.is_muted_by_buyer = value
        elif user.id == self.seller_id:
            self.is_muted_by_seller = value
        self.save(update_fields=["is_muted_by_buyer", "is_muted_by_seller"])

    def mark_as_read(self, user):
        uid = getattr(user, "id", None)
        if uid not in (self.buyer_id, self.seller_id):
            return False  # ignore non-participants

        latest = (
            self.messages.filter(is_deleted=False)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        ) or timezone.now()

        if uid == self.buyer_id:
            if self.buyer_last_read != latest:
                self.buyer_last_read = latest
                self.save(update_fields=["buyer_last_read"])
                return True
        else:  # uid == self.seller_id
            if self.seller_last_read != latest:
                self.seller_last_read = latest
                self.save(update_fields=["seller_last_read"])
                return True
        return False


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
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocker", "blocked")

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


class UserReport(models.Model):
    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reports_made")
    reported = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reports_received")
    conversation = models.ForeignKey(
        "Conversation", null=True, blank=True, on_delete=models.SET_NULL)
    message = models.ForeignKey(
        "Message", null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    def __str__(self):
        return f"Report {self.id} by {self.reporter} -> {self.reported}"
