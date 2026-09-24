from sqlmodel import SQLModel


class Model(SQLModel):
    @property
    def _primary_keys(self):
        return {key.name: getattr(self, key.name) for key in self.__table__.primary_key}

    def __repr__(self):
        primary_keys_string = ", ".join(f"{key}={value}" for key, value in sorted(self._primary_keys.items()))
        return f"{type(self).__name__}({primary_keys_string})"

    def __hash__(self):
        return hash(repr(self))
