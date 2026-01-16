from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from django.db import transaction, DEFAULT_DB_ALIAS
from pydantic import BaseModel, ValidationError

# Define TypeVars for type-hinting the Schema and the Return type
SchemaT = TypeVar("SchemaT", bound=BaseModel)
ReturnT = TypeVar("ReturnT")

class BasePydanticService(ABC, Generic[SchemaT, ReturnT]):
    """
    An abstract base class for services using Pydantic for validation.
    Mirrors the lifecycle of django-service-objects.
    """
    schema: Type[SchemaT]
    db_transaction: bool = True
    using: str = DEFAULT_DB_ALIAS

    def __init__(self, validated_data: SchemaT, **kwargs: Any):
        self.cleaned_data = validated_data
        self.kwargs = kwargs

    @classmethod
    def execute(cls, inputs: Dict[str, Any], **kwargs: Any) -> ReturnT:
        """
        The entry point to the service. Validates inputs and executes logic
        within a transaction context.
        """
        try:
            # 1. Validation (replaces service_clean/is_valid)
            validated_data = cls.schema(**inputs)
        except ValidationError as e:
            # Map Pydantic errors to a format your API layer understands
            raise e

        # 2. Initialization
        instance = cls(validated_data, **kwargs)

        # 3. Execution with Transaction logic
        if cls.db_transaction:
            with transaction.atomic(using=cls.using):
                result = instance.process()
                # Use on_commit for side effects (emails, celery, etc.)
                transaction.on_commit(instance.post_process)
                return result
        else:
            result = instance.process()
            instance.post_process()
            return result

    @abstractmethod
    def process(self) -> ReturnT:
        """
        Override this method with your core business logic.
        """
        pass

    def post_process(self) -> None:
        """
        Override this for actions that should only run after success.
        """
        pass