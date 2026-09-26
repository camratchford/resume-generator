from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Any, Mapping, Sequence

SELECTION_KEYS = ("include", "exclude")


class SelectionError(ValueError):
    pass


def row_table(row: Any) -> str:
    return type(row).__name__


def row_key(row: Any) -> str | None:
    primary_keys = getattr(row, "_primary_keys", None)
    if not primary_keys or len(primary_keys) != 1:
        return None
    return str(next(iter(primary_keys.values())))


def parse_table_lists(value: Any, layer_name: str, selection_key: str) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SelectionError(f"'{selection_key}' in {layer_name} must map table names to lists of keys")

    tables = {}
    for table, keys in value.items():
        if not isinstance(keys, Sequence) or isinstance(keys, str):
            raise SelectionError(f"'{selection_key}.{table}' in {layer_name} must be a list of keys")
        tables[str(table)] = [str(key) for key in keys]
    return tables


def parse_layer(layer: Mapping, layer_name: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    included = parse_table_lists(layer.get("include"), layer_name, "include")
    excluded = parse_table_lists(layer.get("exclude"), layer_name, "exclude")

    conflicts = [
        f"{table}: {key}" for table, keys in included.items() for key in keys if key in excluded.get(table, [])
    ]
    if conflicts:
        raise SelectionError(f"{layer_name} both includes and excludes: {', '.join(conflicts)}")
    return included, excluded


@dataclass
class Selection:
    pins: dict[str, list[str]] = field(default_factory=dict)
    exclusions: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    def from_layers(cls, layers: Sequence[tuple[str, Mapping]]) -> "Selection":
        """Merge include/exclude layers, most specific first: the first layer to mention a row decides it."""
        decided = set()
        selection = cls()
        for layer_name, layer in layers:
            included, excluded = parse_layer(layer, layer_name)
            for table, keys in included.items():
                for key in keys:
                    if (table, key) not in decided:
                        decided.add((table, key))
                        selection.pins.setdefault(table, []).append(key)
            for table, keys in excluded.items():
                for key in keys:
                    if (table, key) not in decided:
                        decided.add((table, key))
                        selection.exclusions.setdefault(table, set()).add(key)
        return selection

    def is_excluded(self, row: Any) -> bool:
        return row_key(row) in self.exclusions.get(row_table(row), set())

    def filter(self, rows: Sequence[Any]) -> list[Any]:
        return [row for row in rows if not self.is_excluded(row)]

    def pin_index(self, row: Any) -> int | None:
        pins = self.pins.get(row_table(row), [])
        key = row_key(row)
        return pins.index(key) if key in pins else None

    def order(self, ranked_rows: Sequence[Any]) -> list[Any]:
        kept = self.filter(ranked_rows)
        pinned = sorted((row for row in kept if self.pin_index(row) is not None), key=self.pin_index)
        return pinned + [row for row in kept if self.pin_index(row) is None]

    def references(self) -> list[tuple[str, str]]:
        pinned = [(table, key) for table, keys in self.pins.items() for key in keys]
        excluded = [(table, key) for table, keys in self.exclusions.items() for key in sorted(keys)]
        return pinned + excluded

    def unknown_references(self, known_keys: Mapping[str, set[str]]) -> list[str]:
        problems = []
        for table, key in self.references():
            if table not in known_keys:
                problems.append(f"unknown table '{table}' (known tables: {', '.join(sorted(known_keys))})")
                continue
            if key not in known_keys[table]:
                suggestions = get_close_matches(key, sorted(known_keys[table]), n=3)
                hint = f" (did you mean: {', '.join(suggestions)})" if suggestions else ""
                problems.append(f"no {table} named '{key}'{hint}")
        return list(dict.fromkeys(problems))
