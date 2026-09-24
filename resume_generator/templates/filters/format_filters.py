import datetime


def jinja_filter_phone_num_fmt(phone_num: str):
    """Format an 11-digit US/Canadian phone number string.

    Args:
        phone_num: A string of digits, assumed to be a valid 11-digit
            US/Canadian phone number (country code + area code + number).
            Returned unchanged if it isn't exactly 11 digits.

    Returns:
        The formatted string, e.g. "1-800-222-2222".
    """
    phone_num = str(phone_num)
    if not phone_num.isdigit():
        return phone_num

    if len(phone_num) != 11:
        return phone_num

    return f"{phone_num[0]}-{phone_num[1:4]}-{phone_num[4:7]}-{phone_num[7:]}"


def jinja_filter_month_year_fmt(_datetime: datetime.datetime):
    """Format a datetime as its full month name and year.

    Args:
        _datetime: The datetime to format.

    Returns:
        The formatted string, e.g. "January 2024".
    """
    return _datetime.strftime("%B %Y")
