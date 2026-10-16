"""A payments csomag egységtesztjei – szintetikus számlákkal, csak standard könyvtár."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from payments.holds import HoldClosed, HoldManager  # noqa: E402
from payments.ledger import InsufficientFunds, Ledger  # noqa: E402
from payments.service import CAPTURED, VOIDED, InvalidState, PaymentService  # noqa: E402


class LedgerTests(unittest.TestCase):
    def test_post_moves_money_and_journals(self):
        ledger = Ledger({"a": 500})
        ledger.post("b", "a", 200)
        self.assertEqual((ledger.balance("a"), ledger.balance("b")), (300, 200))
        self.assertEqual(ledger.journal, [("b", "a", 200)])

    def test_insufficient_and_invalid(self):
        ledger = Ledger({"a": 100})
        with self.assertRaises(InsufficientFunds):
            ledger.post("b", "a", 101)
        for bad in (0, -5, 1.5, "10", True):
            with self.subTest(cents=bad):
                with self.assertRaises(ValueError):
                    ledger.post("b", "a", bad)
        self.assertEqual(ledger.balance("a"), 100)


class HoldTests(unittest.TestCase):
    def setUp(self):
        self.holds = HoldManager(Ledger({"c": 1000}))

    def test_place_and_release(self):
        h = self.holds.place("c", 300)
        self.assertEqual(self.holds.available("c"), 700)
        self.holds.release(h)
        self.assertEqual(self.holds.available("c"), 1000)

    def test_capture_closes_hold_once(self):
        h = self.holds.place("c", 300)
        self.assertEqual(self.holds.capture(h, 200), 200)
        self.assertEqual(self.holds.available("c"), 1000)
        with self.assertRaises(HoldClosed):
            self.holds.capture(h, 100)
        with self.assertRaises(HoldClosed):
            self.holds.release(h)

    def test_cannot_hold_more_than_available(self):
        self.holds.place("c", 900)
        with self.assertRaises(InsufficientFunds):
            self.holds.place("c", 200)


class PaymentServiceTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger({"customer": 1000})
        self.svc = PaymentService(self.ledger)

    def test_authorize_and_full_capture(self):
        p = self.svc.authorize("customer", "shop", 300)
        self.assertEqual(self.svc.available("customer"), 700)
        self.svc.capture(p.payment_id, 300)
        self.assertEqual(p.status, CAPTURED)
        self.assertEqual((self.ledger.balance("customer"), self.ledger.balance("shop")), (700, 300))
        self.assertEqual(self.svc.available("customer"), 700)

    def test_partial_capture_releases_rest(self):
        p = self.svc.authorize("customer", "shop", 300)
        self.svc.capture(p.payment_id, 120)
        self.assertEqual(self.ledger.balance("shop"), 120)
        self.assertEqual(self.svc.available("customer"), 880)

    def test_void_releases_hold(self):
        p = self.svc.authorize("customer", "shop", 300)
        self.svc.void(p.payment_id)
        self.assertEqual(p.status, VOIDED)
        self.assertEqual(self.svc.available("customer"), 1000)
        self.assertEqual(self.ledger.balance("shop"), 0)

    def test_state_transitions_enforced(self):
        p = self.svc.authorize("customer", "shop", 300)
        with self.assertRaises(InvalidState):
            self.svc.refund(p.payment_id, 10)
        self.svc.capture(p.payment_id, 300)
        for op in (lambda: self.svc.capture(p.payment_id, 1), lambda: self.svc.void(p.payment_id)):
            with self.assertRaises(InvalidState):
                op()

    def test_refund_limit_and_bookkeeping(self):
        p = self.svc.authorize("customer", "shop", 300)
        self.svc.capture(p.payment_id, 300)
        self.svc.refund(p.payment_id, 100)
        self.assertEqual(p.refunded, 100)
        with self.assertRaises(ValueError):
            self.svc.refund(p.payment_id, 201)
        with self.assertRaises(ValueError):
            self.svc.refund(p.payment_id, 0)

    def test_authorize_beyond_available_rejected(self):
        self.svc.authorize("customer", "shop", 800)
        with self.assertRaises(InsufficientFunds):
            self.svc.authorize("customer", "shop", 300)


if __name__ == "__main__":
    unittest.main()
