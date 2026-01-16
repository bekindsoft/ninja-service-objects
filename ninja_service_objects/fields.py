from typing import Any, Generic, List, Optional, Type, TypeVar, Union

from django.db import models
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

ModelT = TypeVar("ModelT", bound=models.Model)


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
        model_class: Optional[Type[ModelT]] = None,
        allow_unsaved: bool = False,
    ):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def _validate(self, value: Any, model_class: Type[ModelT]) -> ModelT:
        if not isinstance(value, model_class):
            raise ValueError(
                f"Expected instance of {model_class.__name__}, got {type(value).__name__}"
            )

        if not self.allow_unsaved and value.pk is None:
            raise ValueError("Unsaved model instances are not allowed")

        return value

    def __class_getitem__(cls, model_class: Type[ModelT]) -> Any:
        """Support ModelField[User] syntax."""
        return _ModelFieldAnnotation(model_class=model_class, allow_unsaved=False)

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            lambda v: self._validate(v, self.model_class or source_type),
        )


class _ModelFieldAnnotation:
    """Internal class to handle ModelField[Model] generic syntax."""

    def __init__(self, model_class: Type[models.Model], allow_unsaved: bool = False):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate(value: Any) -> models.Model:
            if not isinstance(value, self.model_class):
                raise ValueError(
                    f"Expected instance of {self.model_class.__name__}, "
                    f"got {type(value).__name__}"
                )
            if not self.allow_unsaved and value.pk is None:
                raise ValueError("Unsaved model instances are not allowed")
            return value

        return core_schema.no_info_plain_validator_function(validate)


class MultipleModelField(Generic[ModelT]):
    """
    A Pydantic-compatible field that validates a list of Django model instances.

    Usage:
        class MyInput(BaseModel):
            users: MultipleModelField[User]
            # or with options:
            users: Annotated[List[User], MultipleModelField(allow_unsaved=True)]
    """

    def __init__(
        self,
        model_class: Optional[Type[ModelT]] = None,
        allow_unsaved: bool = False,
    ):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def _validate(self, value: Any, model_class: Type[ModelT]) -> List[ModelT]:
        if not hasattr(value, "__iter__"):
            raise ValueError("Expected an iterable of model instances")

        result = []
        for i, item in enumerate(value):
            if not isinstance(item, model_class):
                raise ValueError(
                    f"Item {i}: Expected instance of {model_class.__name__}, "
                    f"got {type(item).__name__}"
                )
            if not self.allow_unsaved and item.pk is None:
                raise ValueError(f"Item {i}: Unsaved model instances are not allowed")
            result.append(item)

        return result

    def __class_getitem__(cls, model_class: Type[ModelT]) -> Any:
        """Support MultipleModelField[User] syntax."""
        return _MultipleModelFieldAnnotation(model_class=model_class, allow_unsaved=False)

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_plain_validator_function(
            lambda v: self._validate(v, self.model_class or source_type),
        )


class _MultipleModelFieldAnnotation:
    """Internal class to handle MultipleModelField[Model] generic syntax."""

    def __init__(self, model_class: Type[models.Model], allow_unsaved: bool = False):
        self.model_class = model_class
        self.allow_unsaved = allow_unsaved

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate(value: Any) -> List[models.Model]:
            if not hasattr(value, "__iter__"):
                raise ValueError("Expected an iterable of model instances")

            result = []
            for i, item in enumerate(value):
                if not isinstance(item, self.model_class):
                    raise ValueError(
                        f"Item {i}: Expected instance of {self.model_class.__name__}, "
                        f"got {type(item).__name__}"
                    )
                if not self.allow_unsaved and item.pk is None:
                    raise ValueError(
                        f"Item {i}: Unsaved model instances are not allowed"
                    )
                result.append(item)

            return result

        return core_schema.no_info_plain_validator_function(validate)
