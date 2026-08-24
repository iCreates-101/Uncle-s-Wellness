from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def currency_filter(value):
    return f"${value:,.2f}"


def datetime_filter(value):
    if value:
        return value.strftime("%b %d, %Y %I:%M %p")
    return ""


def date_filter(value):
    if value:
        return value.strftime("%b %d, %Y")
    return ""


templates.env.filters["currency"] = currency_filter
templates.env.filters["datetime"] = datetime_filter
templates.env.filters["date"] = date_filter
