from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from messaging.utils import _is_blocked
from messaging.models import UserBlock
from .models import Item, ItemImage, WishlistItem, Wishlist
from .serializers import (ItemSerializer, ItemImageSerializer,
                          WishlistItemSerializer, WishlistSerializer)
from rest_framework.response import Response
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


class WishlistViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _wishlist(self, request):
        wl, _ = Wishlist.objects.get_or_create(user=request.user)
        # prefetch for speed
        return Wishlist.objects.prefetch_related(
            "items__product"
        ).get(pk=wl.pk)

    def list(self, request):
        wl = self._wishlist(request)
        return Response(WishlistSerializer(wl).data)

    @action(methods=["post"], detail=False)
    def add(self, request):
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, pk=product_id)
        wl = self._wishlist(request)
        item, created = WishlistItem.objects.get_or_create(wishlist=wl, product=product)
        if not created:
            # optional: bump quantity
            item.quantity = max(1, item.quantity)
            item.save(update_fields=["quantity"])
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED if created else 200)

    @action(methods=["post"], detail=False)
    def remove(self, request):
        product_id = request.data.get("product_id")
        wl = self._wishlist(request)
        WishlistItem.objects.filter(wishlist=wl, product_id=product_id).delete()
        return Response(status=204)

    @action(methods=["post"], detail=False)
    def toggle(self, request):
        product_id = request.data.get("product_id")
        product = get_object_or_404(Item, pk=product_id)
        wl = self._wishlist(request)
        qs = WishlistItem.objects.filter(wishlist=wl, product=product)
        if qs.exists():
            qs.delete()
            return Response({"status": "removed"})
        item = WishlistItem.objects.create(wishlist=wl, product=product)
        return Response(
            {"status": "added", "item": WishlistItemSerializer(item).data},
            status=201)

    @action(methods=["patch"], detail=False)
    def update_item(self, request):
        item_id = request.data.get("id")
        wl = self._wishlist(request)
        item = get_object_or_404(WishlistItem, pk=item_id, wishlist=wl)
        serializer = WishlistItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
