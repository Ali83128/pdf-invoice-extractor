"""Compare extracted fields with samples/ground_truth.json and print field-level accuracy."""
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from extractor import extract_invoice  # noqa: E402

FIELDS = ["invoice_number", "vendor", "invoice_date", "currency", "subtotal", "tax", "total"]


def main():
    truth = json.loads((ROOT / "samples" / "ground_truth.json").read_text())
    checked = correct = 0
    flag_ok = 0
    for fname, t in truth.items():
        inv = extract_invoice(ROOT / "samples" / fname)
        misses = []
        for f in FIELDS:
            got, want = getattr(inv, f), t[f]
            if f in ("subtotal", "tax", "total"):
                got, want = got, Decimal(want)
            checked += 1
            if got == want:
                correct += 1
            else:
                misses.append(f"{f}: got {got!r} want {want!r}")
        items_ok = len(inv.line_items) == len(t["line_items"]) and all(
            li.description == w["description"] and li.quantity == w["quantity"]
            and li.unit_price == Decimal(w["unit_price"]) and li.amount == Decimal(w["amount"])
            for li, w in zip(inv.line_items, t["line_items"]))
        checked += 1
        correct += items_ok
        if not items_ok:
            misses.append("line items differ")
        flag_ok += inv.needs_review == t["expected_review"]
        print(f"{fname:22} {'all fields match' if not misses else '; '.join(misses)}"
              f"{'  [flagged for review, as expected]' if inv.needs_review and t['expected_review'] else ''}")
    print(f"\nfield accuracy: {correct}/{checked} ({100 * correct / checked:.1f}%)")
    print(f"review flag correct on {flag_ok}/{len(truth)} files")


if __name__ == "__main__":
    main()
