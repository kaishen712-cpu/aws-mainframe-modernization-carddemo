"""WSGI config for CardDemo project."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "python.carddemo.settings")

application = get_wsgi_application()
