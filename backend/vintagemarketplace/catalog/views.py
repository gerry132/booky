from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
# from django.db.models import Q
from .models import Category, Brand, Tag, Attribute, CategoryAttribute
from .serializers import (
    CategorySerializer, BrandSerializer, TagSerializer,
    AttributeSerializer
)

class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.select_related("parent").order_by("parent__id", "name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["get"], url_path="attributes")
    def attributes(self, request, pk=None):
        """Return Attribute[] for this category (via CategoryAttribute)."""
        attr_ids = CategoryAttribute.objects.filter(category_id=pk).values_list("attribute_id", flat=True)
        attrs = Attribute.objects.filter(id__in=attr_ids).prefetch_related("options").order_by("name")
        return Response(AttributeSerializer(attrs, many=True).data)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by("name")
    serializer_class = BrandSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "slug", "synonyms"]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "slug"]
