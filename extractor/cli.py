import argparse
import logging
import sys
import time
from pathlib import Path

from .export import write_csv, write_excel, write_json
from .parse import extract_invoice

log = logging.getLogger("extractor")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m extractor",
                                description="Extract invoice data from PDFs into Excel, CSV and JSON.")
    p.add_argument("input", help="a PDF file or a folder of PDFs")
    p.add_argument("--out", default="output", help="output folder (default: output)")
    p.add_argument("--format", nargs="+", choices=["xlsx", "csv", "json"], default=["xlsx", "csv", "json"])
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")

    src = Path(a.input)
    files = sorted(src.glob("*.pdf")) if src.is_dir() else [src]
    if not files:
        log.error("no PDF files found in %s", src)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    invoices = []
    for f in files:
        inv = extract_invoice(f)
        invoices.append(inv)
        status = "REVIEW" if inv.needs_review else "ok"
        log.info("%-6s %-22s %-11s %-14s %s %s", status, f.name, inv.layout, inv.invoice_number or "-",
                 inv.currency or "", inv.total if inv.total is not None else "-")
        for reason in inv.review_reasons:
            log.warning("       %s", reason)

    if "xlsx" in a.format:
        write_excel(invoices, out / "invoices.xlsx")
        log.info("wrote %s", out / "invoices.xlsx")
    if "csv" in a.format:
        write_csv(invoices, out)
        log.info("wrote %s and %s", out / "invoices.csv", out / "line_items.csv")
    if "json" in a.format:
        write_json(invoices, out / "invoices.json")
        log.info("wrote %s", out / "invoices.json")
    ok = sum(not i.needs_review for i in invoices)
    lines = sum(len(i.line_items) for i in invoices)
    log.info("done   %d files, %d ok, %d need review, %d line items, %.1fs",
             len(invoices), ok, len(invoices) - ok, lines, time.perf_counter() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
