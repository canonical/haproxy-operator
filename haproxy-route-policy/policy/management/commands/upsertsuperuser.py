# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Update or create a superuser"

    def handle(self, *args, **options):
        try:
            username = os.environ["DJANGO_SUPERUSER_USERNAME"]
        except KeyError:
            raise CommandError("environment variable DJANGO_SUPERUSER_USERNAME not set")
        try:
            password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
        except KeyError:
            raise CommandError("environment variable DJANGO_SUPERUSER_PASSWORD not set")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        user, created = User.objects.get_or_create(username=username)
        if created or not user.check_password(password):
            user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.email = email
        user.save()
        self.stdout.write(
            self.style.SUCCESS(f"successfully updated/created user {username}")
        )
