import pytest
from jinja2 import Environment

from resume_generator.data import DBAccessor
from resume_generator.resume import Model


def test_rejects_non_engine():
    with pytest.raises(TypeError):
        DBAccessor(base_model=Model, engine="sqlite://")


def test_table_name_returns_every_row(accessor):
    assert {skill.name for skill in accessor["Skill"]} == {"Python", "Terraform"}


def test_extra_data_is_accessible_by_key(engine):
    with DBAccessor(base_model=Model, engine=engine, target_company="Cold Bore") as accessor:
        assert accessor["target_company"] == "Cold Bore"


def test_unknown_key_returns_none(accessor):
    assert accessor["does_not_exist"] is None


def test_get_falls_back_to_default_for_unknown_key(accessor):
    assert accessor.get("does_not_exist", "fallback") == "fallback"


def test_table_names_and_query_helpers_are_keys(accessor):
    assert "Skill" in accessor
    assert "get_by_pk" in accessor
    assert "filter_where" in accessor
    assert "filter_where_eval" in accessor


def test_setting_a_table_name_does_not_shadow_the_table(accessor):
    accessor["Skill"] = "overwritten"

    assert [skill.name for skill in accessor["Skill"]]


def test_set_update_and_delete_extra_data(accessor):
    accessor["first"] = 1
    accessor.update({"second": 2}, third=3)

    assert (accessor["first"], accessor["second"], accessor["third"]) == (1, 2, 3)

    del accessor["first"]

    assert "first" not in accessor


def test_get_by_pk(accessor):
    experience = accessor.get_by_pk("Experience", canonical_name="test-co-engineer")

    assert experience.company == "Test Co"


def test_get_by_pk_returns_none_for_missing_row(accessor):
    assert accessor.get_by_pk("Experience", canonical_name="nope") is None


def test_get_by_pk_rejects_unknown_table(accessor):
    with pytest.raises(KeyError):
        accessor.get_by_pk("Spaceship", name="x")


def test_filter_where(accessor):
    projects = accessor.filter_where("Project", category_name="Hobby")

    assert [project.canonical_name for project in projects] == ["hobby-project"]


def test_filter_where_rejects_unknown_table(accessor):
    with pytest.raises(KeyError):
        accessor.filter_where("Spaceship", name="x")


def test_filter_where_eval(accessor):
    experiences = accessor.filter_where_eval("Experience", "Experience.company == 'Test Co'")

    assert [experience.canonical_name for experience in experiences] == ["test-co-engineer"]


def test_filter_where_eval_combines_comma_separated_clauses(accessor):
    projects = accessor.filter_where_eval(
        "Project",
        "Project.category_name == 'Professional', Project.canonical_name == 'hobby-project'",
    )

    assert projects == []


def test_filter_where_eval_rejects_invalid_statement(accessor):
    with pytest.raises(ValueError, match="eval_statement"):
        accessor.filter_where_eval("Experience", "Experience.nonexistent_column ==")


def test_filter_where_eval_rejects_unknown_table(accessor):
    with pytest.raises(KeyError):
        accessor.filter_where_eval("Spaceship", "True")


def test_query_helpers_are_callable_from_templates(accessor):
    environment = Environment()
    environment.globals = accessor

    rendered = environment.from_string(
        "{{ get_by_pk('Experience', canonical_name='test-co-engineer').title }}"
    ).render()

    assert rendered == "Test Engineer"
