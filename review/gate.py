"""Futás- és költségkapu. Tiszta függvények: a GitHub futásnaplóból (amit az AI nem írhat) számol.

Szabályok:
- csak a main ágról indított, első próbálkozás (run_attempt == 1) futhat;
- a számlálás a futás-azonosító szerint történik: a saját futásnál korábbi (kisebb id) és a saját futás számít,
  így párhuzamos indításnál is determinisztikus, melyik bukik el;
- minden állapot beszámít (várakozó, futó, megszakított, hibás is) – konzervatív;
- csak az "[live]" futások számítanak a költségkorlátba; a "[dry]" futás nem hív API-t.
"""

import re

from review import config

_PR_RE = re.compile(r"^[1-9][0-9]{0,6}$")


def validate_pr_number(value):
    value = str(value).strip()
    if not _PR_RE.match(value):
        raise ValueError("INVALID_PR_NUMBER")
    return int(value)


def run_name(pr_number, dry_run):
    return f"codex-review PR #{int(pr_number)} [{'dry' if dry_run else 'live'}]"


def _is_live(run):
    return str(run.get("name", "")).endswith("[live]")


def _is_pr(run, pr_number):
    return str(run.get("name", "")).startswith(f"codex-review PR #{int(pr_number)} ")


def decide(runs, *, my_run_id, pr_number, dry_run, ref, run_attempt, today, month):
    """runs: a workflow futásai (id, name, created_at). today: 'YYYY-MM-DD', month: 'YYYY-MM'."""
    if ref != "refs/heads/main":
        return False, "NOT_FROM_MAIN"
    if str(run_attempt) != "1":
        return False, "RERUN_NOT_ALLOWED"
    worst = config.guaranteed_max_cost_usd()
    if dry_run:
        return True, "DRY_RUN"
    mine = [r for r in runs if int(r["id"]) <= int(my_run_id) and _is_live(r)]
    if not any(int(r["id"]) == int(my_run_id) for r in mine):
        return False, "OWN_RUN_NOT_FOUND"
    per_pr = sum(1 for r in mine if _is_pr(r, pr_number))
    per_day = sum(1 for r in mine if str(r.get("created_at", "")).startswith(today))
    per_month = sum(1 for r in mine if str(r.get("created_at", "")).startswith(month))
    if per_pr > config.MAX_LIVE_RUNS_PER_PR:
        return False, f"PR_LIMIT {per_pr}>{config.MAX_LIVE_RUNS_PER_PR}"
    if per_day > config.MAX_LIVE_RUNS_PER_DAY:
        return False, f"DAY_LIMIT {per_day}>{config.MAX_LIVE_RUNS_PER_DAY}"
    if per_month > config.MAX_LIVE_RUNS_PER_MONTH:
        return False, f"MONTH_LIMIT {per_month}>{config.MAX_LIVE_RUNS_PER_MONTH}"
    if per_month * worst > config.MONTHLY_BUDGET_USD:
        return False, f"BUDGET_LIMIT {per_month * worst:.2f}>{config.MONTHLY_BUDGET_USD:.2f}"
    return True, f"OK pr={per_pr} day={per_day} month={per_month} worst_month_usd={per_month * worst:.2f}"
