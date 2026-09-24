import sys

import pytest
from click import Choice
from jinja2 import DictLoader

from resume_generator.templates import new_template_environment
from resume_generator.templates.environment import TypedVariableEnvironment


def _env(globals_mapping):
    env = TypedVariableEnvironment()
    env.globals = dict(globals_mapping)
    return env


def test_typo_of_a_known_global_raises_with_suggestion():
    env = _env({"Candidate": object()})

    with pytest.raises(NameError, match="did you mean 'Candidate'"):
        env.from_string("{{ Candidat }}")


def test_unrelated_free_variable_is_left_for_prompting():
    env = _env({"Candidate": object()})

    env.from_string("{{ target_job_title }}")

    assert "target_job_title" in env.undeclared_variables
    assert env.undeclared_variables["target_job_title"] is str


def test_reference_to_a_known_global_is_not_flagged_as_undeclared():
    env = _env({"Candidate": object()})

    env.from_string("{{ Candidate }}")

    assert env.undeclared_variables == {}


def test_typed_undeclared_variable_records_the_annotated_type():
    env = _env({})

    env.from_string("{{ years_of_experience: int }}")

    assert env.undeclared_variables["years_of_experience"] is int


def test_type_annotation_is_stripped_before_rendering():
    env = _env({})

    template = env.from_string("{{ years_of_experience: int }} years")

    assert template.render(years_of_experience=8) == "8 years"


def test_unknown_type_name_falls_back_to_str():
    env = _env({})

    env.from_string("{{ start_date: NotARealType }}")

    assert env.undeclared_variables["start_date"] is str


def test_choice_annotation_records_the_choices():
    env = _env({})

    env.from_string("{{ tone: Choice(['formal', 'casual']) }}")

    choice = env.undeclared_variables["tone"]
    assert isinstance(choice, Choice)
    assert list(choice.choices) == ["formal", "casual"]


def test_variables_defined_in_the_template_are_not_undeclared():
    env = _env({})

    env.from_string("{% set company = 'Test Co' %}{{ company }}")

    assert env.undeclared_variables == {}


def test_undefined_variable_raises_at_render_time():
    env = _env({})

    template = env.from_string("{{ never_provided }}")

    with pytest.raises(Exception, match="never_provided"):
        template.render()


def test_get_template_records_undeclared_variables_from_loaded_source():
    env = TypedVariableEnvironment(loader=DictLoader({"cover.md": "Dear {{ hiring_manager }},"}))

    env.get_template("cover.md")

    assert env.undeclared_variables == {"hiring_manager": str}


def test_get_template_passes_through_template_objects():
    env = _env({})
    template = env.from_string("hello")

    assert env.get_template(template) is template


def test_new_template_environment_registers_builtin_filters(home_dir):
    env = new_template_environment(home_dir / "templates", globals_mapping={})

    assert env.from_string("{{ '15551234567' | phone_num_fmt }}").render() == "1-555-123-4567"


def test_new_template_environment_merges_globals_mapping(home_dir):
    env = new_template_environment(home_dir / "templates", globals_mapping={"target_company": "Cold Bore"})

    assert env.from_string("{{ target_company }}").render() == "Cold Bore"


def test_new_template_environment_exposes_database_tables(home_dir, accessor):
    env = new_template_environment(home_dir / "templates", db_accessor=accessor)

    assert env.from_string("{{ Candidate[0].name }}").render() == "Test Candidate"


def test_new_template_environment_loads_from_templates_dir(home_dir, accessor):
    env = new_template_environment(home_dir / "templates", db_accessor=accessor)

    assert "TEST CANDIDATE" in env.get_template("resume.md").render()


def _make_plugin_package(tmp_path, monkeypatch, package_name, source):
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    (package_dir / "plugins.py").write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(package_name, None)
    sys.modules.pop(f"{package_name}.plugins", None)


def test_new_template_environment_loads_custom_filter_modules(home_dir, tmp_path, monkeypatch):
    _make_plugin_package(
        tmp_path, monkeypatch, "custom_filters", "def jinja_filter_shout(value):\n    return value.upper() + '!'\n"
    )

    env = new_template_environment(home_dir / "templates", filters_modules="custom_filters", globals_mapping={})

    assert env.from_string("{{ 'hi' | shout }}").render() == "HI!"


def test_new_template_environment_loads_a_list_of_custom_test_modules(home_dir, tmp_path, monkeypatch):
    _make_plugin_package(
        tmp_path, monkeypatch, "custom_tests", "def jinja_test_answer(value):\n    return value == 42\n"
    )

    env = new_template_environment(home_dir / "templates", tests_modules=["custom_tests"], globals_mapping={})

    assert env.from_string("{{ 42 is answer }}").render() == "True"


def test_new_template_environment_works_with_only_a_templates_dir(home_dir):
    env = new_template_environment(home_dir / "templates")

    assert env.from_string("ok").render() == "ok"
