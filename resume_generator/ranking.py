from pathlib import Path
from typing import Any, Protocol, Sequence

from yaml import safe_load


class Ranker(Protocol):
    def rank_details(self, details: Sequence[Any], limit: int | None = None) -> list[Any]: ...

    def rank_skills(self, skills: Sequence[Any], limit: int | None = None) -> list[Any]: ...


def truncate(items: list[Any], limit: int | None, default_limit: int | None) -> list[Any]:
    return items[: limit if limit is not None else default_limit]


def position_key(detail: Any) -> tuple[bool, int]:
    return detail.position is None, detail.position or 0


class PositionRanker:
    def __init__(self, details_limit: int | None = None, skills_limit: int | None = None):
        self.details_limit = details_limit
        self.skills_limit = skills_limit

    def rank_details(self, details: Sequence[Any], limit: int | None = None) -> list[Any]:
        return truncate(sorted(details, key=position_key), limit, self.details_limit)

    def rank_skills(self, skills: Sequence[Any], limit: int | None = None) -> list[Any]:
        return truncate(list(skills), limit, self.skills_limit)


class CategoryRanker:
    def __init__(
        self, category_names: Sequence[str], details_limit: int | None = None, skills_limit: int | None = None
    ):
        self.category_names = list(category_names)
        self.category_ranks = {name: rank for rank, name in enumerate(self.category_names)}
        self.details_limit = details_limit
        self.skills_limit = skills_limit

    def matching_ranks(self, skill: Any) -> list[int]:
        return [
            self.category_ranks[category.name] for category in skill.categories if category.name in self.category_ranks
        ]

    def best_rank(self, ranks: Sequence[int]) -> int:
        return min(ranks, default=len(self.category_ranks))

    def detail_sort_key(self, detail: Any) -> tuple:
        ranks = [rank for skill in detail.skills for rank in self.matching_ranks(skill)]
        return self.best_rank(ranks), -len(ranks), *position_key(detail)

    def rank_details(self, details: Sequence[Any], limit: int | None = None) -> list[Any]:
        return truncate(sorted(details, key=self.detail_sort_key), limit, self.details_limit)

    def rank_skills(self, skills: Sequence[Any], limit: int | None = None) -> list[Any]:
        ranked = sorted(skills, key=lambda skill: self.best_rank(self.matching_ranks(skill)))
        return truncate(ranked, limit, self.skills_limit)


def load_profile(profiles_dir: Path, profile_name: str) -> dict[str, Any]:
    profile_path = profiles_dir / f"{profile_name}.yml"
    if not profile_path.is_file():
        available = sorted(path.stem for path in profiles_dir.glob("*.yml")) if profiles_dir.is_dir() else []
        raise FileNotFoundError(
            f"No profile named '{profile_name}' in {profiles_dir}. Available profiles: {', '.join(available) or 'none'}"
        )

    profile = safe_load(profile_path.read_text()) or {}
    if not isinstance(profile.get("categories", []), list):
        raise TypeError(f"Profile '{profile_name}' must list its categories as a sequence")
    return profile
