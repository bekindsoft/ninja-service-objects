from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from ninja_service_objects import service, service_object


class CreateInput(BaseModel):
    name: str
    count: int = 1


class ActorInput(BaseModel):
    username: str


def test_service_object_validates_pydantic_annotations():
    @service_object(db_transaction=False)
    def build(data: CreateInput) -> CreateInput:
        return data

    result = build({"name": "widget"})

    assert isinstance(result, CreateInput)
    assert result.name == "widget"
    assert result.count == 1


def test_service_object_can_be_used_without_parentheses(monkeypatch):
    class Atomic:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        "ninja_service_objects.decorators.transaction.atomic",
        lambda using: Atomic(),
    )

    @service_object
    def build(data: CreateInput) -> str:
        return data.name

    assert build({"name": "widget"}) == "widget"


def test_service_object_rejects_invalid_schema_input():
    @service_object(db_transaction=False)
    def build(data: CreateInput) -> CreateInput:
        return data

    with pytest.raises(ValidationError):
        build({"name": "widget", "count": "invalid"})


def test_service_object_validates_multiple_schema_arguments():
    @service_object(db_transaction=False)
    def assign(actor: ActorInput, data: CreateInput) -> str:
        return f"{actor.username}:{data.name}:{data.count}"

    result = assign({"username": "admin"}, {"name": "widget", "count": 3})

    assert result == "admin:widget:3"


def test_service_object_accepts_existing_schema_instances():
    data = CreateInput(name="widget")

    @service_object(db_transaction=False)
    def build(data: CreateInput) -> CreateInput:
        return data

    assert build(data) is data


def test_service_object_supports_annotated_schema_arguments():
    @service_object(db_transaction=False)
    def build(data: Annotated[CreateInput, "metadata"]) -> CreateInput:
        return data

    result = build({"name": "widget"})

    assert isinstance(result, CreateInput)


def test_service_alias_uses_transaction_and_runs_post_process_on_commit(monkeypatch):
    callbacks = []
    atomic_usings = []
    processed = []

    class Atomic:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def atomic(using):
        atomic_usings.append(using)
        return Atomic()

    def on_commit(callback):
        callbacks.append(callback)

    monkeypatch.setattr("ninja_service_objects.decorators.transaction.atomic", atomic)
    monkeypatch.setattr(
        "ninja_service_objects.decorators.transaction.on_commit",
        on_commit,
    )

    @service(using="analytics", post_process=processed.append)
    def build(data: CreateInput) -> str:
        return data.name

    result = build({"name": "widget"})

    assert result == "widget"
    assert atomic_usings == ["analytics"]
    assert processed == []

    callbacks[0]()

    assert processed == ["widget"]


def test_service_object_without_transaction_runs_post_process_immediately(monkeypatch):
    processed = []

    def fail_atomic(using):
        raise AssertionError("transaction.atomic should not be called")

    monkeypatch.setattr(
        "ninja_service_objects.decorators.transaction.atomic",
        fail_atomic,
    )

    @service_object(db_transaction=False, post_process=processed.append)
    def build(data: CreateInput) -> str:
        return data.name

    result = build({"name": "widget"})

    assert result == "widget"
    assert processed == ["widget"]
