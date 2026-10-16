"""Raktárkészlet nyilvántartása memóriában."""


class OutOfStock(Exception):
    """A kért mennyiség nem áll rendelkezésre."""


def _check_qty(qty):
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError("a mennyiség pozitív egész szám kell legyen")


class Inventory:
    def __init__(self, stock):
        self._stock = {}
        for sku, qty in stock.items():
            if isinstance(qty, bool) or not isinstance(qty, int) or qty < 0:
                raise ValueError(f"érvénytelen készlet: {sku}")
            self._stock[sku] = qty

    def available(self, sku):
        return self._stock.get(sku, 0)

    def reserve(self, sku, qty):
        """Lefoglal qty darabot (csökkenti a készletet). Ha nincs elég, OutOfStock, és nincs változás."""
        _check_qty(qty)
        if self.available(sku) < qty:
            raise OutOfStock(sku)
        self._stock[sku] = self.available(sku) - qty

    def release(self, sku, qty):
        """Visszaad qty darabot a készletbe."""
        _check_qty(qty)
        self._stock[sku] = self.available(sku) + qty
