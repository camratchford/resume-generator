import asyncio

import pytest
from click import Choice
from textual.widgets import Input, Select, Static

from resume_generator.user_input.undefined_variable_form import (
    _coerce_to_type,
    _is_valid_float,
    new_template_form,
)


@pytest.mark.parametrize(
    "value, target_type, expected",
    [
        ("8", int, 8),
        ("-2", int, -2),
        ("1.5", float, 1.5),
        (True, bool, True),
        ("hello", str, "hello"),
        ("formal", Choice(["formal"]), "formal"),
    ],
)
def test_coerce_to_type(value, target_type, expected):
    assert _coerce_to_type(value, target_type) == expected


def test_coerce_to_int_rejects_non_numbers():
    with pytest.raises(ValueError):
        _coerce_to_type("eight", int)


@pytest.mark.parametrize("value, expected", [("1", True), ("-1.5e3", True), ("abc", False), ("", False)])
def test_is_valid_float(value, expected):
    assert _is_valid_float(value) is expected


def run_form(variables, defaults=None, interact=None):
    async def run():
        app = new_template_form()(variables, defaults=defaults)
        async with app.run_test() as pilot:
            if interact:
                await interact(app, pilot)
            await pilot.press("ctrl+s")
            await pilot.pause()
            error_text = str(app.query_one("#error-msg", Static).render())
        return app.return_value, error_text

    return asyncio.run(run())


def test_form_submits_defaults_coerced_to_their_types():
    variables = {"company": str, "years": int, "ratio": float, "remote": bool, "tone": Choice(["formal", "casual"])}
    defaults = {"company": "Cold Bore", "years": 8, "ratio": 0.5, "remote": True, "tone": "casual"}

    result, _ = run_form(variables, defaults)

    assert result == defaults


def test_form_reports_empty_fields_instead_of_submitting():
    result, error_text = run_form({"company": str})

    assert result is None
    assert "'company' cannot be empty." in error_text


def test_form_rejects_invalid_numbers():
    result, error_text = run_form({"years": int}, {"years": "eight"})

    assert result is None
    assert "'years' has an invalid value." in error_text


def test_form_requires_a_choice_selection():
    result, error_text = run_form({"tone": Choice(["formal", "casual"])}, {"tone": "not-a-choice"})

    assert result is None
    assert "'tone' requires a selection." in error_text


def test_form_uses_typed_values():
    async def type_company(app, pilot):
        app.query_one("#field_company", Input).value = "Typed Co"

    result, _ = run_form({"company": str}, interact=type_company)

    assert result == {"company": "Typed Co"}


def test_escape_cancels_the_form():
    async def run():
        app = new_template_form()({"company": str}, defaults={"company": "x"})
        async with app.run_test() as pilot:
            await pilot.press("escape")
            await pilot.pause()
        return app.return_value

    assert asyncio.run(run()) is None


def test_choice_field_is_rendered_as_a_select():
    async def run():
        app = new_template_form()({"tone": Choice(["formal", "casual"])})
        async with app.run_test():
            return type(app.query_one("#field_tone"))

    assert asyncio.run(run()) is Select
