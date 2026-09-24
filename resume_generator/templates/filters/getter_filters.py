def jinja_filter_get_list_item_by_attr(list_in: list, attr: str, attr_value: str):
    """Return the first item in a list whose attribute matches a value.

    Similar to Jinja2's built-in `selectattr` filter, but returns only the
    first match instead of an iterable of all matches.

    Args:
        list_in: The list of objects to search.
        attr: The attribute name to compare.
        attr_value: The value `attr` must equal.

    Returns:
        The first matching item, or `""` if none match.
    """
    for item in list_in:
        if getattr(item, attr) == attr_value:
            return item
    return ""


def jinja_filter_with_item_attr_first(list_in: list, attr: str, attr_values: str | list[str]):
    """Reorder a list so items matching given attribute value(s) come first.

    Args:
        list_in: The list of objects to reorder.
        attr: The attribute name to compare.
        attr_values: One or more values of `attr` to move to the front, in
            priority order. If neither a `str` nor a `list`, `list_in` is
            returned unchanged.

    Returns:
        A new list with matching items first (in `attr_values` priority
        order), followed by the remaining items in their original order.
    """
    if not isinstance(attr_values, str) and not isinstance(attr_values, list):
        return list_in

    if isinstance(attr_values, str):
        attr_values = [attr_values]

    result_list = []
    for attr_value in attr_values:
        result_list += [item for item in list_in if getattr(item, attr) == attr_value]

    return result_list + [item for item in list_in if item not in result_list]
