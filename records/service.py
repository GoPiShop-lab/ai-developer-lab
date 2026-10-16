"""Rekordszolgáltatás: minden művelet a hívó felhasználó nevében, a records.auth szabályai szerint."""

from records import auth
from records.auth import PermissionDenied


class RecordService:
    def __init__(self, store):
        self._store = store

    def create(self, user, body, shared_with=()):
        if not auth.has_role(user, auth.EDITOR):
            raise PermissionDenied("rekordot legalább EDITOR hozhat létre")
        return self._store.add(user.tenant_id, user.user_id, body, shared_with)

    def get_record(self, user, record_id):
        record = self._store.get(record_id)
        if not auth.has_tenant_access(user, record.tenant_id):
            raise PermissionDenied(record_id)
        return record

    def list_records(self, user):
        return [r for r in self._store.all() if auth.can_read(user, r)]

    def update_body(self, user, record_id, body):
        record = self._store.get(record_id)
        if not auth.can_edit(user, record):
            raise PermissionDenied(record_id)
        return self._store.update(record_id, body=body)

    def archive(self, user, record_id):
        record = self._store.get(record_id)
        if not (auth.same_tenant(user, record) and auth.has_role(user, auth.EDITOR)):
            raise PermissionDenied(record_id)
        return self._store.update(record_id, archived=True)
