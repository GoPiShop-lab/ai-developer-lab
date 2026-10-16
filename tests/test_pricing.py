"""A shop.pricing modul egységtesztjei – csak standard könyvtár."""

import pathlib
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from shop import pricing  # noqa: E402


class VolumeDiscountTests(unittest.TestCase):
    def test_small_order_has_no_discount(self):
        self.assertEqual(pricing.volume_discount_rate("0"), Decimal("0"))
        self.assertEqual(pricing.volume_discount_rate("49.99"), Decimal("0"))

    def test_mid_range_order(self):
        self.assertEqual(pricing.volume_discount_rate("250.00"), Decimal("0.05"))

    def test_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            pricing.volume_discount_rate("-1")


class CouponTests(unittest.TestCase):
    def test_no_coupon(self):
        self.assertEqual(pricing.coupon_rate(None, "80"), Decimal("0"))

    def test_coupon_case_and_whitespace_insensitive(self):
        self.assertEqual(pricing.coupon_rate(" welcome10 ", "80"), Decimal("0.10"))

    def test_coupon_minimum_order(self):
        self.assertEqual(pricing.coupon_rate("WELCOME10", "49.99"), Decimal("0"))
        self.assertEqual(pricing.coupon_rate("WELCOME10", "50.00"), Decimal("0.10"))

    def test_unknown_coupon_rejected(self):
        with self.assertRaises(ValueError):
            pricing.coupon_rate("FREE100", "80")


class FinalPriceTests(unittest.TestCase):
    def test_no_discounts(self):
        self.assertEqual(pricing.final_price("40"), Decimal("40.00"))

    def test_coupon_only(self):
        self.assertEqual(pricing.final_price("80", "WELCOME10"), Decimal("72.00"))

    def test_volume_and_coupon_applied_in_sequence(self):
        # 250 * 0.95 = 237.50; * 0.90 = 213.75
        self.assertEqual(pricing.final_price("250", "WELCOME10"), Decimal("213.75"))

    def test_rounding_half_up(self):
        # 60.05 * 0.90 = 54.045 -> 54.05
        self.assertEqual(pricing.final_price("60.05", "WELCOME10"), Decimal("54.05"))


if __name__ == "__main__":
    unittest.main()
