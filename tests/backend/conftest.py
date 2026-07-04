import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

PASSWORD = "pass12345"


@pytest.fixture
def make_user(db):
    def _make(role, username=None, **kwargs):
        username = username or f"{role.lower()}_user"
        return User.objects.create_user(
            username=username, password=PASSWORD, role=role, **kwargs
        )

    return _make


@pytest.fixture
def auth_client(make_user):
    """APIClient logged in through a real session, so audit rows attribute
    to the user exactly as they do in production."""

    def _client(role):
        user = make_user(role)
        client = APIClient()
        assert client.login(username=user.username, password=PASSWORD)
        client.user = user
        return client

    return _client


@pytest.fixture
def admin_client(auth_client):
    return auth_client(User.Role.ADMIN)
