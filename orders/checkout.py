"""Pénztár: rendelés véglegesítése a katalógus és a készlet alapján.

Szabályok:
- Az áruérték a katalógus egységárainak (catalog.unit_price) és a darabszámoknak a szorzatösszege.
- Szállítási díj: 4,90 EUR bruttó; legalább 50,00 EUR bruttó áruértéktől ingyenes.
- A végösszeg bruttó (áruérték + szállítás). A vat_included a végösszegben foglalt ÁFA
  (catalog.VAT_RATE szerint).
- Minden vagy semmi: ha bármelyik tétel nem foglalható le, a rendelés OutOfStock kivétellel
  elutasul, és a készlet a hívás előtti állapotban marad.
- Minden összeg 2 tizedesjegyre kerekítve (ROUND_HALF_UP).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from orders import catalog
from orders.inventory import _check_qty

CENT = Decimal("0.01")
SHIPPING_FEE = Decimal("4.90")
FREE_SHIPPING_FROM = Decimal("50.00")


@dataclass(frozen=True)
class Receipt:
    goods: Decimal
    shipping: Decimal
    total: Decimal
    vat_included: Decimal


def _cents(amount):
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def checkout(lines, inventory):
    """lines: (cikkszám, darabszám) párok listája. Siker esetén Receipt, a készlet lefoglalva."""
    if not lines:
        raise ValueError("üres kosár")
    for sku, qty in lines:
        _check_qty(qty)
        catalog.unit_price(sku)

    for sku, qty in lines:
        inventory.reserve(sku, qty)

    net = sum((catalog.unit_price(sku) * qty for sku, qty in lines), Decimal("0"))
    goods = _cents(net * (1 + catalog.VAT_RATE))
    shipping = Decimal("0.00") if goods >= FREE_SHIPPING_FROM else SHIPPING_FEE
    total = goods + shipping
    vat_included = _cents(total - total / (1 + catalog.VAT_RATE))
    return Receipt(goods=goods, shipping=shipping, total=total, vat_included=vat_included)
