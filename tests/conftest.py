import pytest


@pytest.fixture
def user_model():
    """Provide the Django User model."""
    from django.contrib.auth.models import User

    return User
