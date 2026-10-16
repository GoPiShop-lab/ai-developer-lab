"""Főkönyv: egész centben vezetett számlaegyenlegek, napló.

post(to_account, from_account, cents): a from_account számláról cents összeget könyvel
a to_account számlára. Negatív egyenleg nem megengedett (InsufficientFunds).
"""


class InsufficientFunds(Exception):
    """Nincs elegendő fedezet."""


def check_cents(cents):
    if isinstance(cents, bool) or not isinstance(cents, int) or cents <= 0:
        raise ValueError("az összeg pozitív egész cent kell legyen")


class Ledger:
    def __init__(self, balances):
        self._balances = dict(balances)
        self.journal = []

    def balance(self, account):
        return self._balances.get(account, 0)

    def post(self, to_account, from_account, cents):
        check_cents(cents)
        if self.balance(from_account) < cents:
            raise InsufficientFunds(from_account)
        self._balances[from_account] = self.balance(from_account) - cents
        self._balances[to_account] = self.balance(to_account) + cents
        self.journal.append((to_account, from_account, cents))
