"""Create (or promote) an Admin-role superuser.

`createsuperuser` leaves the custom ``role`` at its VIEWER default, which makes the
account read-only in the app and hides the admin navigation — permissions key off
``user.role``, not ``is_superuser`` (see accounts/permissions.py). This command
creates an ADMIN-role staff superuser so the offline/local production operator has
a working administrator on first setup.

Non-interactive (Docker / scripts):
    manage.py create_admin --username admin --email admin@example.com \
        --password '...'            # or set DJANGO_ADMIN_PASSWORD
Interactive:
    manage.py create_admin          # prompts for anything not supplied

Idempotent: if the username already exists it is promoted to ADMIN /
staff / superuser, and the password is updated only when one is supplied.
"""

import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Create or promote an Admin-role superuser for production setup."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("DJANGO_ADMIN_USERNAME"))
        parser.add_argument("--email", default=os.environ.get("DJANGO_ADMIN_EMAIL", ""))
        parser.add_argument("--password", default=os.environ.get("DJANGO_ADMIN_PASSWORD"))

    def handle(self, *args, **options):
        username = options["username"] or input("Username: ").strip()
        if not username:
            raise CommandError("A username is required.")

        email = options["email"]
        password = options["password"]

        existing = User.objects.filter(username=username).first()

        if password is None and not existing:
            # New account needs a password; confirm it when we have a terminal.
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Password (again): ")
            if password != confirm:
                raise CommandError("Passwords did not match.")

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise CommandError("Password rejected: " + "; ".join(exc.messages)) from exc

        if existing:
            existing.role = User.Role.ADMIN
            existing.is_staff = True
            existing.is_superuser = True
            if email:
                existing.email = email
            if password:
                existing.set_password(password)
            existing.save()
            self.stdout.write(
                self.style.SUCCESS(f"Promoted existing user '{username}' to Admin superuser.")
            )
            return

        user = User.objects.create_superuser(username=username, email=email, password=password)
        user.role = User.Role.ADMIN
        user.save(update_fields=["role"])
        self.stdout.write(self.style.SUCCESS(f"Created Admin superuser '{username}'."))
