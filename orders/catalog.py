"""Termékkatalógus.

Az egységárak BRUTTÓ árak EUR-ban, vagyis már tartalmazzák a VAT_RATE szerinti ÁFÁ-t.
"""

from decimal import Decimal

VAT_RATE = Decimal("0.19")

_UNIT_PRICES = {
    "BOOK-001": Decimal("20.00"),
    "MUG-002": Decimal("8.50"),
    "LAMP-003": Decimal("45.00"),
}


def unit_price(sku):
    """Egy termék bruttó egységára. Ismeretlen cikkszám esetén ValueError."""
    try:
        return _UNIT_PRICES[sku]
    except KeyError:
        raise ValueError(f"ismeretlen cikkszám: {sku}") from None


def skus():
    return sorted(_UNIT_PRICES)
