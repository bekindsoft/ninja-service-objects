import pytest
from django.contrib.auth.models import User
from pydantic import BaseModel, ValidationError

from ninja_service_objects import ModelField, MultipleModelField


class SingleModelInput(BaseModel):
    user: ModelField[User]


class MultipleModelInput(BaseModel):
    users: MultipleModelField[User]


class TestModelField:
    """Tests for ModelField validation."""

    @pytest.mark.django_db
    def test_valid_saved_model_instance(self):
        """ModelField accepts saved model instances."""
        user = User.objects.create_user(username="testuser", password="testpass")

        result = SingleModelInput(user=user)

        assert result.user == user
        assert result.user.pk is not None

    def test_rejects_unsaved_model_by_default(self):
        """ModelField rejects unsaved instances by default."""
        user = User(username="unsaved")

        with pytest.raises(ValidationError) as exc_info:
            SingleModelInput(user=user)

        assert "Unsaved model instances are not allowed" in str(exc_info.value)

    def test_rejects_wrong_model_type(self):
        """ModelField rejects instances of wrong model type."""
        with pytest.raises(ValidationError) as exc_info:
            SingleModelInput(user="not a model")

        assert "Expected instance of User" in str(exc_info.value)

    def test_rejects_none(self):
        """ModelField rejects None values."""
        with pytest.raises(ValidationError):
            SingleModelInput(user=None)

    def test_allow_unsaved_option(self):
        """ModelField with allow_unsaved=True accepts unsaved instances."""
        from typing import Annotated

        class AllowUnsavedInput(BaseModel):
            user: Annotated[User, ModelField(allow_unsaved=True)]

        user = User(username="unsaved")

        result = AllowUnsavedInput(user=user)

        assert result.user == user
        assert result.user.pk is None


class TestMultipleModelField:
    """Tests for MultipleModelField validation."""

    @pytest.mark.django_db
    def test_valid_list_of_saved_models(self):
        """MultipleModelField accepts list of saved model instances."""
        user1 = User.objects.create_user(username="user1", password="pass1")
        user2 = User.objects.create_user(username="user2", password="pass2")

        result = MultipleModelInput(users=[user1, user2])

        assert len(result.users) == 2
        assert result.users[0] == user1
        assert result.users[1] == user2

    def test_accepts_empty_list(self):
        """MultipleModelField accepts empty list."""
        result = MultipleModelInput(users=[])

        assert result.users == []

    @pytest.mark.django_db
    def test_rejects_unsaved_model_in_list(self):
        """MultipleModelField rejects unsaved instances in list."""
        saved_user = User.objects.create_user(username="saved", password="pass")
        unsaved_user = User(username="unsaved")

        with pytest.raises(ValidationError) as exc_info:
            MultipleModelInput(users=[saved_user, unsaved_user])

        assert "Item 1" in str(exc_info.value)
        assert "Unsaved model instances are not allowed" in str(exc_info.value)

    def test_rejects_string_input(self):
        """MultipleModelField rejects string (which is technically iterable)."""
        with pytest.raises(ValidationError) as exc_info:
            MultipleModelInput(users="not a list")

        assert "Expected a list of User instances" in str(exc_info.value)

    def test_rejects_non_iterable(self):
        """MultipleModelField rejects non-iterable values."""
        with pytest.raises(ValidationError) as exc_info:
            MultipleModelInput(users=123)

        assert "Expected a list of User instances" in str(exc_info.value)

    @pytest.mark.django_db
    def test_rejects_wrong_model_type_in_list(self):
        """MultipleModelField rejects wrong model types in list."""
        user = User.objects.create_user(username="user1", password="pass")

        with pytest.raises(ValidationError) as exc_info:
            MultipleModelInput(users=[user, "not a model"])

        assert "Item 1" in str(exc_info.value)
        assert "Expected instance of User" in str(exc_info.value)

    def test_allow_unsaved_option(self):
        """MultipleModelField with allow_unsaved=True accepts unsaved instances."""
        from typing import Annotated

        class AllowUnsavedInput(BaseModel):
            users: Annotated[list[User], MultipleModelField(allow_unsaved=True)]

        user1 = User(username="unsaved1")
        user2 = User(username="unsaved2")

        result = AllowUnsavedInput(users=[user1, user2])

        assert len(result.users) == 2
        assert all(u.pk is None for u in result.users)
