"""Kedvezményes ár számítása egy rendeléshez.

Szabályok:
- Mennyiségi kedvezmény: legalább 100,00 EUR rendelési érték esetén 5%,
  legalább 500,00 EUR esetén 10%. Több teljesült sáv esetén a legmagasabb küszöbé érvényes.
- Kupon: "WELCOME10" 10% kedvezményt ad, legalább 50,00 EUR rendelési értéktől.
  Ismeretlen kupon esetén ValueError.
- A kedvezmények egymás után alkalmazandók (először a mennyiségi, majd a kupon).
- Az eredmény 2 tizedesjegyre kerekítve (ROUND_HALF_UP).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")

VOLUME_TIERS = (
    (Decimal("100.00"), Decimal("0.05")),
    (Decimal("500.00"), Decimal("0.10")),
)

COUPONS = {
    "WELCOME10": {"rate": Decimal("0.10"), "min_subtotal": Decimal("50.00")},
}


def _to_decimal(value):
    if isinstance(value, bool):
        raise ValueError("érvénytelen rendelési érték")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("érvénytelen rendelési érték") from None
    if not amount.is_finite():
        raise ValueError("érvénytelen rendelési érték")
    if amount < 0:
        raise ValueError("a rendelési érték nem lehet negatív")
    return amount


def volume_discount_rate(subtotal):
    """A rendelési értékhez tartozó mennyiségi kedvezmény aránya (a legmagasabb teljesült sáv)."""
    subtotal = _to_decimal(subtotal)
    rate = Decimal("0")
    best_threshold = None
    for threshold, tier_rate in VOLUME_TIERS:
        if subtotal >= threshold and (best_threshold is None or threshold > best_threshold):
            best_threshold, rate = threshold, tier_rate
    return rate


def coupon_rate(code, subtotal):
    """A kupon kedvezményaránya; ha a feltétel nem teljesül, 0."""
    if code is None:
        return Decimal("0")
    if not isinstance(code, str):
        raise ValueError("a kuponkód csak szöveg lehet")
    coupon = COUPONS.get(code.strip().upper())
    if coupon is None:
        raise ValueError(f"ismeretlen kupon: {code}")
    if _to_decimal(subtotal) < coupon["min_subtotal"]:
        return Decimal("0")
    return coupon["rate"]


def final_price(subtotal, coupon_code=None):
    """Fizetendő összeg a kedvezmények után, 2 tizedesjegyre kerekítve."""
    subtotal = _to_decimal(subtotal)
    price = subtotal * (1 - volume_discount_rate(subtotal))
    price = price * (1 - coupon_rate(coupon_code, subtotal))
    return price.quantize(CENT, rounding=ROUND_HALF_UP)


if __name__ == "__main__":
    for amount in ("40", "250", "1000"):
        print(amount, "->", final_price(amount, "WELCOME10"))
