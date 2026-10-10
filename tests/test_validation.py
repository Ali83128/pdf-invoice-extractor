from decimal import Decimal

from extractor import extract_invoice
from extractor.models import Invoice, LineItem
from extractor.validate import validate
from tests.conftest import SAMPLES


def make(sub="30.00", tax="3.00", total="33.00"):
    inv = Invoice("x.pdf", invoice_number="A1", vendor="V", currency="USD", invoice_date="2026-01-01",
                  subtotal=Decimal(sub), tax=Decimal(tax), total=Decimal(total))
    inv.line_items = [LineItem("a", Decimal(1), Decimal("10.00"), Decimal("10.00")),
                      LineItem("b", Decimal(2), Decimal("10.00"), Decimal("20.00"))]
    return inv


def test_consistent_invoice_passes():
    inv = make()
    validate(inv)
    assert inv.review_reasons == []


def test_subtotal_mismatch_is_flagged_not_hidden():
    inv = make(sub="25.00", total="28.00")
    validate(inv)
    assert any("line items sum to 30.00" in r for r in inv.review_reasons)


def test_total_mismatch_is_flagged():
    inv = make(total="40.00")
    validate(inv)
    assert any("subtotal + tax" in r for r in inv.review_reasons)


def test_bad_line_arithmetic_is_flagged():
    inv = make()
    inv.line_items[1] = LineItem("b", Decimal(3), Decimal("10.00"), Decimal("20.00"))
    validate(inv)
    assert any(r.startswith("line 2:") for r in inv.review_reasons)


def test_missing_total_is_flagged():
    inv = make()
    inv.total = None
    validate(inv)
    assert "total not found" in inv.review_reasons


def test_vendor_typo_sample_goes_to_review():
    inv = extract_invoice(SAMPLES / "12_kestrel.pdf")
    assert inv.needs_review
    assert any("subtotal" in r for r in inv.review_reasons)
