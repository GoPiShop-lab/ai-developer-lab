"""A modell válaszának JSON-sémája és saját (függőség nélküli) ellenőrzése."""

from review import config

SEVERITIES = ["KRITIKUS", "MAGAS", "KOZEPES", "ALACSONY", "INFO"]
CATEGORIES = ["kodhiba", "biztonsag", "logika", "tesztelhetoseg", "egyeb"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["osszefoglalo", "megallapitasok"],
    "properties": {
        "osszefoglalo": {"type": "string"},
        "megallapitasok": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["sulyossag", "kategoria", "fajl", "sor", "cim", "indoklas", "javaslat"],
                "properties": {
                    "sulyossag": {"type": "string", "enum": SEVERITIES},
                    "kategoria": {"type": "string", "enum": CATEGORIES},
                    "fajl": {"type": "string"},
                    "sor": {"type": ["integer", "null"]},
                    "cim": {"type": "string"},
                    "indoklas": {"type": "string"},
                    "javaslat": {"type": "string"},
                },
            },
        },
    },
}

_FINDING_KEYS = set(SCHEMA["properties"]["megallapitasok"]["items"]["required"])


def validate(obj):
    """Visszaad: (True, None) vagy (False, ok). Szigorú: plusz mező, rossz típus, rossz enum = hiba."""
    if not isinstance(obj, dict) or set(obj) != {"osszefoglalo", "megallapitasok"}:
        return False, "TOP_LEVEL_KEYS"
    if not isinstance(obj["osszefoglalo"], str):
        return False, "SUMMARY_TYPE"
    items = obj["megallapitasok"]
    if not isinstance(items, list) or len(items) > config.MAX_FINDINGS:
        return False, "FINDINGS_TYPE_OR_COUNT"
    for i, f in enumerate(items):
        if not isinstance(f, dict) or set(f) != _FINDING_KEYS:
            return False, f"FINDING_{i}_KEYS"
        if f["sulyossag"] not in SEVERITIES:
            return False, f"FINDING_{i}_SEVERITY"
        if f["kategoria"] not in CATEGORIES:
            return False, f"FINDING_{i}_CATEGORY"
        for k in ("fajl", "cim", "indoklas", "javaslat"):
            if not isinstance(f[k], str):
                return False, f"FINDING_{i}_{k.upper()}_TYPE"
        if f["sor"] is not None and (not isinstance(f["sor"], int) or isinstance(f["sor"], bool) or f["sor"] < 0):
            return False, f"FINDING_{i}_LINE"
    return True, None
