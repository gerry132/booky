from django.db import models
from django.utils.text import slugify


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStamped):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children",
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("parent", "name")
        ordering = ["parent__id", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            self.slug = base
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent} > {self.name}" if self.parent else self.name


class Brand(TimeStamped):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    synonyms = models.JSONField(default=list, blank=True)  # ["Levis","Levi's"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(TimeStamped):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Attribute(models.Model):
    INPUT_CHOICES = [
        ("enum","enum"),
        ("text","text"),
        ("number","number"),
    ]

    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True, blank=True)
    input_type = models.CharField(max_length=12, choices=INPUT_CHOICES, default="enum")
    unit = models.CharField(max_length=8, blank=True, default="")     # e.g. "in", "cm"
    min_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    step = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def save(self, *a, **k):
        if not self.slug: 
            self.slug = slugify(self.name)
        return super().save(*a, **k)

    def __str__(self):
        return self.name


class AttributeOption(models.Model):
    attribute = models.ForeignKey(Attribute, related_name="options", on_delete=models.CASCADE)
    value = models.CharField(max_length=40)
    sort_key = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("attribute", "value")
        ordering = ["sort_key", "value"]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class CategoryAttribute(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("category","attribute")
