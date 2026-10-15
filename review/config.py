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

# --- Bemeneti korlát: GARANTÁLT felső becslés, nem átlagos karakter/token arány ---
# A teljes kérés (rendszerutasítás + JSON-séma + diff + minden JSON-mező) UTF-8 bájtszámát mérjük.
# Bájtszintű BPE-tokenizálónál minden token legalább 1 bájtot fed le, ezért a szöveg tokenszáma
# <= a bájtszáma. A szerveroldali keretezés (szerepjelölők, a séma belső formája) nem nyilvános:
# erre fix tartalék szolgál. Ami e fölött maradna, azt a hívás utáni ellenőrzés jelzi, és végső
# védelemként az OpenAI-projekt 1,50 USD kemény korlátja állítja meg.
MAX_REQUEST_BYTES = 36_000       # a teljes szerializált kérés; felette nincs hívás (fail-closed)
MAX_DIFF_BYTES = 32_000          # korai kapu a prepare jobban (informatív); a döntő a fenti
FRAMING_MARGIN_TOKENS = 2_000    # szerveroldali keretezés tartaléka
MAX_OUTPUT_TOKENS = 4_000        # szerveroldali korlát, az érvelési tokenekkel együtt
REQUEST_TIMEOUT_S = 120

# Csak tájékoztató becslés (NEM korlát): átlagos kód ~4 bájt/token.
TYPICAL_BYTES_PER_TOKEN = 4.0
TYPICAL_OUTPUT_TOKENS = 1_500

MAX_LIVE_RUNS_PER_PR = 3
MAX_LIVE_RUNS_PER_DAY = 5
MAX_LIVE_RUNS_PER_MONTH = 10
MONTHLY_BUDGET_USD = 1.20        # az OpenAI-projekt 1,50 USD kemény korlátja alatt

MAX_FINDINGS = 30
MAX_FIELD_CHARS = 1_500


def price(model):
    if model in DEPRECATED_MODELS:
        raise ValueError(f"MODEL_DEPRECATED={model}")
    if model not in MODEL_PRICES_USD_PER_M:
        raise ValueError(f"MODEL_NOT_ALLOWED={model}")
    return MODEL_PRICES_USD_PER_M[model]


def max_input_tokens(request_bytes=MAX_REQUEST_BYTES):
    """Garantált felső korlát a bemeneti tokenekre: bájtszám + keretezési tartalék."""
    return int(request_bytes) + FRAMING_MARGIN_TOKENS


def guaranteed_max_cost_usd(model=DEFAULT_MODEL, request_bytes=MAX_REQUEST_BYTES):
    """Egy futás legnagyobb lehetséges költsége (USD). Erre épül a havi keret, nem a becslésre."""
    p = price(model)
    return (max_input_tokens(request_bytes) * p["input"] + MAX_OUTPUT_TOKENS * p["output"]) / 1_000_000


def typical_cost_usd(model=DEFAULT_MODEL, request_bytes=MAX_REQUEST_BYTES):
    """Tájékoztató becslés (átlagos kód, átlagos válasz). Költségkorlátként NEM használható."""
    p = price(model)
    return (request_bytes / TYPICAL_BYTES_PER_TOKEN * p["input"] + TYPICAL_OUTPUT_TOKENS * p["output"]) / 1_000_000


def cost_usd(model, input_tokens, output_tokens):
    p = price(model)
    return (int(input_tokens or 0) * p["input"] + int(output_tokens or 0) * p["output"]) / 1_000_000
