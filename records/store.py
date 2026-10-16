"""Memóriabeli rekordtároló."""

import itertools
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class Record:
    record_id: str
    tenant_id: str
    owner_id: str
    body: str
    shared_with: frozenset = field(default_factory=frozenset)
    archived: bool = False


class RecordStore:
    def __init__(self):
        self._records = {}
        self._ids = itertools.count(1)

    def add(self, tenant_id, owner_id, body, shared_with=()):
        record = Record(f"r{next(self._ids)}", tenant_id, owner_id, body, frozenset(shared_with))
        self._records[record.record_id] = record
        return record

    def get(self, record_id):
        try:
            return self._records[record_id]
        except KeyError:
            raise KeyError(f"nincs ilyen rekord: {record_id}") from None

    def all(self):
        return list(self._records.values())

    def update(self, record_id, **changes):
        record = replace(self.get(record_id), **changes)
        self._records[record_id] = record
        return record
