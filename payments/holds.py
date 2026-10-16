"""Zárolások (előzetes engedélyezés) kezelése a főkönyv fölött.

- place(account, cents) -> hold_id: a zárolt összeg a szabad egyenlegből (available) levonódik.
- capture(hold_id, cents) -> int: a ténylegesen terhelhető összeg, min(cents, zárolt összeg).
  A zárolás lezárul, a nem terhelt maradék felszabadul. Pénzmozgást nem végez.
- release(hold_id): a zárolás terhelés nélkül lezárul.
Egy zárolás csak egyszer zárható le; ismételt lezárás vagy ismeretlen zárolás: HoldClosed.
"""

import itertools

from payments.ledger import InsufficientFunds, check_cents


class HoldClosed(Exception):
    """A zárolás nem létezik vagy már lezárult."""


class HoldManager:
    def __init__(self, ledger):
        self._ledger = ledger
        self._open = {}
        self._ids = itertools.count(1)

    def available(self, account):
        held = sum(c for acct, c in self._open.values() if acct == account)
        return self._ledger.balance(account) - held

    def place(self, account, cents):
        check_cents(cents)
        if self.available(account) < cents:
            raise InsufficientFunds(account)
        hold_id = f"h{next(self._ids)}"
        self._open[hold_id] = (account, cents)
        return hold_id

    def _close(self, hold_id):
        try:
            return self._open.pop(hold_id)
        except KeyError:
            raise HoldClosed(hold_id) from None

    def capture(self, hold_id, cents):
        check_cents(cents)
        _, held = self._close(hold_id)
        return min(cents, held)

    def release(self, hold_id):
        self._close(hold_id)
