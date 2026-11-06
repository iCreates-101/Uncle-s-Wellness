import datetime as _dt

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def currency_filter(value):
    return f"${value:,.2f}"


def _as_datetime(value):
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    text = str(value).strip()
    if not text:
        return None
    try:
        return _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def datetime_filter(value):
    dt = _as_datetime(value)
    if dt:
        return dt.strftime("%b %d, %Y %I:%M %p")
    return ""


def date_filter(value):
    dt = _as_datetime(value)
    if dt:
        return dt.strftime("%b %d, %Y")
    return ""


templates.env.filters["currency"] = currency_filter
templates.env.filters["datetime"] = datetime_filter
templates.env.filters["date"] = date_filter
