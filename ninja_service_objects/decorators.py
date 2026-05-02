from collections.abc import Callable
from functools import wraps
from inspect import BoundArguments, Parameter, Signature, signature
from types import UnionType
from typing import Annotated, Any, TypeVar, Union, cast, get_args, get_origin, overload

from django.db import DEFAULT_DB_ALIAS, transaction  # type: ignore[import-untyped]
from pydantic import BaseModel

FuncT = TypeVar("FuncT", bound=Callable[..., Any])
PostProcess = Callable[[Any], None]

_NONE_TYPE = type(None)
_POST_PROCESS_ATTR = "__ninja_service_objects_post_process_callbacks__"


def _get_post_process_callbacks(func: Callable[..., Any]) -> tuple[PostProcess, ...]:
    return tuple(getattr(func, _POST_PROCESS_ATTR, ()))


def _set_post_process_callbacks(
    func: Callable[..., Any],
    callbacks: tuple[PostProcess, ...],
) -> None:
    setattr(func, _POST_PROCESS_ATTR, callbacks)


def _run_post_process_callbacks(
    callbacks: tuple[PostProcess, ...],
    result: Any,
) -> None:
    for callback in callbacks:
        callback(result)


def _get_schema_model(annotation: Any) -> tuple[type[BaseModel], bool] | None:
    """Return a Pydantic model class and whether None is accepted."""
    if annotation is Parameter.empty:
        return None

    origin = get_origin(annotation)

    if origin is Annotated:
        args = get_args(annotation)
        if not args:
            return None
        return _get_schema_model(args[0])

    if origin in (Union, UnionType):
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not _NONE_TYPE]
        if len(non_none_args) != 1 or len(non_none_args) == len(args):
            return None

        schema = _get_schema_model(non_none_args[0])
        if schema is None:
            return None

        schema_model, _allow_none = schema
        return schema_model, True

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation, False

    return None


def _validate_bound_arguments(
    call_signature: Signature,
    bound_arguments: BoundArguments,
) -> BoundArguments:
    bound_arguments.apply_defaults()

    for name, value in list(bound_arguments.arguments.items()):
        parameter = call_signature.parameters[name]
        schema = _get_schema_model(parameter.annotation)
        if schema is None:
            continue

        schema_model, allow_none = schema
        if value is None and allow_none:
            continue

        if isinstance(value, schema_model):
            continue

        bound_arguments.arguments[name] = schema_model.model_validate(value)

    return bound_arguments


@overload
def service_object(
    func: FuncT,
    *,
    db_transaction: bool = True,
    using: str = DEFAULT_DB_ALIAS,
    post_process: PostProcess | None = None,
) -> FuncT: ...


@overload
def service_object(
    func: None = None,
    *,
    db_transaction: bool = True,
    using: str = DEFAULT_DB_ALIAS,
    post_process: PostProcess | None = None,
) -> Callable[[FuncT], FuncT]: ...


def service_object(
    func: FuncT | None = None,
    *,
    db_transaction: bool = False,
    using: str = DEFAULT_DB_ALIAS,
    post_process: PostProcess | None = None,
) -> FuncT | Callable[[FuncT], FuncT]:
    """
    Decorate a function with service-object validation and transaction behavior.

    Any argument annotated with a Pydantic BaseModel subclass is validated before
    the wrapped function runs. When transactions are enabled, post-process hooks
    are scheduled with ``transaction.on_commit`` and receive the function result.
    """

    def decorator(inner: FuncT) -> FuncT:
        call_signature = signature(inner)
        callbacks = _get_post_process_callbacks(inner)
        if post_process is not None:
            callbacks = (*callbacks, post_process)

        @wraps(inner)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            bound_arguments = _validate_bound_arguments(
                call_signature,
                call_signature.bind(*args, **kwargs),
            )

            if db_transaction:
                with transaction.atomic(using=using):
                    result = inner(*bound_arguments.args, **bound_arguments.kwargs)
                    callbacks = _get_post_process_callbacks(wrapped)
                    if callbacks:
                        transaction.on_commit(
                            lambda callbacks=callbacks, result=result: (
                                _run_post_process_callbacks(callbacks, result)
                            )
                        )
                    return result

            result = inner(*bound_arguments.args, **bound_arguments.kwargs)
            callbacks = _get_post_process_callbacks(wrapped)
            if callbacks:
                _run_post_process_callbacks(callbacks, result)
            return result

        _set_post_process_callbacks(wrapped, callbacks)
        return cast(FuncT, wrapped)

    if func is None:
        return decorator

    return decorator(func)


def post_process(callback: PostProcess) -> Callable[[FuncT], FuncT]:
    """Register a callback to run after a decorated service function succeeds."""

    def decorator(func: FuncT) -> FuncT:
        print("decorator called with func:", func)
        callbacks = (*_get_post_process_callbacks(func), callback)
        print("setting callbacks:", callbacks)
        _set_post_process_callbacks(func, callbacks)
        return func

    return decorator


service = service_object
