import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# літери (в т.ч. юнікод), розділені пробілом, крапкою, апострофом або дефісом
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-][^\W\d_]+)*\.?$")


def is_valid_email(value: str) -> bool:
    return EMAIL_RE.fullmatch(value) is not None


def is_valid_name(value: str) -> bool:
    return NAME_RE.fullmatch(value) is not None
