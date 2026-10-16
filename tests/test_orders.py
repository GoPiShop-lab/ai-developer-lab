"""Az orders csomag egységtesztjei – csak standard könyvtár."""

import pathlib
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from orders import catalog  # noqa: E402
from orders.checkout import SHIPPING_FEE, checkout  # noqa: E402
from orders.inventory import Inventory, OutOfStock  # noqa: E402


class CatalogTests(unittest.TestCase):
    def test_known_and_unknown_sku(self):
        self.assertEqual(catalog.unit_price("BOOK-001"), Decimal("20.00"))
        self.assertEqual(catalog.skus(), ["BOOK-001", "LAMP-003", "MUG-002"])
        with self.assertRaises(ValueError):
            catalog.unit_price("NOPE-999")


class InventoryTests(unittest.TestCase):
    def test_reserve_and_release(self):
        inv = Inventory({"BOOK-001": 5})
        inv.reserve("BOOK-001", 2)
        self.assertEqual(inv.available("BOOK-001"), 3)
        inv.release("BOOK-001", 2)
        self.assertEqual(inv.available("BOOK-001"), 5)

    def test_insufficient_stock_leaves_item_unchanged(self):
        inv = Inventory({"BOOK-001": 1})
        with self.assertRaises(OutOfStock):
            inv.reserve("BOOK-001", 2)
        self.assertEqual(inv.available("BOOK-001"), 1)
        with self.assertRaises(OutOfStock):
            inv.reserve("UNKNOWN", 1)

    def test_invalid_quantities(self):
        inv = Inventory({"BOOK-001": 1})
        for bad in (0, -1, 1.5, "1", True):
            with self.subTest(qty=bad):
                with self.assertRaises(ValueError):
                    inv.reserve("BOOK-001", bad)
        with self.assertRaises(ValueError):
            Inventory({"BOOK-001": -1})


class CheckoutTests(unittest.TestCase):
    def test_successful_checkout_reserves_stock(self):
        inv = Inventory({"BOOK-001": 5, "MUG-002": 5})
        checkout([("BOOK-001", 1), ("MUG-002", 2)], inv)
        self.assertEqual(inv.available("BOOK-001"), 4)
        self.assertEqual(inv.available("MUG-002"), 3)

    def test_small_order_pays_shipping(self):
        receipt = checkout([("MUG-002", 1)], Inventory({"MUG-002": 1}))
        self.assertEqual(receipt.shipping, SHIPPING_FEE)

    def test_single_line_out_of_stock(self):
        inv = Inventory({"LAMP-003": 1})
        with self.assertRaises(OutOfStock):
            checkout([("LAMP-003", 2)], inv)
        self.assertEqual(inv.available("LAMP-003"), 1)

    def test_invalid_input_rejected_before_any_reservation(self):
        inv = Inventory({"BOOK-001": 5})
        for lines in ([], [("BOOK-001", 0)], [("BOOK-001", 1), ("NOPE-999", 1)]):
            with self.subTest(lines=lines):
                with self.assertRaises(ValueError):
                    checkout(lines, inv)
        self.assertEqual(inv.available("BOOK-001"), 5)


if __name__ == "__main__":
    unittest.main()
