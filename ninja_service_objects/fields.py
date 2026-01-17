from typing import Any, Generic, TypeVar

from django.db import models
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

ModelT = TypeVar("ModelT", bound=models.Model)


def _resolve_model_class(
    model_class: type[models.Model] | None,
    source_type: Any,
    field_name: str,
    extract_from_list: bool = False,
) -> type[models.Model]:
    """Resolve and validate the model class from either explicit or source type."""
    resolved = model_class or source_type

    if resolved is None:
        raise TypeError(
            f"{field_name} requires a model class. "
            f"Use {field_name}[ModelClass] or Annotated[ModelClass, {field_name}()]"
        )

    # Handle generic types like list[User], Optional[User], etc.
    origin = getattr(resolved, "__origin__", None)
    if origin is not None:
        if extract_from_list and origin is list:
            # Extract the inner type from list[Model]
            args = getattr(resolved, "__args__", ())
            if args:
                resolved = args[0]
            else:
                raise TypeError(
                    f"{field_name} requires a typed list, e.g., list[ModelClass]"
                )
        else:
            raise TypeError(
                f"{field_name} does not support generic types like Optional or Union. "
                f"Got: {resolved}"
            )

    if not isinstance(resolved, type) or not issubclass(resolved, models.Model):
        raise TypeError(f"{field_name} requires a Django Model class, got: {resolved}")

    return resolved


def _validate_model_instance(
    value: Any,
    model_class: type[models.Model],
    allow_unsaved: bool = False,
) -> models.Model:
    """Validate that a value is an instance of the specified Django model."""
    if not isinstance(value, model_class):
        raise ValueError(
            f"Expected instance of {model_class.__name__}, got {type(value).__name__}"
        )

    if not allow_unsaved and value.pk is None:
        raise ValueError("Unsaved model instances are not allowed")

    return value


def _validate_model_iterable(
    value: Any,
    model_class: type[models.Model],
    allow_unsaved: bool = False,
) -> list[models.Model]:
    """Validate that a value is an iterable of Django model instances."""
    if isinstance(value, (str, bytes)):
        raise ValueError(
            f"Expected a list of {model_class.__name__} instances, "
            f"got {type(value).__name__}"
        )

    if not hasattr(value, "__iter__"):
        raise ValueError(
            f"Expected a list of {model_class.__name__} instances, "
            f"got {type(value).__name__}"
        )

    result = []
    for i, item in enumerate(value):
        try:
            validated = _validate_model_instance(item, model_class, allow_unsaved)
            result.append(validated)
        except ValueError as e:
            raise ValueError(f"Item {i}: {e}") from None

    return result


class ModelField(Generic[ModelT]):
    """
    A Pydantic-compatible field that validates Django model instances.

    Usage:
        class MyInput(BaseModel):
            user: ModelField[User]
            # or with options:
            user: Annotated[User, ModelField(allow_unsaved=True)]
    """

    def __init__(
        self,
        model_class: type[ModelT] | None = None,
        allow_unsaved: bool = False,
    ):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __class_getitem__(cls, model_class: type[ModelT]) -> Any:
        """Support ModelField[User] syntax."""
        return _ModelFieldAnnotation(model_class=model_class, allow_unsaved=False)

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        model_class = _resolve_model_class(self.model_class, source_type, "ModelField")
        allow_unsaved = self.allow_unsaved

        return core_schema.no_info_plain_validator_function(
            lambda v: _validate_model_instance(v, model_class, allow_unsaved),
        )


class _ModelFieldAnnotation:
    """Internal class to handle ModelField[Model] generic syntax."""

    def __init__(self, model_class: type[models.Model], allow_unsaved: bool = False):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        model_class = _resolve_model_class(self.model_class, source_type, "ModelField")
        allow_unsaved = self.allow_unsaved

        return core_schema.no_info_plain_validator_function(
            lambda v: _validate_model_instance(v, model_class, allow_unsaved),
        )


class MultipleModelField(Generic[ModelT]):
    """
    A Pydantic-compatible field that validates a list of Django model instances.

    Usage:
        class MyInput(BaseModel):
            users: MultipleModelField[User]
            # or with options:
            users: Annotated[list[User], MultipleModelField(allow_unsaved=True)]
    """

    def __init__(
        self,
        model_class: type[ModelT] | None = None,
        allow_unsaved: bool = False,
    ):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __class_getitem__(cls, model_class: type[ModelT]) -> Any:
        """Support MultipleModelField[User] syntax."""
        return _MultipleModelFieldAnnotation(
            model_class=model_class, allow_unsaved=False
        )

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        model_class = _resolve_model_class(
            self.model_class, source_type, "MultipleModelField", extract_from_list=True
        )
        allow_unsaved = self.allow_unsaved

        return core_schema.no_info_plain_validator_function(
            lambda v: _validate_model_iterable(v, model_class, allow_unsaved),
        )


class _MultipleModelFieldAnnotation:
    """Internal class to handle MultipleModelField[Model] generic syntax."""

    def __init__(self, model_class: type[models.Model], allow_unsaved: bool = False):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        model_class = _resolve_model_class(
            self.model_class, source_type, "MultipleModelField", extract_from_list=True
        )
        allow_unsaved = self.allow_unsaved

        return core_schema.no_info_plain_validator_function(
            lambda v: _validate_model_iterable(v, model_class, allow_unsaved),
        )
