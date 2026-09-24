from datetime import date, datetime, timezone
from typing import Optional

import pytest

from resume_generator.data.model_field_typing import (
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
from resume_generator.resume import ALL_MODELS, Experience, Model, Skill
from resume_generator.resume.skill import SkillCategorySkills


@pytest.mark.parametrize("value", ["text", 1, 1.5, True, b"bytes"])
def test_scalar_values_are_scalar(value):
    assert is_scalar_type(value)


@pytest.mark.parametrize("value", [None, [], {}, date(2020, 1, 1)])
def test_non_scalar_values_are_not_scalar(value):
    assert not is_scalar_type(value)


@pytest.mark.parametrize("annotation", [int | None, Optional[int], str | int])
def test_union_types_are_detected(annotation):
    assert is_union_type(annotation)


@pytest.mark.parametrize("annotation", [int, list[int], None])
def test_non_union_types_are_not_detected(annotation):
    assert not is_union_type(annotation)


def test_list_types_are_detected():
    assert is_list_type(list[str])
    assert not is_list_type(list)
    assert not is_list_type(str)


def test_first_type_from_union_skips_trailing_none():
    assert get_first_type_from_union(int | None) is int


def test_first_type_from_union_skips_leading_none():
    assert get_first_type_from_union(None | int) is int


def test_base_model_list_contains_every_resume_model():
    models = get_model_base_model_list(Model)

    assert set(ALL_MODELS) <= set(models)


def test_base_model_list_rejects_non_models():
    with pytest.raises(TypeError):
        get_model_base_model_list(dict)


def test_type_annotations_resolve_scalars_and_relationships():
    annotations = get_model_type_annotations(Experience)

    assert annotations["canonical_name"] is str
    assert annotations["date_from"] is date
    assert is_list_type(annotations["details"])


def test_type_annotations_reject_non_models():
    with pytest.raises(TypeError):
        get_model_type_annotations(dict)


def test_primary_key_reference_extracts_only_primary_key_fields():
    reference = get_primary_key_reference(Experience, {"canonical_name": "job", "company": "Test Co"})

    assert reference == {"canonical_name": "job"}


def test_primary_key_reference_supports_composite_keys():
    reference = get_primary_key_reference(SkillCategorySkills, {"skill_name": "Python", "category_name": "DevOps"})

    assert reference == {"skill_name": "Python", "category_name": "DevOps"}


def test_primary_key_reference_rejects_non_mappings():
    with pytest.raises(TypeError):
        get_primary_key_reference(Skill, "Python")


def test_primary_key_reference_reports_missing_keys():
    with pytest.raises(KeyError, match="skill_name"):
        get_primary_key_reference(SkillCategorySkills, {"category_name": "DevOps"})


def test_date_string_is_parsed():
    assert get_date_from_date_str("2024-02-29") == date(2024, 2, 29)


def test_date_objects_pass_through():
    value = date(2024, 1, 1)

    assert get_date_from_date_str(value) is value


def test_unparseable_date_raises_value_error():
    with pytest.raises(ValueError, match="as a date"):
        get_date_from_date_str("January 2024")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2024-01-02T03:04:05", datetime(2024, 1, 2, 3, 4, 5)),
        ("2024-01-02T03:04:05Z", datetime(2024, 1, 2, 3, 4, 5)),
        ("2024-01-02T03:04:05.123456", datetime(2024, 1, 2, 3, 4, 5, 123456)),
        ("2024-01-02T03:04:05+0000", datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)),
        ("2024-01-02", datetime(2024, 1, 2)),
    ],
)
def test_datetime_formats_are_parsed(text, expected):
    assert get_datetime_from_datetime_str(text) == expected


def test_datetime_objects_pass_through():
    value = datetime(2024, 1, 1, 12)

    assert get_datetime_from_datetime_str(value) is value


def test_unparseable_datetime_raises_value_error():
    with pytest.raises(ValueError, match="as a datetime"):
        get_datetime_from_datetime_str("yesterday")
