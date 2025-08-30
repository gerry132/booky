from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import generics
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer
from vintageapi.models import Item
from orders.models import Review
from orders.serializers import ReviewSerializer

from django.contrib.auth import get_user_model


User = get_user_model()


class UserProfileView(generics.RetrieveAPIView):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'


class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer

    def patch(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        profile = self.queryset.get(user=request.user)
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def reviews(self, request, pk=None):
        profile = self.get_object()
        seller = profile.user

        if request.method == 'GET':
            reviews = Review.objects.filter(seller=seller)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            if not request.user.is_authenticated:
                raise PermissionDenied("Login required to leave a review.")

            item_id = request.data.get('item_id')
            if not item_id:
                raise ValidationError("item_id is required.")

            try:
                item = Item.objects.get(pk=item_id, seller=seller)
            except Item.DoesNotExist:
                raise ValidationError("Item does not exist or does not belong to this seller.")

            # Check if the requesting user has completed an order for this item
            from orders.models import Order
            has_bought = Order.objects.filter(
                buyer=request.user,
                item=item,
                paid=True  # or whatever marks as completed
            ).exists()
            if not has_bought:
                raise PermissionDenied("You must have bought this item to review it.")

            # Prevent double-reviewing (handled by unique_together, but let's be explicit)
            if Review.objects.filter(reviewer=request.user, item=item).exists():
                raise ValidationError("You have already reviewed this item.")

            review = Review.objects.create(
                seller=seller,
                reviewer=request.user,
                item=item,
                rating=request.data.get('rating'),
                text=request.data.get('text', '')
            )
            serializer = ReviewSerializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
