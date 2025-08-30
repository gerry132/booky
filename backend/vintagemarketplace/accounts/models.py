from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from vintageapi.serializers import ItemSerializer


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=50)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        items = user.items.all()
        # Optionally split here, or do it in frontend
        return Response({
            "username": user.username,
            "date_joined": user.date_joined,
            "items_for_sale": ItemSerializer(items.filter(is_sold=False), many=True).data,
            "items_sold": ItemSerializer(items.filter(is_sold=True), many=True).data,
        })


    def __str__(self):
        return self.display_name or self.user.username
