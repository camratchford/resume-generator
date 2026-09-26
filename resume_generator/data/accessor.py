from typing import Any, Mapping, Type

from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session

from resume_generator.data.model_field_typing import get_model_base_model_list, get_primary_key_reference
from resume_generator.selection import Selection


class DBAccessor(Mapping):
    """Read-only, dict-like access to a collection of SQLAlchemy models.

    Can be used in place of a plain `dict` as `jinja2.Environment`'s
    `globals` attribute. If an accessed key is not a table name known to
    `base_model`, it falls back to a normal dictionary backed by `self._data`
    (seeded from `data_key_values`). Accessing a table name always returns
    every row for that table as a list of model instances.

    Args:
        base_model: The parent model every table's model is a subclass of -
            for sqlmodel, `SQLModel`; for sqlalchemy, a subclass of
            `DeclarativeBase`. When using `SQLModel`, every model is read
            from SQLModel's single global registry, since `SQLModel.registry`
            isn't otherwise accessible - passing a custom `registry` to a
            `SQLModel` subclass isn't supported here.
        engine: The return value of `sqlalchemy.create_engine()`
            (`sqlmodel.create_engine()` returns the same type).
        sqlalchemy_session: An already-opened `sqlalchemy.orm.Session`. When
            omitted, a new session is opened on `__enter__` and closed on
            `__exit__`.
        **data_key_values: Initial non-table key/value pairs, accessible the
            same way as table names.

    Raises:
        TypeError: If `engine` is not a `sqlalchemy.Engine`.
    """

    _engine: Engine = None
    _session: Session = None
    _data: dict[str, DeclarativeBase | None | Any]
    _models: dict[str, Type[DeclarativeBase]]

    def __init__(
        self,
        base_model: Type[DeclarativeBase],
        engine: Engine,
        sqlalchemy_session: Session = None,
        selection: Selection = None,
        **data_key_values,
    ):
        self._selection = selection or Selection()
        if sqlalchemy_session is not None:
            self._session = sqlalchemy_session

        self._engine = engine
        models = get_model_base_model_list(base_model)

        if not isinstance(engine, Engine):
            raise TypeError(f"Parameter <engine>'s type should be a subclass of sqlalchemy.Engine - got {engine}")

        self._models = {model.__name__: model for model in models}
        placeholder_keys = {model: None for model in self._models}
        self._data = {
            **placeholder_keys,
            **data_key_values,
            "get_by_pk": self.get_by_pk,
            "filter_where": self.filter_where,
            "filter_where_eval": self.filter_where_eval,
        }

    @property
    def table_names(self) -> list[str]:
        return list(self._models)

    def _get_from_db(self, model: Type[DeclarativeBase]):
        return self._selection.filter(self._session.scalars(select(model)).all())

    def get_by_pk(self, model_name: str, **key_value_kw_params):
        if model_name not in self._models:
            raise KeyError(f"No table with name {model_name}")
        model = self._models[model_name]
        primary_key_reference = get_primary_key_reference(model, key_value_kw_params)
        return self._session.get(model, primary_key_reference)

    def filter_where(self, model_name: str, **filter_kw_params):
        if model_name not in self._models:
            raise KeyError(f"No table with name {model_name}")
        model = self._models[model_name]

        select_statement = select(model).where(
            *list(getattr(model, attr) == value for attr, value in filter_kw_params.items())
        )
        return self._selection.filter(self._session.scalars(select_statement).all())

    def filter_where_eval(self, model_name: str, eval_statement: str):
        model = self._models.get(model_name)
        if len(model_name.split(".")) > 1:
            try:
                model = eval(model_name, None, self._models)
            except (SyntaxError, NameError, AttributeError, TypeError) as e:
                raise ValueError(f"Could not evaluate model_name {model_name!r}: {e}") from e
        if not model:
            raise KeyError(f"No table with name {model_name}")

        try:
            clauses = [eval(statement, None, self._models) for statement in eval_statement.split(",")]
        except (SyntaxError, NameError, AttributeError, TypeError) as e:
            raise ValueError(f"Could not evaluate eval_statement {eval_statement!r}: {e}") from e

        try:
            select_statement = select(model).where(*clauses)
            return self._session.scalars(select_statement).all()
        except SQLAlchemyError as e:
            raise ValueError(f"Could not build/execute query for eval_statement {eval_statement!r}: {e}") from e

    def __getitem__(self, key):
        """
        :param key: The table name of the model or the key from init's data_key_values parameter
        :return: Either the corresponding table name instances or the data from init's data_key_values parameter
        """
        model = self._models.get(key)

        if model is None:
            try:
                return self._data.get(key)
            except KeyError as e:
                raise KeyError(f"{self} has no field {key}") from e

        return self._get_from_db(model)

    def __setitem__(self, key, item):
        if key not in self._models:
            self._data[key] = item

    def __delitem__(self, key):
        if key not in self._models:
            del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, key):
        return key in self._data

    def __enter__(self):
        if self._session is None:
            self._session = Session(self._engine)
        return self

    def __exit__(self, *_):
        self._session.close()
        return False

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        if key in self:
            return self[key]

        return default

    def update(self, _dict=None, /, **kwargs):
        if _dict is not None:
            self._data.update(_dict)
        if kwargs:
            self._data.update(kwargs)
