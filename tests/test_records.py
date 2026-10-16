"""A records csomag egységtesztjei – szintetikus adatokkal, csak standard könyvtár."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from records.auth import ADMIN, EDITOR, VIEWER, PermissionDenied, User  # noqa: E402
from records.service import RecordService  # noqa: E402
from records.store import RecordStore  # noqa: E402

ALICE = User("alice", "t1", EDITOR)
BOB = User("bob", "t1", VIEWER)
ADA = User("ada", "t1", ADMIN)
EVE = User("eve", "t2", ADMIN)


class RecordServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = RecordService(RecordStore())
        self.rec = self.svc.create(ALICE, "jegyzet")

    def test_owner_reads_own_record(self):
        self.assertEqual(self.svc.get_record(ALICE, self.rec.record_id).body, "jegyzet")

    def test_admin_reads_tenant_record(self):
        self.assertEqual(self.svc.get_record(ADA, self.rec.record_id).owner_id, "alice")

    def test_other_tenant_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.svc.get_record(EVE, self.rec.record_id)

    def test_list_only_readable_records(self):
        shared = self.svc.create(ALICE, "megosztott", shared_with=["bob"])
        self.assertEqual([r.record_id for r in self.svc.list_records(BOB)], [shared.record_id])
        self.assertEqual(len(self.svc.list_records(ALICE)), 2)
        self.assertEqual(self.svc.list_records(EVE), [])

    def test_viewer_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            self.svc.create(BOB, "x")

    def test_owner_editor_updates_body(self):
        self.assertEqual(self.svc.update_body(ALICE, self.rec.record_id, "új").body, "új")

    def test_viewer_and_other_tenant_cannot_update(self):
        for user in (BOB, EVE):
            with self.subTest(user=user.user_id):
                with self.assertRaises(PermissionDenied):
                    self.svc.update_body(user, self.rec.record_id, "x")

    def test_admin_archives_and_archived_is_read_only(self):
        self.assertTrue(self.svc.archive(ADA, self.rec.record_id).archived)
        for user in (ALICE, ADA):
            with self.subTest(user=user.user_id):
                with self.assertRaises(PermissionDenied):
                    self.svc.update_body(user, self.rec.record_id, "x")

    def test_viewer_and_other_tenant_cannot_archive(self):
        for user in (BOB, EVE):
            with self.subTest(user=user.user_id):
                with self.assertRaises(PermissionDenied):
                    self.svc.archive(user, self.rec.record_id)
        self.assertFalse(self.svc.get_record(ALICE, self.rec.record_id).archived)

    def test_unknown_record_and_role(self):
        with self.assertRaises(KeyError):
            self.svc.get_record(ALICE, "r999")
        with self.assertRaises(ValueError):
            User("x", "t1", "superuser")


if __name__ == "__main__":
    unittest.main()
