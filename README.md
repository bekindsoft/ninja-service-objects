# Django Ninja Service Objects

Service objects for Django Ninja using Pydantic validation. Encapsulate your business logic in reusable, testable service classes.

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
from pydantic import BaseModel
from ninja_service_objects import Service

class CreateUserInput(BaseModel):
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

## Features

- Pydantic validation for inputs
- Automatic database transaction handling
- `post_process` hook for side effects (runs after commit)
- Type-safe with generics support

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
