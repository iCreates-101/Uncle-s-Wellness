import os
from fastapi.templating import Jinja2Templates

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(_PROJECT_ROOT, "templates"))


def currency_filter(value):
    return f"${value:,.2f}"


def datetime_filter(value):
    if value:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y %I:%M %p")
        try:
            dt = datetime.datetime.fromisoformat(str(value))
            return dt.strftime("%b %d, %Y %I:%M %p")
        except (ValueError, TypeError):
            return str(value)
    return ""


def date_filter(value):
    if value:
        if hasattr(value, "strftime"):
            return value.strftime("%b %d, %Y")
        try:
            dt = datetime.datetime.fromisoformat(str(value))
            return dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            return str(value)
    return ""


templates.env.filters["currency"] = currency_filter
templates.env.filters["datetime"] = datetime_filter
templates.env.filters["date"] = date_filter
