"""A shop.pricing modul egységtesztjei – csak standard könyvtár."""

import pathlib
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from shop import pricing  # noqa: E402

# rendelési érték, mennyiségi arány, végösszeg kupon nélkül, végösszeg WELCOME10 kuponnal
THRESHOLD_CASES = (
    ("99.99", "0", "99.99", "89.99"),        # 99.99 * 0.90 = 89.991
    ("100.00", "0.05", "95.00", "85.50"),
    ("499.99", "0.05", "474.99", "427.49"),  # 474.9905; * 0.90 = 427.49145
    ("500.00", "0.10", "450.00", "405.00"),
    ("1000.00", "0.10", "900.00", "810.00"),
)


class VolumeDiscountTests(unittest.TestCase):
    def test_small_order_has_no_discount(self):
        self.assertEqual(pricing.volume_discount_rate("0"), Decimal("0"))
        self.assertEqual(pricing.volume_discount_rate("49.99"), Decimal("0"))

    def test_threshold_rates(self):
        for amount, rate, _, _ in THRESHOLD_CASES:
            with self.subTest(amount=amount):
                self.assertEqual(pricing.volume_discount_rate(amount), Decimal(rate))

    def test_highest_reached_tier_wins_regardless_of_table_order(self):
        reversed_tiers = tuple(reversed(pricing.VOLUME_TIERS))
        original = pricing.VOLUME_TIERS
        try:
            pricing.VOLUME_TIERS = reversed_tiers
            self.assertEqual(pricing.volume_discount_rate("1000.00"), Decimal("0.10"))
            self.assertEqual(pricing.volume_discount_rate("100.00"), Decimal("0.05"))
        finally:
            pricing.VOLUME_TIERS = original

    def test_invalid_amounts_rejected(self):
        for bad in ("-1", "-0.01", "abc", "", "NaN", "Infinity", True):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    pricing.volume_discount_rate(bad)


class CouponTests(unittest.TestCase):
    def test_no_coupon(self):
        self.assertEqual(pricing.coupon_rate(None, "80"), Decimal("0"))

    def test_coupon_case_and_whitespace_insensitive(self):
        self.assertEqual(pricing.coupon_rate(" welcome10 ", "80"), Decimal("0.10"))

    def test_coupon_minimum_order(self):
        self.assertEqual(pricing.coupon_rate("WELCOME10", "49.99"), Decimal("0"))
        self.assertEqual(pricing.coupon_rate("WELCOME10", "50.00"), Decimal("0.10"))

    def test_unknown_or_non_text_coupon_rejected(self):
        for bad in ("FREE100", 10):
            with self.subTest(code=bad):
                with self.assertRaises(ValueError):
                    pricing.coupon_rate(bad, "80")


class FinalPriceTests(unittest.TestCase):
    def test_threshold_final_prices_without_and_with_coupon(self):
        for amount, _, plain, with_coupon in THRESHOLD_CASES:
            with self.subTest(amount=amount):
                self.assertEqual(pricing.final_price(amount), Decimal(plain))
                self.assertEqual(pricing.final_price(amount, "WELCOME10"), Decimal(with_coupon))

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
