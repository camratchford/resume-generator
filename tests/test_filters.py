from datetime import date, datetime
from types import SimpleNamespace

import pytest

from resume_generator.templates.filters import (
    jinja_filter_get_list_item_by_attr,
    jinja_filter_month_year_fmt,
    jinja_filter_phone_num_fmt,
    jinja_filter_with_item_attr_first,
)


@pytest.mark.parametrize("phone_number", ["15551234567", 15551234567])
def test_phone_number_is_formatted(phone_number):
    assert jinja_filter_phone_num_fmt(phone_number) == "1-555-123-4567"


@pytest.mark.parametrize("phone_number", ["5551234567", "1-555-123-4567", "+15551234567", ""])
def test_unrecognized_phone_number_is_returned_unchanged(phone_number):
    assert jinja_filter_phone_num_fmt(phone_number) == phone_number


@pytest.mark.parametrize("value", [date(2024, 3, 1), datetime(2024, 3, 1, 12, 30)])
def test_month_year_format(value):
    assert jinja_filter_month_year_fmt(value) == "March 2024"


def make_items(*names):
    return [SimpleNamespace(name=name) for name in names]


def test_get_list_item_by_attr_returns_first_match():
    items = make_items("alpha", "beta", "beta")

    assert jinja_filter_get_list_item_by_attr(items, "name", "beta") is items[1]


def test_get_list_item_by_attr_returns_empty_string_without_match():
    assert jinja_filter_get_list_item_by_attr(make_items("alpha"), "name", "gamma") == ""


def test_with_item_attr_first_moves_a_single_match_to_the_front():
    items = make_items("alpha", "beta", "gamma")

    result = jinja_filter_with_item_attr_first(items, "name", "gamma")

    assert [item.name for item in result] == ["gamma", "alpha", "beta"]


def test_with_item_attr_first_orders_matches_by_priority():
    items = make_items("alpha", "beta", "gamma", "delta")

    result = jinja_filter_with_item_attr_first(items, "name", ["delta", "beta"])

    assert [item.name for item in result] == ["delta", "beta", "alpha", "gamma"]


def test_with_item_attr_first_ignores_values_with_no_match():
    items = make_items("alpha", "beta")

    result = jinja_filter_with_item_attr_first(items, "name", ["missing", "beta"])

    assert [item.name for item in result] == ["beta", "alpha"]


def test_with_item_attr_first_returns_input_for_unsupported_value_type():
    items = make_items("alpha")

    assert jinja_filter_with_item_attr_first(items, "name", 5) is items
