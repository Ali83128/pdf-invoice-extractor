from decimal import Decimal

import pytest

from extractor import extract_invoice
from tests.conftest import SAMPLES

LAYOUT_FILES = {"northwind": "01_northwind.pdf", "brightwater": "02_brightwater.pdf", "kestrel": "03_kestrel.pdf"}


@pytest.mark.parametrize("layout,fname", LAYOUT_FILES.items())
def test_each_layout_parses_every_field(layout, fname, truth):
    inv = extract_invoice(SAMPLES / fname)
    t = truth[fname]
    assert inv.layout == layout
    assert inv.invoice_number == t["invoice_number"]
    assert inv.vendor == t["vendor"]
    assert inv.invoice_date == t["invoice_date"]
    assert inv.currency == t["currency"]
    assert (inv.subtotal, inv.tax, inv.total) == tuple(Decimal(t[k]) for k in ("subtotal", "tax", "total"))
    assert [(li.description, li.quantity, li.amount) for li in inv.line_items] == [
        (w["description"], w["quantity"], Decimal(w["amount"])) for w in t["line_items"]]
    assert not inv.needs_review


def test_all_twelve_samples_match_ground_truth(truth):
    for fname, t in truth.items():
        inv = extract_invoice(SAMPLES / fname)
        assert inv.total == Decimal(t["total"]), fname
        assert inv.invoice_date == t["invoice_date"], fname
        assert len(inv.line_items) == len(t["line_items"]), fname
        assert inv.needs_review == t["expected_review"], fname


def test_european_number_format_is_read_correctly():
    inv = extract_invoice(SAMPLES / "02_brightwater.pdf")
    assert inv.currency == "EUR"
    assert all(li.amount == li.quantity * li.unit_price for li in inv.line_items)
