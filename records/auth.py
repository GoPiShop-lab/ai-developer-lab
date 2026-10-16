"""Felhasználók és hozzáférési szabályok.

Szerepkörök (növekvő sorrendben): VIEWER < EDITOR < ADMIN. Egy felhasználó egy tenanthoz tartozik.

Hozzáférési szabályok (a tenanton kívüli rekordhoz soha nincs hozzáférés):
- Olvasás: a rekord tulajdonosa, az a felhasználó, akivel a rekordot megosztották,
  vagy a tenant ADMIN szerepkörű felhasználója.
- Tartalom módosítása: a tulajdonos, ha legalább EDITOR szerepkörű; vagy a tenant ADMIN-ja.
  Archivált rekord nem módosítható.
- Archiválás: kizárólag a tenant ADMIN-ja.
"""

from dataclasses import dataclass

VIEWER = "viewer"
EDITOR = "editor"
ADMIN = "admin"
_RANK = {VIEWER: 1, EDITOR: 2, ADMIN: 3}


class PermissionDenied(Exception):
    """A felhasználónak nincs joga a művelethez."""


@dataclass(frozen=True)
class User:
    user_id: str
    tenant_id: str
    role: str

    def __post_init__(self):
        if self.role not in _RANK:
            raise ValueError(f"ismeretlen szerepkör: {self.role}")


def has_role(user, minimum):
    """Igaz, ha a felhasználó szerepköre legalább a megadott szint."""
    return _RANK[user.role] >= _RANK[minimum]


def same_tenant(user, record):
    return user.tenant_id == record.tenant_id


def has_tenant_access(user, tenant_id):
    """Tagja-e a felhasználó a tenantnak."""
    return user.tenant_id == tenant_id


def can_read(user, record):
    if not same_tenant(user, record):
        return False
    return (record.owner_id == user.user_id
            or user.user_id in record.shared_with
            or has_role(user, ADMIN))


def can_edit(user, record):
    if not same_tenant(user, record) or record.archived:
        return False
    if has_role(user, ADMIN):
        return True
    return record.owner_id == user.user_id and has_role(user, EDITOR)
