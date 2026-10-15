"""Belépési pont a workflow három jobjához. Adatátadás csak fájlokon keresztül (nincs ${{ }} a shellben).

  prepare : titok nélkül – PR-ellenőrzés, kapu, diff-méret, meta.json + diff.txt
  review  : csak itt van OPENAI_API_KEY – egy API-hívás, result.json (titok nélkül)
  publish : titok nélkül – SHA-ellenőrzés, komment-szöveg előállítása (comment.md)
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

from review import config, gate, prompt, render
from review.openai_client import ApiError, call, extract
from review.redact import redact

DRY_RUN_RESPONSE = {
    "status": "completed",
    "usage": {"input_tokens": 0, "output_tokens": 0},
    "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({
        "osszefoglalo": "DRY RUN: nem történt API-hívás, ez egy rögzített mintaválasz.",
        "megallapitasok": [{
            "sulyossag": "INFO", "kategoria": "egyeb", "fajl": "README.md", "sor": None,
            "cim": "Próbafutás", "indoklas": "A teljes lánc API-költség nélkül lefutott.",
            "javaslat": "Éles ellenőrzéshez dry_run=false és tulajdonosi döntés kell."}]})}]}],
}

BOUND_WARNING = ("> ⚠️ **KÖLTSÉGKORLÁT-FIGYELMEZTETÉS:** a tényleges tokenhasználat meghaladta a garantáltnak "
                 "számolt felső korlátot. További éles futás csak a korlátszámítás felülvizsgálata után.\n\n")


def _write(path, obj):
    pathlib.Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _bool(v):
    return str(v).strip().lower() in ("1", "true", "yes")


def cmd_prepare(a):
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pr_number = gate.validate_pr_number(a.pr_number)
    pr = json.loads(pathlib.Path(a.pr).read_text(encoding="utf-8"))
    runs = [json.loads(line) for line in pathlib.Path(a.runs).read_text(encoding="utf-8").splitlines() if line.strip()]
    now = dt.datetime.now(dt.timezone.utc)
    allowed, reason = gate.decide(runs, my_run_id=a.run_id, pr_number=pr_number, dry_run=_bool(a.dry_run),
                                  ref=a.ref, run_attempt=a.run_attempt,
                                  today=now.strftime("%Y-%m-%d"), month=now.strftime("%Y-%m"))
    if allowed and pr.get("state") != "open":
        allowed, reason = False, "PR_NOT_OPEN"
    if allowed and (pr.get("base") or {}).get("ref") != "main":
        allowed, reason = False, "BASE_NOT_MAIN"
    diff = pathlib.Path(a.diff).read_text(encoding="utf-8", errors="replace")
    diff_bytes = len(diff.encode("utf-8"))
    if allowed and diff_bytes > config.MAX_DIFF_BYTES:
        allowed, reason = False, f"DIFF_TOO_LARGE {diff_bytes}>{config.MAX_DIFF_BYTES}"
    meta = {"pr": pr_number, "head_sha": (pr.get("head") or {}).get("sha", ""), "dry_run": _bool(a.dry_run),
            "allowed": allowed, "reason": reason, "diff_bytes": diff_bytes}
    _write(out / "meta.json", meta)
    (out / "diff.txt").write_text(diff if allowed else "", encoding="utf-8")
    print(f"GATE allowed={allowed} reason={reason} diff_bytes={diff_bytes}")
    return 0


def cmd_review(a):
    inp, out = pathlib.Path(a.inp), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((inp / "meta.json").read_text(encoding="utf-8"))
    model = (a.model or "").strip() or config.DEFAULT_MODEL
    result = {"pr": meta["pr"], "head_sha": meta["head_sha"], "model": model, "dry_run": meta["dry_run"]}
    try:
        if str(a.run_attempt) != "1":
            raise ApiError("RERUN_NOT_ALLOWED")
        if not meta.get("allowed"):
            raise ApiError("GATE_DENIED", None, meta.get("reason", ""))
        diff = (inp / "diff.txt").read_text(encoding="utf-8")
        try:
            payload = prompt.build_request(diff, meta, model)
        except ValueError as e:
            raise ApiError("CONFIG_ERROR", None, str(e)) from None
        size = prompt.request_bytes(payload)
        result["request_bytes"] = size
        result["max_input_tokens"] = config.max_input_tokens(size)
        result["max_cost_usd"] = round(config.guaranteed_max_cost_usd(model, size), 6)
        if meta["dry_run"]:
            response = DRY_RUN_RESPONSE
        else:
            response = call(payload, os.environ.get("OPENAI_API_KEY", ""))
        text, usage, _ = extract(response)
        result["usage"] = usage
        result["cost_usd"] = config.cost_usd(model, usage["input_tokens"], usage["output_tokens"])
        # Utólagos ellenőrzés: ha a tényleges használat a garantáltnak hitt korlát fölött van,
        # a feltevés megdőlt -> hangos jelzés a kommentben, további éles futás csak felülvizsgálat után.
        result["bound_exceeded"] = (int(usage["input_tokens"] or 0) > result["max_input_tokens"]
                                    or int(usage["output_tokens"] or 0) > config.MAX_OUTPUT_TOKENS)
        try:
            obj = json.loads(text)
        except Exception:
            raise ApiError("INVALID_MODEL_JSON") from None
        from review import schema
        ok, why = schema.validate(obj)
        if not ok:
            raise ApiError("INVALID_SCHEMA", None, why)
        result.update(status="ok", review=obj)
    except ApiError as e:
        result.update(status="error", error=e.kind, http_status=e.http_status, detail=e.detail)
    _write(out / "result.json", json.loads(redact(json.dumps(result, ensure_ascii=False))))
    print(f"REVIEW status={result['status']} error={result.get('error')} "
          f"usage={result.get('usage')} cost_usd={result.get('cost_usd')}")
    return 0


def cmd_publish(a):
    meta = json.loads(pathlib.Path(a.meta).read_text(encoding="utf-8"))
    result_path = pathlib.Path(a.result)
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else None
    current = (a.current_sha or "").strip()
    if not current or current != meta["head_sha"]:
        body = render.render_stale(meta, current or "ismeretlen")
    elif result is None:
        body = render.render_error(meta, "NO_RESULT")
    elif result.get("status") != "ok":
        body = render.render_error(meta, result.get("error", "UNKNOWN"), result.get("detail", ""))
    else:
        try:
            body = render.render_ok(result["review"], meta, result["model"], result.get("usage", {}),
                                    result.get("cost_usd", 0.0))
        except Exception as e:
            body = render.render_error(meta, "RENDER_ERROR", type(e).__name__)
    if result and result.get("bound_exceeded") and current == meta["head_sha"]:
        body = BOUND_WARNING + body
    pathlib.Path(a.out).write_text(body, encoding="utf-8")
    print("PUBLISH body_chars=%d stale=%s" % (len(body), current != meta["head_sha"]))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="review")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare")
    for k in ("pr-number", "pr", "diff", "runs", "run-id", "run-attempt", "ref", "dry-run", "out"):
        s.add_argument("--" + k, required=True)
    s = sub.add_parser("review")
    s.add_argument("--in", dest="inp", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--model", default="")
    s.add_argument("--run-attempt", required=True)
    s = sub.add_parser("publish")
    for k in ("meta", "result", "current-sha", "out"):
        s.add_argument("--" + k, required=True)
    a = p.parse_args(argv)
    return {"prepare": cmd_prepare, "review": cmd_review, "publish": cmd_publish}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
