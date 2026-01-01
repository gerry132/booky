from django.contrib import admin
from .models import (Category,
                     Brand, Tag, Attribute, AttributeOption, CategoryAttribute)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class BrandAdmin(admin.ModelAdmin):
    search_fields = ("name", "synonyms")
    prepopulated_fields = {"slug": ("name",)}


class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Attribute)
admin.site.register(AttributeOption)
admin.site.register(CategoryAttribute)
