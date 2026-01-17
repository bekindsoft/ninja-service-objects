# Django Ninja Service Objects

An implementation of the [django-service-objects](https://django-service-objects.readthedocs.io/en/latest/pages/philosophy.html) philosophy for Django Ninja with Pydantic validation.

Encapsulate your business logic in reusable, testable service classes.

## Installation

```bash
pip install django-ninja-service-objects
```

Add to your Django settings:

```python
# settings.py
INSTALLED_APPS = [
    ...
    'ninja_service_objects',
    ...
]
```

## Usage

```python
from ninja import Schema
from ninja_service_objects import Service

class CreateUserInput(Schema):
    email: str
    name: str

class CreateUserService(Service[CreateUserInput, User]):
    schema = CreateUserInput

    def process(self) -> User:
        return User.objects.create(
            email=self.cleaned_data.email,
            name=self.cleaned_data.name,
        )

    def post_process(self) -> None:
        # Called after successful transaction commit
        send_welcome_email(self.cleaned_data.email)

# In your view
user = CreateUserService.execute({"email": "test@example.com", "name": "Test"})
```

### Using Pydantic BaseModel with Custom Validators

You can also use Pydantic's BaseModel directly for more complex validation:

```python
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from ninja_service_objects import Service

class RegisterUserInput(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterUserInput":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self

class RegisterUserService(Service[RegisterUserInput, User]):
    schema = RegisterUserInput

    def process(self) -> User:
        return User.objects.create_user(
            email=self.cleaned_data.email,
            password=self.cleaned_data.password,
        )
```

### Using ModelField for Django Model Instances

Use `ModelField` and `MultipleModelField` to validate Django model instances as service inputs:

```python
from pydantic import BaseModel
from ninja_service_objects import Service, ModelField, MultipleModelField

class TransferOwnershipInput(BaseModel):
    from_user: ModelField[User]
    to_user: ModelField[User]
    posts: MultipleModelField[Post]

class TransferOwnershipService(Service[TransferOwnershipInput, None]):
    schema = TransferOwnershipInput

    def process(self) -> None:
        for post in self.cleaned_data.posts:
            post.author = self.cleaned_data.to_user
            post.save()
```

By default, `ModelField` rejects unsaved model instances (objects without a primary key). To allow unsaved instances:

```python
from typing import Annotated

class MyInput(BaseModel):
    user: Annotated[User, ModelField(allow_unsaved=True)]
    items: Annotated[list[Item], MultipleModelField(allow_unsaved=True)]
```

## Features

- Pydantic validation for inputs
- Automatic database transaction handling
- `post_process` hook for side effects (runs after commit)
- Type-safe with generics support
- `ModelField` and `MultipleModelField` for Django model instance validation

## Design Decisions

### Why Pydantic instead of Django Forms?

The original django-service-objects uses Django Forms for validation. Since Django Ninja already uses Pydantic for request/response schemas, this library uses Pydantic to:

- Avoid mixing two validation systems in the same project
- Reuse your existing Django Ninja schemas as service inputs
- Get better type hints and IDE support

### API Compatibility

We maintain familiar patterns from django-service-objects:

- `cleaned_data` - Access validated input data (same naming as Django forms/original library)
- `process()` - Override this with your business logic
- `post_process()` - Runs after successful transaction commit (for emails, notifications, etc.)
- `execute()` - Class method entry point that handles validation and transactions

### What's Different

| django-service-objects | ninja-service-objects |
|------------------------|----------------------|
| Django Forms validation | Pydantic validation |
| `service_clean()` method | Pydantic validators |
| Form fields | Pydantic BaseModel |
| `is_valid()` + `execute()` | Single `execute()` call |

## Configuration

### Transaction Control

```python
class MyService(Service[MyInput, MyOutput]):
    schema = MyInput
    db_transaction = False  # Disable automatic transaction wrapping
    using = "other_db"      # Use a different database alias
```

## License

MIT
