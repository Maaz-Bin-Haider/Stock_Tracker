from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        PURCHASE = "PURCHASE", "Purchase User"
        SALE = "SALE", "Sale User"
        VIEWER = "VIEWER", "Viewer"

    class Theme(models.TextChoices):
        LIGHT = "LIGHT", "Light"
        DARK = "DARK", "Dark"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)
    # Empty = follow the system preference (FR-126); stored on the profile so
    # the choice follows the user across devices (TECHNICAL_ARCHITECTURE §9.1).
    theme = models.CharField(max_length=8, choices=Theme.choices, blank=True, default="")
