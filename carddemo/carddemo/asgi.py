"""ASGI config for the CardDemo project."""
from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carddemo.settings.development")

application = get_asgi_application()
