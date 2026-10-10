"""Cross-checks that turn silent errors into a 'needs review' flag."""
from decimal import Decimal

TOLERANCE = Decimal("0.01")


def validate(inv) -> None:
    r = inv.review_reasons
    for name in ("invoice_number", "vendor", "currency", "subtotal", "tax", "total"):
        if getattr(inv, name) in (None, ""):
            r.append(f"{name.replace('_', ' ')} not found")
    if not inv.line_items:
        r.append("no line items found")
    for i, li in enumerate(inv.line_items, 1):
        if None in (li.unit_price, li.amount):
            r.append(f"line {i}: unreadable amount")
        elif abs(li.quantity * li.unit_price - li.amount) > TOLERANCE:
            r.append(f"line {i}: {li.quantity} x {li.unit_price} != {li.amount}")
    if inv.line_items and inv.subtotal is not None and all(li.amount is not None for li in inv.line_items):
        s = sum((li.amount for li in inv.line_items), Decimal("0"))
        if abs(s - inv.subtotal) > TOLERANCE:
            r.append(f"line items sum to {s} but subtotal says {inv.subtotal}")
    if None not in (inv.subtotal, inv.tax, inv.total):
        if abs(inv.subtotal + inv.tax - inv.total) > TOLERANCE:
            r.append(f"subtotal + tax = {inv.subtotal + inv.tax} but total says {inv.total}")
