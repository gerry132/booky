from rest_framework import viewsets, permissions, parsers
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from vintageapi.models import Item
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(Q(buyer=user) | Q(seller=user))

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        convo = self.get_object()
        messages = convo.messages.order_by('created_at')
        return Response(MessageSerializer(messages, many=True).data)

    def perform_create(self, serializer):
        item_id = self.request.data.get('item')
        item = Item.objects.get(pk=item_id)
        serializer.save(
            buyer=self.request.user,
            seller=item.seller,
            item=item
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        convo = self.get_object()
        user = request.user
        if convo.mark_as_read(user):
            return Response({
                "status": "ok", "unread": convo.unread_count_for(user)})
        else:
            return Response({"error": "Not a participant"}, status=403)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser,
                      parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(conversation__buyer=user) |
            Q(conversation__seller=user))

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
