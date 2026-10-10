"""Generate fictional sample invoices (3 vendor layouts) plus a ground-truth file."""
import json
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
CENT = Decimal("0.01")
FOOTER = "Sample document for testing - all companies and people are fictional."

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def q(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


def us(x):
    return f"{x:,.2f}"


def eu(x):
    s = f"{x:,.2f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def build_items(rng, catalog, n):
    picks = rng.sample(catalog, n)
    items = []
    for desc, lo, hi in picks:
        qty = rng.randint(1, 12)
        price = q(rng.randint(lo * 100, hi * 100) / 100)
        items.append({"description": desc, "quantity": qty, "unit_price": price,
                      "amount": q(price * qty)})
    return items


def totals(items, rate):
    sub = sum((i["amount"] for i in items), Decimal("0"))
    tax = q(sub * Decimal(rate))
    return q(sub), tax, q(sub + tax)


def footer(c):
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.grey)
    c.drawString(20 * mm, 12 * mm, FOOTER)
    c.setFillColor(colors.black)


NW_CATALOG = [("A4 copy paper, 80gsm (box of 5 reams)", 28, 42), ("Black toner cartridge HL-2350", 55, 89),
              ("Ergonomic mesh office chair", 140, 260), ("Whiteboard markers, assorted (pack of 12)", 9, 16),
              ("Desk organiser, bamboo", 18, 35), ("USB-C docking station", 95, 160),
              ("Stapler, heavy duty", 22, 40), ("Document shredder, cross-cut", 120, 210),
              ("Sticky notes 76x76 (pack of 24)", 11, 19), ("LED desk lamp", 30, 58)]

BW_CATALOG = [("Pallet storage (per week)", 8, 15), ("Inbound handling per pallet", 6, 12),
              ("Pick and pack per order", 2, 5), ("Express courier DE domestic", 9, 18),
              ("Stretch wrapping per pallet", 3, 7), ("Customs documentation", 35, 70),
              ("Returns processing per item", 2, 6), ("Labelling service per carton", 1, 3)]

KS_CATALOG = [("Logo design concepts", 120, 260), ("Brand style guide", 300, 650),
              ("Social media templates", 40, 90), ("Website hero illustration", 180, 380),
              ("Business card design", 60, 120), ("Photo retouching per image", 8, 20),
              ("Packaging mockup", 90, 200), ("Revision round", 35, 70)]


def layout_northwind(path, n, rng, d):
    items = build_items(rng, NW_CATALOG, rng.randint(3, 6))
    sub, tax, total = totals(items, "0.0825")
    inv = f"NW-{d.year}-{rng.randint(1000, 9999)}"
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, h - 25 * mm, "Northwind Office Supply Co.")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 31 * mm, "418 Harbor Lane, Springfield, OR 97477")
    c.drawString(20 * mm, h - 36 * mm, "accounts@northwind-supply.example")
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(w - 20 * mm, h - 25 * mm, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 20 * mm, h - 33 * mm, f"Invoice #: {inv}")
    c.drawRightString(w - 20 * mm, h - 39 * mm, f"Date: {d.strftime('%m/%d/%Y')}")
    c.drawRightString(w - 20 * mm, h - 45 * mm, "Terms: Net 30")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, h - 55 * mm, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 61 * mm, rng.choice(["Maple Street Dental", "Orchard Hill Accounting",
                                                  "Bluefin Marketing LLC", "Cedar Point Realty"]))
    data = [["Description", "Qty", "Unit Price", "Amount"]]
    for i in items:
        data.append([i["description"], str(i["quantity"]), f"${us(i['unit_price'])}", f"${us(i['amount'])}"])
    t = Table(data, colWidths=[95 * mm, 15 * mm, 30 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa4b5")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    tw, th = t.wrapOn(c, w, h)
    y = h - 72 * mm - th
    t.drawOn(c, 20 * mm, y)
    c.setFont("Helvetica", 10)
    y -= 10 * mm
    for label, val, bold in [("Subtotal", sub, False), ("Sales Tax (8.25%)", tax, False), ("Total", total, True)]:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        c.drawRightString(w - 55 * mm, y, label)
        c.drawRightString(w - 20 * mm, y, f"${us(val)}")
        y -= 6 * mm
    footer(c)
    c.save()
    return dict(invoice_number=inv, vendor="Northwind Office Supply Co.", invoice_date=d.isoformat(),
                currency="USD", subtotal=sub, tax=tax, total=total, line_items=items)


def layout_brightwater(path, n, rng, d):
    items = build_items(rng, BW_CATALOG, rng.randint(3, 5))
    sub, tax, total = totals(items, "0.19")
    inv = f"BW/{d.strftime('%y')}/{rng.randint(10, 999):04d}"
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFillColor(colors.HexColor("#0b6e69"))
    c.rect(0, h - 30 * mm, w, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, h - 17 * mm, "Brightwater Logistics GmbH")
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, h - 23 * mm, "Hafenstrasse 12, 20457 Hamburg - VAT ID DE000000000")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 42 * mm, f"Invoice No. {inv}")
    c.drawString(20 * mm, h - 48 * mm, f"Invoice date {d.strftime('%d.%m.%Y')}")
    c.drawString(20 * mm, h - 54 * mm, f"Customer {rng.choice(['Lindqvist Home AB', 'Ferro Bikes S.r.l.', 'Atelier Mousse SARL'])}")
    y = h - 70 * mm
    c.setFont("Helvetica-Bold", 9)
    cols = [20 * mm, 120 * mm, 145 * mm, 190 * mm]
    c.drawString(cols[0], y, "Service")
    c.drawRightString(cols[1] + 10 * mm, y, "Qty")
    c.drawRightString(cols[2] + 15 * mm, y, "Unit EUR")
    c.drawRightString(cols[3], y, "Line EUR")
    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)
    c.setFont("Helvetica", 9)
    for i in items:
        y -= 7 * mm
        c.drawString(cols[0], y, i["description"])
        c.drawRightString(cols[1] + 10 * mm, y, str(i["quantity"]))
        c.drawRightString(cols[2] + 15 * mm, y, eu(i["unit_price"]))
        c.drawRightString(cols[3], y, eu(i["amount"]))
    c.line(20 * mm, y - 3 * mm, 190 * mm, y - 3 * mm)
    y -= 11 * mm
    for label, val in [("Net amount", sub), ("VAT 19%", tax), ("Amount due", total)]:
        c.setFont("Helvetica-Bold" if label == "Amount due" else "Helvetica", 10)
        c.drawString(130 * mm, y, label)
        c.drawRightString(190 * mm, y, f"{eu(val)} EUR")
        y -= 6 * mm
    footer(c)
    c.save()
    return dict(invoice_number=inv, vendor="Brightwater Logistics GmbH", invoice_date=d.isoformat(),
                currency="EUR", subtotal=sub, tax=tax, total=total, line_items=items)


def layout_kestrel(path, n, rng, d, break_math=False):
    items = build_items(rng, KS_CATALOG, rng.randint(2, 5))
    sub, tax, total = totals(items, "0.20")
    printed_sub = sub
    if break_math:
        # the vendor typed a subtotal that ignores the last line: the extractor must flag it
        printed_sub = q(sub - items[-1]["amount"])
    inv = f"KS-{rng.randint(1000, 1999)}"
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFont("Times-Bold", 24)
    c.drawString(20 * mm, h - 28 * mm, "Kestrel Studio Ltd")
    c.setFont("Times-Roman", 10)
    c.drawString(20 * mm, h - 35 * mm, "Design & illustration - 7 Weavers Yard, Leeds LS1 4AP")
    c.drawString(20 * mm, h - 48 * mm, f"Ref: {inv}")
    c.drawString(20 * mm, h - 54 * mm, f"Issued: {d.day} {MONTHS[d.month - 1]} {d.year}")
    c.drawString(20 * mm, h - 60 * mm, f"Client: {rng.choice(['Hollow Oak Coffee', 'Pennant Yoga', 'Marlow & Finch'])}")
    y = h - 75 * mm
    c.setFont("Times-Roman", 11)
    for i in items:
        c.drawString(20 * mm, y, f"{i['quantity']} x {i['description']} @ GBP {us(i['unit_price'])}")
        c.drawRightString(190 * mm, y, f"GBP {us(i['amount'])}")
        y -= 7 * mm
    y -= 6 * mm
    for label, val in [("Subtotal", printed_sub), ("VAT (20%)", tax), ("Total due", total)]:
        c.setFont("Times-Bold" if label == "Total due" else "Times-Roman", 11)
        c.drawString(120 * mm, y, label)
        c.drawRightString(190 * mm, y, f"GBP {us(val)}")
        y -= 7 * mm
    footer(c)
    c.save()
    return dict(invoice_number=inv, vendor="Kestrel Studio Ltd", invoice_date=d.isoformat(),
                currency="GBP", subtotal=printed_sub, tax=tax, total=total, line_items=items,
                expected_review=break_math)


def main():
    OUT.mkdir(exist_ok=True)
    rng = random.Random(2026)
    truth = {}
    start = date(2026, 1, 5)
    layouts = [("northwind", layout_northwind), ("brightwater", layout_brightwater), ("kestrel", layout_kestrel)]
    for n in range(12):
        name, fn = layouts[n % 3]
        d = start + timedelta(days=rng.randint(0, 270))
        fname = f"{n + 1:02d}_{name}.pdf"
        kwargs = {"break_math": True} if n == 11 else {}
        rec = fn(OUT / fname, n, rng, d, **kwargs)
        rec.setdefault("expected_review", False)
        truth[fname] = rec
    def enc(o):
        if isinstance(o, Decimal):
            return str(o)
        raise TypeError
    (OUT / "ground_truth.json").write_text(json.dumps(truth, indent=2, default=enc))
    print(f"wrote {len(truth)} sample invoices to {OUT}")


if __name__ == "__main__":
    main()
