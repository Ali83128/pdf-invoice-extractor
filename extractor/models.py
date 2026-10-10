from dataclasses import dataclass, field, asdict
from decimal import Decimal
from typing import Optional


@dataclass
class LineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class Invoice:
    source_file: str
    layout: str = "unknown"
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    invoice_date: Optional[str] = None  # ISO 8601
    currency: Optional[str] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    line_items: list = field(default_factory=list)
    review_reasons: list = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.review_reasons)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["needs_review"] = self.needs_review
        return _jsonable(d)


def _jsonable(o):
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_jsonable(v) for v in o]
    return o
