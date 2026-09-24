from __future__ import annotations

import importlib
import typing
from datetime import date, datetime
from inspect import isclass
from pprint import pformat
from types import UnionType

# Only importing the whole modules so ModelType's docstring shows which package the classes come from
import sqlalchemy.orm
import sqlmodel
from sqlmodel.main import default_registry

SCALAR_TYPES = {str, int, bytes, float, bool}
ScalarType: typing.TypeAlias = typing.Type[str | int | bytes | float | bool]

VALID_DATETIME_FORMATS: tuple[str, ...] = (
    # Ordered deliberately: a plain tuple (not a set) so match priority for an
    # ambiguous input (e.g. a trailing "Z") is deterministic across runs.
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
    "%H:%M:%S.%f",
    "%H:%M:%S",
)

ModelType: typing.TypeAlias = typing.Type[sqlmodel.SQLModel | sqlalchemy.orm.DeclarativeBase]
"""A model class - either an SQLModel or SQLAlchemy DeclarativeBase subclass."""


def get_model_base_model_list(base_model: ModelType):
    if issubclass(base_model, sqlmodel.SQLModel):
        # SQLModel.registry is inaccessible because of some metaclassing sorcery, so this
        # always reads from SQLModel's single global registry instead. Documented as a
        # restriction on DataImporter/DBAccessor's base_model - see their docstrings.
        models = [i.class_ for i in default_registry.mappers]
    elif isclass(base_model) and issubclass(base_model, (sqlalchemy.orm.DeclarativeBase, sqlmodel.SQLModel)):
        models = [i.class_ for i in base_model.registry.mappers]
    else:
        raise TypeError(
            f"Parameter <base_model>'s type should be a subclass of sqlalchemy.DeclarativeBase - got {base_model}"
        )

    return models


def derive_type_from_mapped_column(mapped: sqlalchemy.orm.Mapped, module_name: str):
    first_arg = mapped.__args__[0]

    if not isinstance(first_arg, typing.ForwardRef):
        return first_arg

    module = importlib.import_module(module_name)
    return getattr(module, first_arg.__forward_arg__, None)


def derive_type_from_annotated_type(annotated_type: typing.Any, module_name: str):
    if not isinstance(annotated_type, typing._GenericAlias):
        return annotated_type

    return derive_type_from_mapped_column(annotated_type, module_name)


def get_model_type_annotations(model: ModelType):
    if issubclass(model, sqlmodel.SQLModel):
        annotations = {
            name: derive_type_from_annotated_type(annotation, model.__module__)
            for name, annotation in model.__annotations__.items()
        }

    elif issubclass(model, sqlalchemy.orm.DeclarativeBase):
        annotations = {
            name: derive_type_from_mapped_column(annotation, model.__module__)
            for name, annotation in model.__annotations__.items()
        }
    else:
        raise TypeError(f"Parameter <model>'s type should be a subclass of sqlalchemy.DeclarativeBase - got {model}")
    return annotations


def is_scalar_type(value: typing.Any):
    return any(isinstance(value, _type) for _type in SCALAR_TYPES)


def is_union_type(_type: typing.Any) -> bool:
    origin = typing.get_origin(_type)
    return origin is typing.Union or origin is UnionType


def is_list_type(_type: typing.Any) -> bool:
    origin = typing.get_origin(_type)
    return origin is list


def is_forward_ref(_type: typing.Any) -> bool:
    origin = typing.get_origin(_type)
    return origin is typing.ForwardRef


def get_first_type_from_union(_type: typing.Union | UnionType):
    for arg in _type.__args__:
        if arg is not type(None):
            return arg
    return None


def get_primary_key_reference(model: ModelType, reference_value: typing.Any):
    primary_key_field = model.__table__.primary_key

    field_types = get_model_type_annotations(model)
    primary_keys = [key.name for key in primary_key_field]
    primary_key_types = {primary_key: field_types[primary_key] for primary_key in primary_keys}

    primary_key_types_str = "[" + ", ".join(f"{k}: {v}" for k, v in primary_key_types.items()) + "]"
    key_type = "single" if len(primary_key_types) == 1 else " composite"
    if not isinstance(reference_value, (typing.Mapping, dict)):
        raise TypeError(
            f"Invalid primary key reference for {model}."
            f"{model.__name__} has a {key_type} primary key: {primary_key_types_str} "
            f" - got {pformat(reference_value)}"
        )

    if not all(key in reference_value for key in primary_key_types):
        missing_keys = [key for key in primary_key_types if key not in reference_value]
        raise KeyError(
            f"Invalid model reference for {model}."
            f"{model.__name__} has a {key_type} primary key: {primary_key_types_str} "
            f"Missing key(s)='{', '.join(missing_keys)}'"
            f" - got {pformat(reference_value)}"
        )

    return {k: reference_value[k] for k in primary_key_types}


def get_date_from_date_str(maybe_date_str: str):
    if not isinstance(maybe_date_str, str):
        return maybe_date_str
    try:
        return datetime.strptime(maybe_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Could not parse '{maybe_date_str}' as a date")


def get_datetime_from_datetime_str(maybe_datetime_str: str):
    if isinstance(maybe_datetime_str, date) or isinstance(maybe_datetime_str, datetime):
        return maybe_datetime_str

    for fmt in VALID_DATETIME_FORMATS:
        try:
            return datetime.strptime(maybe_datetime_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse '{maybe_datetime_str}' as a datetime")
