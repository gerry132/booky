# messaging/views.py
from django.db.models import Q, Subquery, OuterRef
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied, ValidationError
from .utils import (
    broadcast_message_new,
    broadcast_conversation_upsert
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, Message, UserReport, UserBlock
from .serializers import (ConversationSerializer,
                          MessageSerializer,
                          UserBlockSerializer,
                          UserReportSerializer)
from .utils import _is_blocked
from vintageapi.models import Item


def _other_user(convo, me):
    return convo.seller if convo.buyer_id == me.id else convo.buyer


# ---- pagination ----
class MessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ---- permissions ----
class IsParticipant(permissions.BasePermission):
    """Only buyer/seller of a conversation can access it."""
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Conversation):
            return obj.buyer_id == request.user.id or obj.seller_id == request.user.id
        if isinstance(obj, Message):
            c = obj.conversation
            return c.buyer_id == request.user.id or c.seller_id == request.user.id
        return False


# ---- viewsets ----
class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    # For object actions we also enforce IsParticipant
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("retrieve", "update", "partial_update", "destroy", "messages", "read"):
            return [permissions.IsAuthenticated(), IsParticipant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        blocked_ids = list(UserBlock.objects.filter(blocker=user).values_list(
            "blocked_id", flat=True)) + \
                    list(UserBlock.objects.filter(blocked=user).values_list(
                        "blocker_id", flat=True))

        # Subqueries for last message details
        last_msg = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")

        return (
            Conversation.objects
            .filter(Q(buyer=user) | Q(seller=user)).exclude(
                    Q(buyer_id__in=blocked_ids) | Q(seller_id__in=blocked_ids)
            )
            .annotate(
                last_message_body=Subquery(last_msg.values("body")[:1]),
                last_message_sender_username=Subquery(
                    last_msg.values("sender__username")[:1]),
                last_message_at=Subquery(last_msg.values("created_at")[:1]),
            )
            .order_by("-last_message_at", "-created_at")
        )

    def create(self, request, *args, **kwargs):

        item_id = request.data.get("item")
        if not item_id:
            return Response({"item": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        item = get_object_or_404(Item, pk=item_id)
        buyer = request.user
        seller = getattr(item, "owner", None) or getattr(item, "seller", None)
        if _is_blocked(buyer, seller):
            return Response({"detail": "You cannot message this user."},
                            status=403)
        if seller is None:
            raise ValidationError(
                {"item": ["Item has no seller/owner configured."]})
        if buyer == seller:
            return Response(
                {"detail": "You cannot start a conversation with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        convo, created = Conversation.objects.get_or_create(item=item, buyer=buyer, seller=seller)
        data = self.get_serializer(convo, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Paginated messages.

        Default: oldest -> newest (newest LAST) for chat scroll.
        Toggle newest-first via either:
          - ?newest_last=false
          - or ?ordering=-created_at
        (Also supports ?order=newest and ?newest_first=1/true for flexibility.)
        """
        convo = self.get_object()

        def truthy(v):
            return str(v).lower() in {"1", "true", "yes", "on"}

        newest_first = False  # default

        # A) ?newest_last=false  => newest first
        newest_last = request.query_params.get("newest_last")
        if newest_last is not None:
            newest_first = not truthy(newest_last)
        else:
            # B) DRF-style ordering
            ordering_param = (request.query_params.get("ordering") or "").strip()
            if ordering_param in {"-created_at", "-id", "-pk"}:
                newest_first = True
            elif ordering_param in {"created_at", "id", "pk"}:
                newest_first = False
            else:
                # C) Alternate toggles
                order_param = (request.query_params.get("order") or "").lower()
                if order_param in {"newest", "desc", "descending"}:
                    newest_first = True
                newest_first_flag = request.query_params.get("newest_first")
                if newest_first_flag is not None:
                    newest_first = truthy(newest_first_flag) or newest_first

        # Stable ordering with tie-breaker to avoid shuffles on equal timestamps
        ordering = ("-created_at", "-id") if newest_first else ("created_at", "id")
        qs = convo.messages.order_by(*ordering)
        # --- NEW: filters ---
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(body__icontains=q)

        has_image = request.query_params.get("has_image")
        if has_image is not None and truthy(has_image):
            qs = qs.filter(image__isnull=False)

        sender_filter = (request.query_params.get("from") or "").strip().lower()
        if sender_filter:
            if sender_filter in {"me", "self"}:
                qs = qs.filter(sender=request.user)
            elif sender_filter in {"other", "them"}:
                other_id = convo.seller_id if request.user.id == convo.buyer_id else convo.buyer_id
                qs = qs.filter(sender_id=other_id)
            else:
                # allow username
                qs = qs.filter(sender__username=sender_filter)

        paginator = MessagePagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        ser = MessageSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(ser.data)    

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        convo = self.get_object()
        changed = convo.mark_as_read(request.user)

        if changed:
            layer = get_channel_layer()

            # existing chat read receipt
            async_to_sync(layer.group_send)(
                f"chat_{convo.pk}",
                {
                    "type": "read.receipt",
                    "conversation_id": convo.pk,
                    "reader_username": request.user.username,
                    "last_read_at": (
                        convo.buyer_last_read if request.user.id == convo.buyer_id
                        else convo.seller_last_read
                    ).isoformat(),
                },
            )

            for uid in (convo.buyer_id, convo.seller_id):
                async_to_sync(layer.group_send)(
                    f"inbox_user_{uid}",
                    {
                        "type": "inbox.conversation_upsert",
                        "conversation": ConversationSerializer(
                            convo, context={"for_user_id": uid}
                        ).data,
                    },
                )

        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def mute(self, request, pk=None):
        convo = self.get_object()
        value = str(request.data.get(
            "value", "true")).lower() in {"1", "true", "yes", "on"}
        convo.set_muted(request.user, value)
        return Response(
            {"ok": True, "is_muted_for_me": convo.is_muted_for(request.user)})



class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_permissions(self):
        if self.action in ("retrieve", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsParticipant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        return (
            Message.objects
            .filter(Q(conversation__buyer=user) | Q(conversation__seller=user))
            .select_related("sender", "conversation")
        )

    def perform_create(self, serializer):
        user = self.request.user
        convo = serializer.validated_data.get("conversation")
        if not convo or (convo.buyer_id != user.id and convo.seller_id != user.id):
            raise PermissionDenied("Not a participant.")

        # Optional: enforce blocks here (uncomment if you have UserBlock)
        # other = convo.seller if user.id == convo.buyer_id else convo.buyer
        # if UserBlock.objects.filter(
        #     Q(blocker=user, blocked=other) | Q(blocker=other, blocked=user)
        # ).exists():
        #     raise PermissionDenied("Messaging is blocked between these users.")

        body = (serializer.validated_data.get("body") or "").strip()
        image = serializer.validated_data.get("image")
        if not body and not image:
            raise ValidationError({"non_field_errors": ["Message must contain text or an image."]})

        # Save message with sender
        msg = serializer.save(sender=user)

        # Prepare serialized payloads
        # Use request context for Message so image_url is absolute for REST clients
        ser_msg = MessageSerializer(msg, context={"request": self.request}).data

        # For inbox WS, serialize conversation twice with per-user context
        ser_convo_buyer  = ConversationSerializer(convo, context={"for_user_id": convo.buyer_id}).data
        ser_convo_seller = ConversationSerializer(convo, context={"for_user_id": convo.seller_id}).data

        # Broadcast to chat group (open thread)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{convo.id}",
            {
                "type": "chat.message",     # -> ChatConsumer.chat_message
                "message": ser_msg,
                "sender": user.username,    # include for consumers that read event["sender"]
                "origin": "rest.perform_create",
            },
        )

        # Broadcast to each participant’s inbox group (list/badges/preview)
        for uid, payload in (
            (convo.buyer_id,  ser_convo_buyer),
            (convo.seller_id, ser_convo_seller),
        ):
            async_to_sync(channel_layer.group_send)(
                f"user_inbox_{uid}",
                {
                    "type": "inbox.upsert",       # -> InboxConsumer.inbox_upsert
                    "conversation": payload,
                },
            )
            async_to_sync(channel_layer.group_send)(
                f"user_inbox_{uid}",
                {
                    "type": "inbox.message_new",  # optional: separate event if you handle counts
                    "conversation": convo.id,
                    "message": ser_msg,
                },
            )


class UserBlockViewSet(viewsets.ModelViewSet):
    serializer_class = UserBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserBlock.objects.filter(blocker=self.request.user)

    @action(detail=False, methods=["get"], url_path="is-blocked/(?P<username>[^/]+)")
    def is_blocked(self, request, username=None):
        try:
            other = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"blocked": False})
        blocked = UserBlock.objects.filter(blocker=request.user, blocked=other).exists()
        return Response({"blocked": blocked})


class UserReportViewSet(viewsets.ModelViewSet):
    serializer_class = UserReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Reporter can see their own reports; staff see all
        qs = UserReport.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(reporter=self.request.user)
        return qs