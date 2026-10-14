"""Rögzített korlátok. Szándékosan nem workflow-bemenetek: futtatáskor nem emelhetők."""

# Hivatalos ár (USD / 1M token), forrás: developers.openai.com/api/docs/pricing,
# ellenőrizve 2026-10-14 (Standard, rövid kontextus). Csak az itt felsorolt modell használható.
MODEL_PRICES_USD_PER_M = {
    "gpt-6.1-sol": {"input": 2.00, "output": 10.00},
}
DEFAULT_MODEL = "gpt-6.1-sol"

# Elavult modellek (developers.openai.com/api/docs/deprecations): kifejezetten tiltva.
DEPRECATED_MODELS = {
    "gpt-5.3-codex", "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini",
    "gpt-5-codex", "gpt-5.2-codex", "codex-mini-latest",
}

MAX_DIFF_CHARS = 60_000          # nagyobb PR -> nincs hívás (fail-closed)
MAX_OUTPUT_TOKENS = 4_000        # a modell érvelési tokenjei is ide számítanak
CHARS_PER_TOKEN_WORST = 2.5      # konzervatív becslés a bemeneti tokenekre
PROMPT_OVERHEAD_TOKENS = 2_500   # rendszerutasítás + séma
REQUEST_TIMEOUT_S = 120

MAX_LIVE_RUNS_PER_PR = 3
MAX_LIVE_RUNS_PER_DAY = 5
MAX_LIVE_RUNS_PER_MONTH = 12
MONTHLY_BUDGET_USD = 1.20        # az OpenAI-projekt 1,50 USD kemény korlátja alatt

MAX_FINDINGS = 30
MAX_FIELD_CHARS = 1_500


def price(model):
    if model in DEPRECATED_MODELS:
        raise ValueError(f"MODEL_DEPRECATED={model}")
    if model not in MODEL_PRICES_USD_PER_M:
        raise ValueError(f"MODEL_NOT_ALLOWED={model}")
    return MODEL_PRICES_USD_PER_M[model]


def worst_case_cost_usd(model=DEFAULT_MODEL):
    p = price(model)
    input_tokens = MAX_DIFF_CHARS / CHARS_PER_TOKEN_WORST + PROMPT_OVERHEAD_TOKENS
    return (input_tokens * p["input"] + MAX_OUTPUT_TOKENS * p["output"]) / 1_000_000


def cost_usd(model, input_tokens, output_tokens):
    p = price(model)
    return (int(input_tokens or 0) * p["input"] + int(output_tokens or 0) * p["output"]) / 1_000_000
