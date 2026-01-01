from backend.vintagemarketplace.catalog.models import Category, Attribute, AttributeOption, CategoryAttribute


root = Category.objects.create(name="Clothing")                  # slug auto
men  = Category.objects.create(name="Men", parent=root)
women= Category.objects.create(name="Women", parent=root)
jeans= Category.objects.create(name="Jeans", parent=men)

# attributes
waist   = Attribute.objects.create(name="Waist size", slug="waist", input_type="number")
length  = Attribute.objects.create(name="Inseam length", slug="inseam", input_type="number")
fit     = Attribute.objects.create(name="Fit", slug="fit", input_type="enum")
cond    = Attribute.objects.create(name="Condition", slug="condition", input_type="enum")

# options for enum attributes
for v in ["Skinny","Slim","Straight","Relaxed","Wide"]:
    AttributeOption.objects.create(attribute=fit, value=v)
for v in ["New with tags","Excellent","Good","Fair"]:
    AttributeOption.objects.create(attribute=cond, value=v)

# link attributes to categories
CategoryAttribute.objects.create(category=men,   attribute=cond)  # applies to all men’s clothing (if you inherit)
CategoryAttribute.objects.create(category=jeans, attribute=waist)
CategoryAttribute.objects.create(category=jeans, attribute=length)
CategoryAttribute.objects.create(category=jeans, attribute=fit)
