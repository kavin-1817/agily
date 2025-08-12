from django import template

register = template.Library()


@register.filter(name="truncate_title")
def truncate_title(value: str, length: int = 45) -> str:
    try:
        max_len = int(length)
    except Exception:
        max_len = 45

    if value is None:
        return ""

    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


@register.filter(name="truncate_desc")
def truncate_desc(value: str, length: int = 60) -> str:
    try:
        max_len = int(length)
    except Exception:
        max_len = 60

    if not value:
        return ""

    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."




