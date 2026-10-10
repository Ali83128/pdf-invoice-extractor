"""Layout detection, per-layout rules and a generic fallback."""
import re
from decimal import Decimal
from pathlib import Path

import pdfplumber

from .models import Invoice, LineItem
from .numbers import AmbiguousDate, detect_currency, normalise_date, parse_money
from .validate import validate

DATE_TOKEN = r"(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2} [A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{1,2}, \d{4})"


def read_pdf(path: Path):
    with pdfplumber.open(path) as pdf:
        texts, tables = [], []
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            tables.extend(page.extract_tables() or [])
    return "\n".join(texts), tables


def _find(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _set_date(inv, raw, hint):
    if not raw:
        inv.review_reasons.append("invoice date not found")
        return
    try:
        inv.invoice_date = normalise_date(raw, hint)
    except AmbiguousDate as e:
        inv.review_reasons.append(f"ambiguous date: {e}")
    except ValueError as e:
        inv.review_reasons.append(str(e))


# ---------- layout rules ----------

def parse_northwind(inv, text, tables):
    inv.layout = "northwind"
    inv.vendor = "Northwind Office Supply Co."
    inv.currency = "USD"
    inv.invoice_number = _find(r"Invoice #:\s*(\S+)", text)
    _set_date(inv, _find(r"^Date:\s*" + DATE_TOKEN, text), "us")
    for table in tables:
        header = [c.strip().lower() if c else "" for c in table[0]]
        if header[:1] == ["description"] and "amount" in header:
            for row in table[1:]:
                desc, qty, price, amount = row[:4]
                inv.line_items.append(LineItem(desc.strip(), Decimal(qty), parse_money(price, False),
                                               parse_money(amount, False)))
    inv.subtotal = parse_money(_find(r"^Subtotal\s+(.+)$", text), False)
    inv.tax = parse_money(_find(r"^Sales Tax[^$]*(\$[\d,.]+)$", text), False)
    inv.total = parse_money(_find(r"^Total\s+(\$[\d,.]+)$", text), False)


BW_LINE = re.compile(r"^(?P<desc>.+?)\s+(?P<qty>\d+)\s+(?P<price>\d[\d.]*,\d{2})\s+(?P<amount>\d[\d.]*,\d{2})$")


def parse_brightwater(inv, text, tables):
    inv.layout = "brightwater"
    inv.vendor = "Brightwater Logistics GmbH"
    inv.currency = "EUR"
    inv.invoice_number = _find(r"Invoice No\.\s*(\S+)", text)
    _set_date(inv, _find(r"Invoice date\s+" + DATE_TOKEN, text), "eu")
    for line in text.splitlines():
        m = BW_LINE.match(line.strip())
        if m:
            inv.line_items.append(LineItem(m["desc"], Decimal(m["qty"]), parse_money(m["price"], True),
                                           parse_money(m["amount"], True)))
    inv.subtotal = parse_money(_find(r"^Net amount\s+(.+)$", text), True)
    inv.tax = parse_money(_find(r"^VAT \d+%\s+(.+)$", text), True)
    inv.total = parse_money(_find(r"^Amount due\s+(.+)$", text), True)


KS_LINE = re.compile(r"^(?P<qty>\d+) x (?P<desc>.+?) @ GBP (?P<price>[\d,]+\.\d{2})\s+GBP (?P<amount>[\d,]+\.\d{2})$")


def parse_kestrel(inv, text, tables):
    inv.layout = "kestrel"
    inv.vendor = "Kestrel Studio Ltd"
    inv.currency = "GBP"
    inv.invoice_number = _find(r"^Ref:\s*(\S+)", text)
    _set_date(inv, _find(r"^Issued:\s*" + DATE_TOKEN, text), "eu")
    for line in text.splitlines():
        m = KS_LINE.match(line.strip())
        if m:
            inv.line_items.append(LineItem(m["desc"], Decimal(m["qty"]), parse_money(m["price"], False),
                                           parse_money(m["amount"], False)))
    inv.subtotal = parse_money(_find(r"^Subtotal\s+(.+)$", text), False)
    inv.tax = parse_money(_find(r"^VAT\s*\(\d+%\)\s+(.+)$", text), False)
    inv.total = parse_money(_find(r"^Total due\s+(.+)$", text), False)


# ---------- generic fallback ----------

GENERIC_LINE = re.compile(
    r"^(?P<desc>[A-Za-z].*?)\s+(?P<qty>\d+(?:\.\d+)?)\s+[$€£]?\s?(?P<price>\d[\d.,]*\d)\s+[$€£]?\s?(?P<amount>\d[\d.,]*\d)$")


def parse_generic(inv, text, tables):
    inv.layout = "generic"
    first = next((l.strip() for l in text.splitlines() if l.strip() and l.strip().upper() != "INVOICE"), None)
    inv.vendor = first
    inv.currency = detect_currency(text)
    inv.invoice_number = _find(r"(?:Invoice\s*(?:No\.?|#|Number)|Ref(?:erence)?)\s*[:#]?\s*([A-Z0-9][A-Z0-9/\-]{2,})", text)
    _set_date(inv, _find(r"(?:Invoice\s+)?Date[d:]?\s*:?\s*" + DATE_TOKEN, text), None)
    for line in text.splitlines():
        m = GENERIC_LINE.match(line.strip())
        if m:
            inv.line_items.append(LineItem(m["desc"].strip(), Decimal(m["qty"]), parse_money(m["price"]),
                                           parse_money(m["amount"])))
    inv.subtotal = parse_money(_find(r"^(?:Sub-?total|Net(?: amount)?)\b[^\d]*(.+)$", text))
    inv.tax = parse_money(_find(r"^(?:Tax|VAT|Sales Tax|GST)\b[^\n]*?([$€£]?\s?\d[\d.,]*\d)\s*(?:[A-Z]{3})?$", text))
    inv.total = parse_money(_find(r"^(?:Total(?: due)?|Amount due|Balance due)\b[^\d]*(.+)$", text))
    inv.review_reasons.append("unknown layout: parsed with generic rules, please spot-check")


LAYOUTS = [
    ("Northwind Office Supply", parse_northwind),
    ("Brightwater Logistics", parse_brightwater),
    ("Kestrel Studio", parse_kestrel),
]


def extract_invoice(path) -> Invoice:
    path = Path(path)
    inv = Invoice(source_file=path.name)
    try:
        text, tables = read_pdf(path)
    except Exception as e:  # corrupt or encrypted file
        inv.review_reasons.append(f"could not open PDF: {e.__class__.__name__}")
        return inv
    if len(text.strip()) < 20:
        inv.layout = "no-text"
        inv.review_reasons.append("no text layer (scanned image) - needs the OCR add-on")
        return inv
    for marker, parser in LAYOUTS:
        if marker in text:
            parser(inv, text, tables)
            break
    else:
        parse_generic(inv, text, tables)
    validate(inv)
    return inv
