from rest_framework import viewsets, permissions, filters
from .models import Order, Review
from vintageapi.models import Item
from .serializers import OrderSerializer, ReviewSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings

import stripe
from django.conf import settings


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Buyers see their orders, sellers see their sold orders
        user = self.request.user
        if self.request.query_params.get('as_seller'):
            return Order.objects.filter(order_items__item__seller=user).distinct()
        return Order.objects.filter(buyer=user)

    def perform_create(self, serializer):
        print("Current user in perform_create:", self.request.user)
        serializer.save(buyer=self.request.user)


    @action(detail=True, methods=['post'])
    def create_payment_intent(self, request, pk=None):
        order = self.get_object()
        if order.status != "pending":
            return Response({"error": "Order is not in pending status."}, status=400)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.PaymentIntent.create(
            amount=int(order.total_amount * 100),  # Stripe wants cents
            currency="eur",  # or your currency
            metadata={"order_id": order.id},
        )
        order.payment_reference = intent['id']
        order.save()
        return Response({"client_secret": intent['client_secret']})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle successful payment
    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        payment_reference = intent['id']
        try:
            order = Order.objects.get(payment_reference=payment_reference)
            order.status = 'paid'
            order.save()
        except Order.DoesNotExist:
            pass  # Log or handle this as needed

    # Add more event types as needed

    return HttpResponse(status=200)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]  # You can add more, like SearchFilter if you wish
    ordering_fields = ['created_at', 'rating']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by seller username if provided
        seller_username = self.request.query_params.get("seller__username")
        if seller_username:
            queryset = queryset.filter(seller__username=seller_username)
        # You can add more filters as needed
        return queryset

    def perform_create(self, serializer):
        order_id = self.request.data.get("order")
        item_id = self.request.data.get("item")
        # Get order/item instance (import your models)
        from .models import Order, Item  # adjust import if needed
        order = Order.objects.get(id=order_id)
        item = Item.objects.get(id=item_id)
        seller = item.seller
        serializer.save(
            buyer=self.request.user,
            order=order,
            item=item,
            seller=seller,
        )