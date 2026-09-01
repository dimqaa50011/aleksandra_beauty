import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import jwt

class Command(BaseCommand):
    def handle(self, *args, **options):
        wp = random.choice(settings.WEB_PASSWORDS)
        token = jwt.encode({"user": wp, "id": 22, "st": "AS"}, settings.ADMIN_API_SECRET,  algorithm="HS256")
        self.stdout.write(token)