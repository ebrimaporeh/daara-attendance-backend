import os
from django.core.asgi import get_asgi_application

# Set environment for ASGI
os.environ.setdefault('DJANGO_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anamuslimah_project.settings')

application = get_asgi_application()