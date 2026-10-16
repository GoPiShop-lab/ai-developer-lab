"""Fizetési folyamat: engedélyezés, terhelés, sztornó, visszatérítés.

Szabályok:
- authorize(customer, merchant, cents): zárolás a vevő számláján; állapot AUTHORIZED.
- capture(payment_id, cents): csak AUTHORIZED állapotból. A zárolásból ténylegesen terhelhető
  összeg kerül a vevőtől a kereskedőhöz; ezt a payment.captured rögzíti. Állapot CAPTURED.
- void(payment_id): csak AUTHORIZED állapotból; a zárolás feloldódik. Állapot VOIDED.
- refund(payment_id, cents): csak CAPTURED állapotú fizetésre, akár több részletben.
  A visszatérítések összege nem haladhatja meg a ténylegesen terhelt összeget.
  A visszatérített összeg a kereskedőtől a vevőhöz kerül.
"""

import itertools
from dataclasses import dataclass

from payments.holds import HoldManager
from payments.ledger import check_cents

AUTHORIZED, CAPTURED, VOIDED = "AUTHORIZED", "CAPTURED", "VOIDED"


class InvalidState(Exception):
    """A művelet a fizetés jelenlegi állapotában nem megengedett."""


@dataclass
class Payment:
    payment_id: str
    customer: str
    merchant: str
    authorized: int
    hold_id: str
    status: str = AUTHORIZED
    captured: int = 0
    refunded: int = 0


class PaymentService:
    def __init__(self, ledger):
        self._ledger = ledger
        self._holds = HoldManager(ledger)
        self._payments = {}
        self._ids = itertools.count(1)

    def available(self, account):
        return self._holds.available(account)

    def get(self, payment_id):
        return self._payments[payment_id]

    def _require(self, payment_id, status):
        p = self.get(payment_id)
        if p.status != status:
            raise InvalidState(f"{payment_id}: {p.status}")
        return p

    def authorize(self, customer, merchant, cents):
        hold_id = self._holds.place(customer, cents)
        p = Payment(f"p{next(self._ids)}", customer, merchant, cents, hold_id)
        self._payments[p.payment_id] = p
        return p

    def capture(self, payment_id, cents):
        p = self._require(payment_id, AUTHORIZED)
        charged = self._holds.capture(p.hold_id, cents)
        self._ledger.post(p.merchant, p.customer, charged)
        p.captured = cents
        p.status = CAPTURED
        return p

    def void(self, payment_id):
        p = self._require(payment_id, AUTHORIZED)
        self._holds.release(p.hold_id)
        p.status = VOIDED
        return p

    def refund(self, payment_id, cents):
        check_cents(cents)
        p = self._require(payment_id, CAPTURED)
        if p.refunded + cents > p.captured:
            raise ValueError("a visszatérítés meghaladná a terhelt összeget")
        self._ledger.post(p.merchant, p.customer, cents)
        p.refunded += cents
        return p
