"""WSGI config for the CardDemo project."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carddemo.settings.production")

application = get_wsgi_application()
