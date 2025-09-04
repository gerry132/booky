# vintagemarketplace/vintagemarketplace/settings_test.py
from .settings import *  # noqa

DEBUG = False

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Local file storage to a temp-ish folder (pytest will override MEDIA_ROOT to a tmp dir via conftest)
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Test database (file-based sqlite for better migration compatibility)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}

# Local-memory cache (fast + isolated)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
    }
}

# Make sure REST pagination defaults are deterministic (tweak to match your API)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# If channels is installed, use in-memory layer in tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
