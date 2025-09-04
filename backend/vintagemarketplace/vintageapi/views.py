from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from messaging.utils import _is_blocked
from messaging.models import UserBlock
from .models import Item, ItemImage
from .serializers import ItemSerializer, ItemImageSerializer
from .permissions import IsSellerOrReadOnly

from rest_framework import permissions


class IsSellerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.seller == request.user


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.filter(is_sold=False)
    serializer_class = ItemSerializer
    permission_classes = [IsSellerOrReadOnly]
    filtersets = [DjangoFilterBackend]
    filterset_fields = { 
        'price': ['gte', 'lte'],
        'title': ['icontains'],
    }
    search_fields = ['title', 'description']

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def perform_destroy(self, instance):
        if instance.seller != self.request.user:
            raise PermissionError(
                "Unauthorized deletion of id: %s" % str(instance.id))
        instance.delete()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            qs = qs.exclude(
                seller__in=UserBlock.objects.filter(blocker=user).values(
                    "blocked"))
            qs = qs.exclude(
                seller__in=UserBlock.objects.filter(blocked=user).values(
                    "blocker"))
        return qs


class ItemImageViewSet(viewsets.ModelViewSet):
    queryset = ItemImage.objects.all()
    serializer_class = ItemImageSerializer
    permission_classes = [IsAuthenticated]  # sellers only

    def perform_create(self, serializer):
        item_id = self.request.data.get('item')
        serializer.save(item_id=item_id)
