from datetime import date, datetime
from inspect import isclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from sqlalchemy import Engine
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import DeclarativeBase, Session
from sqlmodel import SQLModel
from yaml import safe_load

from resume_generator.data.model_field_typing import (
    SCALAR_TYPES,
    ModelType,
    ScalarType,
    get_date_from_date_str,
    get_datetime_from_datetime_str,
    get_first_type_from_union,
    get_model_base_model_list,
    get_model_type_annotations,
    get_primary_key_reference,
    is_list_type,
    is_scalar_type,
    is_union_type,
)


class DataImporter:
    """Imports YAML data into a SQLAlchemy/SQLModel-backed database.

    Reads a YAML sequence of records for a given model, coerces each field to
    the model's declared type (including nested relationships and lists of
    related models), and upserts the resulting rows by primary key so that
    re-importing the same data updates existing rows instead of duplicating
    them.

    Args:
        base_model: The parent model every importable model is a subclass
            of - for sqlmodel, `SQLModel`; for sqlalchemy, a subclass of
            `DeclarativeBase`. When using `SQLModel`, every model is read
            from SQLModel's single global registry, since `SQLModel.registry`
            isn't otherwise accessible - passing a custom `registry` to a
            `SQLModel` subclass isn't supported here.
        engine: The return value of `sqlalchemy.create_engine()`
            (`sqlmodel.create_engine()` returns the same type).
        sqlalchemy_session: An already-opened `sqlalchemy.orm.Session`. When
            omitted, a new session is opened on `__enter__` and closed on
            `__exit__`.

    Raises:
        TypeError: If `engine` is not a `sqlalchemy.Engine`.
    """

    _engine: Engine = None
    _session: Session = None
    _base_model: ModelType
    _model_fields: dict[str, Any]
    _all_models: dict[str, ModelType]
    _created_instances: dict[tuple, Any]
    _current_file: Path

    def __init__(
        self,
        base_model: ModelType,
        engine: Engine,
        sqlalchemy_session: Session = None,
    ):
        """
        :param base_model:
            The parent model that each created model is a subclass of,
            for sqlmodel: SQLModel, for sqlalchemy: a subclass of DeclarativeBase
        :param engine:
            The return value of sqlalchemy.create_engine() (sqlmodel uses the same function)
        :param (optional) sqlalchemy_session:
            [Optional] An instantiated and opened sqlalchemy.Session object, typically via the context manager protocol
             - `with Session(engine) as session:`
        """

        if sqlalchemy_session is not None:
            self._session = sqlalchemy_session

        self._engine = engine

        if not isinstance(engine, Engine):
            raise TypeError(f"Parameter <engine>'s type should be a subclass of sqlalchemy.Engine - got {engine}")

        self._base_model = base_model
        self._all_models = {m.__name__: m for m in get_model_base_model_list(base_model)}
        self._model_fields = {m.__name__: get_model_type_annotations(m) for m in self._all_models.values()}
        self._created_instances = {}

    def load_data(self, yaml_text: str, model: ModelType):
        data = safe_load(yaml_text)
        if isinstance(data, Mapping):
            raise TypeError("Top-level YAML object should be a Sequence - got Mapping")
        for instance in data:
            with self._session.no_autoflush:
                upserted = self._upsert(model, self._coerce_instance_data_types(model, instance))
            self._session.add(upserted)
            self._session.commit()

    def load_data_from_file(self, path: Path | str, model: ModelType):
        with open(str(path), "r") as file:
            self.load_data(file.read(), model)

    def _coerce_sequence(self, model: ModelType, field_key: str, field_value: Any, coerced_data: dict):
        if not isinstance(field_value, Sequence):
            raise TypeError(
                f"Invalid type for {model.__name__}.{field_key}, expected Sequence - got '{type(field_value)}'"
            )
        if not field_value:
            coerced_data[field_key] = []
            return coerced_data

        try:
            type_annotation = self._model_fields[model.__name__].get(field_key).__args__[0]
            if not isinstance(type_annotation, str) and hasattr(type_annotation, "__forward_arg__"):
                type_annotation = type_annotation.__forward_arg__
            model_name = type_annotation

        except AttributeError as e:
            raise AttributeError(
                f"Error processing type for {model.__name__}.{field_key} with annotations "
                f"'{self._model_fields[model.__name__].get(field_key).__args__[0]}' "
                f"(Type {type(self._model_fields[model.__name__].get(field_key).__args__[0])})"
                f": {e}"
            ) from e

        if isclass(model_name) and issubclass(model_name, DeclarativeBase):
            model_name = model_name.__tablename__

        model_type = self._all_models.get(model_name)
        if not model_type:
            model_type = model_name

        items_by_primary_key = {}
        has_position_field = "position" in self._model_fields.get(getattr(model_type, "__name__", ""), {})
        for position, instance in enumerate(field_value):
            if isinstance(instance, Mapping):
                if has_position_field and "position" not in instance:
                    instance = {**instance, "position": position}
                instance = self._coerce_instance_data_types(model_type, instance)
            upserted = self._upsert(model_type, instance)
            items_by_primary_key[self._primary_key_of_instance(upserted)] = upserted

        coerced_data[field_key] = list(items_by_primary_key.values())

        return coerced_data

    def _coerce_model(
        self, model: ModelType, field_key: str, field_value: Any, field_type: ModelType, coerced_data: dict
    ):
        if not isinstance(field_value, Mapping):
            raise TypeError(
                f"Invalid type for {model.__name__}.{field_key}, expected Mapping - got '{type(field_value)}'"
            )
        coerced_data[field_key] = self._upsert(field_type, self._coerce_instance_data_types(field_type, field_value))

    @staticmethod
    def _coerce_scalar(model: ModelType, field_key: str, field_value: Any, field_type: ScalarType, coerced_data: dict):
        if not is_scalar_type(field_value) and field_value is not None:
            scalar_types_str = "[" + ", ".join(str(_type) for _type in SCALAR_TYPES) + "]"
            raise TypeError(
                f"Invalid type for {model.__name__}.{field_key}, "
                f"expecting '{field_type}' '{scalar_types_str}' - got '{type(field_value)}'"
            )
        try:
            coerced_data[field_key] = field_type(field_value)
        except TypeError as e:
            raise TypeError(f"{e.args}\n\n\n{field_type} is not callable") from e

    def _coerce_instance_data_types(self, model: ModelType, instance_data: dict[str, Any]):
        coerced_data = {}
        for field_key in instance_data:
            field_type = self._model_fields[model.__name__].get(field_key, None)

            if is_union_type(field_type):
                field_type = get_first_type_from_union(field_type)

            field_value = instance_data[field_key]
            if field_type is None:
                raise KeyError(f"Invalid field for model '{model.__name__}': Has no field '{field_key}'")

            if is_list_type(field_type):
                coerced_data = self._coerce_sequence(model, field_key, field_value, coerced_data)

            elif isclass(field_type) and issubclass(field_type, (DeclarativeBase, SQLModel)):
                self._coerce_model(model, field_key, field_value, field_type, coerced_data)

            elif field_type is date:
                coerced_data[field_key] = get_date_from_date_str(field_value)

            elif field_type is datetime:
                coerced_data[field_key] = get_datetime_from_datetime_str(field_value)

            else:
                self._coerce_scalar(model, field_key, field_value, field_type, coerced_data)

        return coerced_data

    @staticmethod
    def _primary_key_of_instance(instance: Any):
        primary_key_columns = [column.name for column in type(instance).__table__.primary_key]
        return tuple(getattr(instance, column) for column in primary_key_columns)

    def _merge_list_field(self, existing_items: list, new_items: list):
        """Union an existing relationship collection with newly-imported items.

        Keyed by each item's primary key, so re-importing a partial list
        (e.g. a `Skill`'s `categories`) adds to what's already attached
        instead of replacing the whole collection. Where both sides share a
        primary key, the new item wins.
        """
        merged = {self._primary_key_of_instance(item): item for item in existing_items}
        for item in new_items:
            merged[self._primary_key_of_instance(item)] = item
        return list(merged.values())

    def _upsert(self, model: ModelType, reference_value: Any):
        primary_key_reference = get_primary_key_reference(model, reference_value)
        init_data = reference_value if isinstance(reference_value, (Mapping, dict)) else primary_key_reference
        try:
            instance = self._session.get(model, primary_key_reference)
        except InvalidRequestError as e:
            raise InvalidRequestError(f"{e}: got {primary_key_reference}")

        created_key = (model, tuple(sorted(primary_key_reference.items())))
        instance = instance or self._created_instances.get(created_key)
        if not instance:
            instance = model(**init_data)
            self._created_instances[created_key] = instance
            return instance

        for key, value in init_data.items():
            if isinstance(value, list):
                value = self._merge_list_field(getattr(instance, key, None) or [], value)
            setattr(instance, key, value)

        return instance

    def __enter__(self):
        if self._session is None:
            self._session = Session(self._engine)
        return self

    def __exit__(self, *_):
        self._session.close()
        return False
