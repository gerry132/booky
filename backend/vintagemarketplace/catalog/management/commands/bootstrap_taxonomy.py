# -*- coding: utf-8 -*-
"""
Seed a common taxonomy for a vintage marketplace:
- Categories (with hierarchy)
- Attributes + options (enum/text)
- CategoryAttribute links (with optional position)
- Brands (+ synonyms)
- Tags

Idempotent: safe to re-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

Category = apps.get_model("catalog", "Category")
Brand = apps.get_model("catalog", "Brand")
Tag = apps.get_model("catalog", "Tag")
Attribute = apps.get_model("catalog", "Attribute")
AttributeOption = apps.get_model("catalog", "AttributeOption")
CategoryAttribute = apps.get_model("catalog", "CategoryAttribute")


def _has_field(model, field_name: str) -> bool:
    return field_name in {f.name for f in model._meta.get_fields()}


# ------------- CONFIGURABLE SEED DATA -----------------

CATEGORY_PATHS = [
    "Clothing/Tops/T-Shirts",
    "Clothing/Tops/Shirts",
    "Clothing/Tops/Sweaters",
    "Clothing/Outerwear/Jackets",
    "Clothing/Outerwear/Coats",
    "Clothing/Bottoms/Jeans",
    "Clothing/Bottoms/Trousers",
    "Clothing/Bottoms/Shorts",
    "Clothing/Bottoms/Skirts",
    "Clothing/Dresses",
    "Footwear/Sneakers",
    "Footwear/Boots",
    "Accessories/Bags",
    "Accessories/Belts",
    "Accessories/Hats",
    "Accessories/Sunglasses",
    "Accessories/Jewellery",
    "Sportswear",
]

# Global attributes (some enum, some text). You can add/remove as needed.
ATTRIBUTES = [
    # (name, slug, input_type, options or None)
    ("Size", "size_alpha", "enum", ["XXS", "XS", "S", "M", "L", "XL", "XXL"]),
    ("Waist (inches)", "waist_inches", "enum", [str(x) for x in range(24, 45, 2)]),
    ("Chest (inches)", "chest_inches", "enum", [str(x) for x in range(32, 49, 2)]),
    ("Inseam (inches)", "inseam_inches", "enum", [str(x) for x in range(26, 37, 2)]),
    ("Length (cm)", "length_cm", "text", None),  # free text/number
    ("Colour", "colour", "enum",
     ["Black", "White", "Navy", "Blue", "Red", "Green", "Brown", "Beige", "Grey",
      "Pink", "Purple", "Yellow", "Orange", "Cream", "Burgundy"]),
    ("Material", "material", "enum",
     ["Cotton", "Wool", "Denim", "Leather", "Linen", "Silk",
      "Polyester", "Acrylic", "Nylon", "Down"]),
    ("Era", "era", "enum",
     ["1950s", "1960s", "1970s", "1980s", "1990s", "Y2K", "2010s"]),
    ("Pattern", "pattern", "enum", ["Solid", "Striped", "Checked", "Floral", "Graphic"]),
    ("Fit", "fit", "enum", ["Slim", "Regular", "Relaxed", "Oversized", "High-waisted"]),
    ("Condition", "condition", "enum",
     ["New with tags", "Excellent", "Very good", "Good", "Fair"]),
    ("Notes", "notes", "text", None),
]

# Map category path → which attributes to show (and in what order)
# (Use the attribute slug from ATTRIBUTES)
CATEGORY_ATTR_MAP = {
    "Clothing/Tops/T-Shirts":       ["size_alpha", "colour", "material", "era", "condition", "pattern", "notes"],
    "Clothing/Tops/Shirts":         ["size_alpha", "chest_inches", "colour", "material", "era", "condition", "pattern", "notes"],
    "Clothing/Tops/Sweaters":       ["size_alpha", "chest_inches", "material", "colour", "era", "condition", "pattern", "notes"],
    "Clothing/Outerwear/Jackets":   ["size_alpha", "chest_inches", "material", "colour", "era", "condition", "fit", "notes"],
    "Clothing/Outerwear/Coats":     ["size_alpha", "chest_inches", "material", "colour", "era", "condition", "fit", "notes"],
    "Clothing/Bottoms/Jeans":       ["waist_inches", "inseam_inches", "fit", "material", "colour", "era", "condition", "notes"],
    "Clothing/Bottoms/Trousers":    ["waist_inches", "inseam_inches", "fit", "material", "colour", "era", "condition", "notes"],
    "Clothing/Bottoms/Shorts":      ["waist_inches", "fit", "material", "colour", "era", "condition", "notes"],
    "Clothing/Bottoms/Skirts":      ["size_alpha", "length_cm", "material", "colour", "era", "condition", "notes"],
    "Clothing/Dresses":             ["size_alpha", "length_cm", "material", "colour", "era", "condition", "notes"],
    "Footwear/Sneakers":            ["size_alpha", "colour", "material", "era", "condition", "notes"],
    "Footwear/Boots":               ["size_alpha", "colour", "material", "era", "condition", "notes"],
    "Accessories/Bags":             ["material", "colour", "era", "condition", "notes"],
    "Accessories/Belts":            ["waist_inches", "material", "colour", "era", "condition", "notes"],
    "Accessories/Hats":             ["size_alpha", "material", "colour", "era", "condition", "notes"],
    "Accessories/Sunglasses":       ["colour", "era", "condition", "notes"],
    "Accessories/Jewellery":        ["material", "era", "condition", "notes"],
    "Sportswear":                   ["size_alpha", "material", "colour", "era", "condition", "notes"],
}

# Brands (with synonyms)
BRANDS = [
    ("Levi's", ["Levis", "Levi Strauss", "Levi Strauss & Co"]),
    ("Nike", ["NKE"]),
    ("Adidas", ["adidas Originals"]),
    ("Carhartt", ["Carhartt WIP"]),
    ("Patagonia", []),
    ("The North Face", ["TNF"]),
    ("Dr. Martens", ["Docs", "Doc Martens"]),
    ("Ralph Lauren", ["Polo Ralph Lauren"]),
    ("Tommy Hilfiger", ["Tommy Jeans"]),
]

# Tags
TAGS = [
    "Vintage", "Deadstock", "Made in USA", "Workwear", "Streetwear",
    "Y2K", "90s", "80s", "Heritage", "Minimalist", "Festival",
]


def ensure_category(path: str) -> Category:
    """
    Ensure a slash-delimited path of categories exists.
    Returns the leaf Category.
    """
    parent = None
    for part in path.split("/"):
        obj, _ = Category.objects.get_or_create(parent=parent, name=part)
        parent = obj
    return parent


def ensure_attribute(name: str, slug: str, input_type: str, options: list | None):
    """
    Create or update an Attribute and its options (for enum types).
    Returns (attribute, created, options_created_count)
    """
    attr, created = Attribute.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "input_type": input_type},
    )
    # keep name / input_type in sync if changed
    changed = False
    if attr.name != name:
        attr.name = name
        changed = True
    if attr.input_type != input_type:
        attr.input_type = input_type
        changed = True
    if changed:
        attr.save()

    created_opts = 0
    if input_type == "enum":
        options = options or []
        has_sort = _has_field(AttributeOption, "sort_key")
        for idx, val in enumerate(options):
            opt, opt_created = AttributeOption.objects.get_or_create(
                attribute=attr, value=val
            )
            if has_sort and (getattr(opt, "sort_key", None) != idx):
                setattr(opt, "sort_key", idx)
                opt.save(update_fields=["sort_key"])
            if opt_created:
                created_opts += 1
    return attr, created, created_opts


def link_category_attribute(category: Category, attribute: Attribute, position: int):
    """
    Ensure CategoryAttribute exists. If the join model has a 'position' field,
    we keep it in sync with the given position.
    """
    ca, _ = CategoryAttribute.objects.get_or_create(
        category=category, attribute=attribute
    )
    if _has_field(CategoryAttribute, "position"):
        if getattr(ca, "position", None) != position:
            ca.position = position
            ca.save(update_fields=["position"])


class Command(BaseCommand):
    help = "Bootstrap a vintage marketplace taxonomy (categories, attributes, brands, tags)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-options",
            action="store_true",
            help="For enum attributes, remove options not in the seed list.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        self.stdout.write(self.style.MIGRATE_HEADING("Bootstrapping taxonomy…"))

        # 1) Categories
        created_cat = 0
        path_to_obj = {}
        for path in CATEGORY_PATHS:
            cat = ensure_category(path)
            path_to_obj[path] = cat
            # crude created detection: first creation returns id immediately; get_or_create hides it.
            # We'll just count distinct new slugs by ensuring parent/name pair exists anyway.
        self.stdout.write(self.style.SUCCESS(f"✓ Categories ensured: {len(CATEGORY_PATHS)} paths"))

        # 2) Attributes + options
        slug_to_attr = {}
        total_opt_created = 0
        for (name, slug, input_type, options) in ATTRIBUTES:
            attr, created, opt_created = ensure_attribute(name, slug, input_type, options)
            slug_to_attr[slug] = attr
            total_opt_created += opt_created

            if opts["reset_options"] and input_type == "enum":
                # remove enum options not present in seed (idempotent pruning)
                keep = set(options or [])
                qs = AttributeOption.objects.filter(attribute=attr)
                removed = 0
                for opt in qs:
                    if opt.value not in keep:
                        opt.delete()
                        removed += 1
                if removed:
                    self.stdout.write(f"  - pruned {removed} options from '{name}'")

        self.stdout.write(self.style.SUCCESS(
            f"✓ Attributes ensured: {len(ATTRIBUTES)} (new options created: {total_opt_created})"
        ))

        # 3) Category ↔ Attribute links
        for path, attr_slugs in CATEGORY_ATTR_MAP.items():
            cat = path_to_obj[path]
            for pos, slug in enumerate(attr_slugs):
                attr = slug_to_attr[slug]
                link_category_attribute(cat, attr, pos)
        self.stdout.write(self.style.SUCCESS("✓ Category ↔ Attribute links ensured"))

        # 4) Brands
        for name, syns in BRANDS:
            b, _ = Brand.objects.get_or_create(name=name, defaults={"synonyms": syns})
            # keep synonyms up to date if changed
            if syns and (b.synonyms != syns):
                b.synonyms = syns
                b.save(update_fields=["synonyms"])
        self.stdout.write(self.style.SUCCESS(f"✓ Brands ensured: {len(BRANDS)}"))

        # 5) Tags
        for t in TAGS:
            Tag.objects.get_or_create(name=t)
        self.stdout.write(self.style.SUCCESS(f"✓ Tags ensured: {len(TAGS)}"))

        self.stdout.write(self.style.SUCCESS("Done."))

