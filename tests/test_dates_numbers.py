from decimal import Decimal

import pytest

from extractor.numbers import AmbiguousDate, detect_currency, normalise_date, parse_money


@pytest.mark.parametrize("raw,hint,iso", [
    ("03/14/2026", "us", "2026-03-14"),
    ("14.03.2026", "eu", "2026-03-14"),
    ("14 March 2026", None, "2026-03-14"),
    ("March 14, 2026", None, "2026-03-14"),
    ("2026-03-14", None, "2026-03-14"),
    ("03/04/2026", "us", "2026-03-04"),
    ("03/04/2026", "eu", "2026-04-03"),
    ("25/12/2026", None, "2026-12-25"),
])
def test_dates_normalise_to_iso(raw, hint, iso):
    assert normalise_date(raw, hint) == iso


def test_ambiguous_date_without_hint_is_refused():
    with pytest.raises(AmbiguousDate):
        normalise_date("03/04/2026")


def test_garbage_date_raises():
    with pytest.raises(ValueError):
        normalise_date("next tuesday")


@pytest.mark.parametrize("raw,want", [
    ("$1,234.50", "1234.50"), ("1.234,50 EUR", "1234.50"), ("GBP 99.00", "99.00"),
    ("12,40", "12.40"), ("1,234", "1234.00"), ("7", "7.00"),
])
def test_money_formats(raw, want):
    assert parse_money(raw) == Decimal(want)


def test_currency_detection():
    assert detect_currency("Total 12,00 EUR") == "EUR"
    assert detect_currency("Total £12.00") == "GBP"
    assert detect_currency("Total $12.00") == "USD"
