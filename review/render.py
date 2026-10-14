"""PR-komment előállítása. A modell kimenete is megbízhatatlan: minden mező semlegesítve."""

import re

from review import config, schema
from review.redact import redact

ZWSP = "​"
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SEVERITY_LABEL = {"KRITIKUS": "🔴 KRITIKUS", "MAGAS": "🟠 MAGAS", "KOZEPES": "🟡 KÖZEPES",
                  "ALACSONY": "🔵 ALACSONY", "INFO": "⚪ INFO"}
CATEGORY_LABEL = {"kodhiba": "kódhiba", "biztonsag": "biztonság", "logika": "logika",
                  "tesztelhetoseg": "tesztelhetőség", "egyeb": "egyéb"}
DISCLAIMER = ("_Automatikus AI-vélemény (Codex-szerep). Nem jóváhagyás, nem elutasítás; "
              "a PR-ről kizárólag a tulajdonos dönt._")


def sanitize(text, limit=config.MAX_FIELD_CHARS):
    text = redact(text)
    text = _CTRL.sub("", text)
    text = text.replace("@", "@" + ZWSP)          # nincs @-említés -> nincs bot-indítás, nincs értesítés
    text = text.replace("<", "&lt;").replace(">", "&gt;")  # nincs HTML / rejtett komment
    text = text.replace("](", "]" + ZWSP + "(")   # nincs markdown-link / kép
    text = text.replace("![", "!" + ZWSP + "[")
    text = re.sub(r"(?i)\b(https?|javascript|data):", lambda m: m.group(1) + ZWSP + ":", text)
    text = text.replace("```", "'''")
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _header(meta, model, usage, cost):
    return (f"### 🤖 Codex-ellenőrzés – PR #{int(meta['pr'])}\n"
            f"Commit: `{meta['head_sha'][:12]}` · Modell: `{model}` · "
            f"Token: {usage.get('input_tokens', 0)} be / {usage.get('output_tokens', 0)} ki · "
            f"Becsült költség: {cost:.4f} USD\n\n")


def render_ok(review_obj, meta, model, usage, cost):
    ok, why = schema.validate(review_obj)
    if not ok:
        raise ValueError(f"SCHEMA_INVALID {why}")
    order = {s: i for i, s in enumerate(schema.SEVERITIES)}
    items = sorted(review_obj["megallapitasok"], key=lambda f: (order[f["sulyossag"]], f["fajl"], f["sor"] or 0))
    out = [_header(meta, model, usage, cost), "**Összefoglaló:** " + sanitize(review_obj["osszefoglalo"]) + "\n"]
    if not items:
        out.append("\nNincs érdemi megállapítás.\n")
    for i, f in enumerate(items, 1):
        loc = sanitize(f["fajl"], 200).replace("`", "'") + (f":{f['sor']}" if f["sor"] else "")
        out.append(
            f"\n**{i}. {SEVERITY_LABEL[f['sulyossag']]} · {CATEGORY_LABEL[f['kategoria']]} · `{loc}`**\n"
            f"{sanitize(f['cim'], 200)}\n\n"
            f"- Indoklás: {sanitize(f['indoklas'])}\n"
            f"- Javaslat: {sanitize(f['javaslat'])}\n"
        )
    out.append("\n" + DISCLAIMER + "\n")
    return "".join(out)


def render_error(meta, kind, detail=""):
    return (f"### 🤖 Codex-ellenőrzés – PR #{int(meta['pr'])}\n"
            f"Commit: `{meta['head_sha'][:12]}`\n\n"
            f"⚠️ Az automatikus ellenőrzés **nem készült el**: `{sanitize(kind, 80)}`"
            + (f" ({sanitize(detail, 200)})" if detail else "") + ".\n"
            "A modell válaszából semmi nem került a kommentbe.\n\n" + DISCLAIMER + "\n")


def render_stale(meta, current_sha):
    return (f"### 🤖 Codex-ellenőrzés – PR #{int(meta['pr'])}\n"
            f"⚠️ **Elavult ellenőrzés, nem publikálva.** Az ellenőrzött commit `{meta['head_sha'][:12]}`, "
            f"a PR jelenlegi feje `{str(current_sha)[:12]}`. Indítsd újra az ellenőrzést az új commitra.\n\n"
            + DISCLAIMER + "\n")
