"""Money and date parsing that copes with US, EU and UK formatting."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

MONEY_RE = re.compile(r"-?\d[\d.,\s]*\d|-?\d")
CURRENCY_HINTS = [("EUR", ("EUR", "€")), ("GBP", ("GBP", "£")), ("USD", ("USD", "$"))]


def parse_money(text: str, decimal_comma: bool | None = None) -> Decimal | None:
    """Parse '1,234.50', '1.234,50', '$1,234.50' or 'GBP 99.00' into Decimal('1234.50')."""
    if text is None:
        return None
    m = MONEY_RE.search(text.replace(" ", " "))
    if not m:
        return None
    s = m.group(0).replace(" ", "")
    if decimal_comma is None:
        # the separator that appears last, followed by exactly two digits, is the decimal mark
        last_dot, last_comma = s.rfind("."), s.rfind(",")
        decimal_comma = last_comma > last_dot and len(s) - last_comma - 1 == 2
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def detect_currency(text: str) -> str | None:
    for code, marks in CURRENCY_HINTS:
        if any(mark in text for mark in marks):
            return code
    return None


DATE_FORMATS = {
    "us": ["%m/%d/%Y", "%m-%d-%Y"],
    "eu": ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"],
    "iso": ["%Y-%m-%d"],
    "long": ["%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y"],
}


class AmbiguousDate(ValueError):
    pass


def normalise_date(text: str, hint: str | None = None) -> str:
    """Return ISO date. `hint` ('us' or 'eu') resolves 03/04/2026-style dates.

    Raises AmbiguousDate when a numeric dd/mm vs mm/dd date cannot be resolved,
    and ValueError when nothing matches.
    """
    text = text.strip().rstrip(".")
    for fmt in DATE_FORMATS["iso"] + DATE_FORMATS["long"]:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    if hint in ("us", "eu"):
        for fmt in DATE_FORMATS[hint]:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                pass
    us = eu = None
    for fmt in DATE_FORMATS["us"]:
        try:
            us = datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    for fmt in DATE_FORMATS["eu"]:
        try:
            eu = datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    if us and eu and us != eu:
        raise AmbiguousDate(f"'{text}' could be {us.isoformat()} or {eu.isoformat()}")
    if us or eu:
        return (us or eu).isoformat()
    raise ValueError(f"unrecognised date '{text}'")
