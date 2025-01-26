"""
WSGI config for image_processor project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_processor.settings')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

logger.info(f"Using database: {os.getenv('DATABASE_URL')}")
logger.info(f"Environment: {os.getenv('ENV')}")

application = get_wsgi_application()
