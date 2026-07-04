from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        PURCHASE = "PURCHASE", "Purchase User"
        SALE = "SALE", "Sale User"
        VIEWER = "VIEWER", "Viewer"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)
