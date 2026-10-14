# Codex-alapú PR-ellenőrzés (AI Developer Lab)

Folyamat: **Claude Code fejleszt → Codex-szerepű modell ellenőriz (csak komment) → a tulajdonos dönt.**
Állapot: DRAFT, élesítés és az első fizetős hívás csak külön tulajdonosi jóváhagyással.

## 1. Működés
`.github/workflows/codex-review.yml`, kézi indítás (`workflow_dispatch`): `pr_number`, `dry_run` (alapértelmezés: **igen**).

| Job | Titok | GitHub-jog | Feladat |
|---|---|---|---|
| prepare | nincs | contents/pull-requests/actions: read | kapuk; PR-adat + diff **szövegként** (PR-kód nem kerül checkoutra, nem fut) |
| review | `OPENAI_API_KEY` – csak éles futásnál, egy lépésben | contents: read | 1 db `POST /v1/responses` hívás, újrapróbálkozás nélkül |
| publish | nincs | pull-requests: write | commit-SHA ellenőrzés, **PR-komment** (soha nem approve/merge) |

Adatátadás csak artifact-fájlokkal (`meta.json`, `diff.txt`, `result.json`); a workflow shell-szkriptjeiben nincs `${{ }}` kifejezés (script-injection ellen). Az artifactok titkot nem tartalmaznak (teszt ellenőrzi), megőrzés 3 nap.

## 2. Modell és ár (ellenőrizve 2026-10-14, hivatalos OpenAI-oldalak)
- `gpt-5.3-codex`: **elavult** (deprecation 2026-10-01, megszűnés 2027-04-01; ajánlott utód: `gpt-6-sol`). Minden korábbi `*-codex` modell már megszűnt (2026-07-23). → A kód ezeket tiltja.
- `gpt-6-sol` az árlistán nem szerepel → nem használjuk, amíg az ára nem ellenőrizhető.
- **Választott: `gpt-6.1-sol`** – hivatalos ár: 2,00 USD / 1M bemeneti, 10,00 USD / 1M kimeneti token (Standard, rövid kontextus).
- **NEM IGAZOLT:** hogy a lab-projekt API-kulcsa eléri-e ezt a modellt. Ellenőrzés: díjmentes `GET /v1/models/gpt-6.1-sol` – csak tulajdonosi jóváhagyással.
- Modellcsere: `CODEX_REVIEW_MODEL` repó-változó; csak a `review/config.py` árlistáján szereplő modell engedélyezett.

## 3. Költség- és futáskorlátok (kódba rögzítve, futáskor nem emelhetők)
| Korlát | Érték |
|---|---|
| diff | ≤ 60 000 karakter, felette nincs hívás |
| kimeneti token | ≤ 4 000 (érveléssel együtt), `reasoning.effort=low` |
| legrosszabb eset / futás | 0,093 USD |
| éles futás / PR | ≤ 3 |
| éles futás / nap | ≤ 5 |
| éles futás / hónap | ≤ 12 → legrosszabb esetben 1,12 USD |
| havi saját keret | 1,20 USD (az OpenAI-projekt 1,50 USD kemény korlátja alatt) |
| időkorlát / job | 5 perc |

**Újrafuttatás és párhuzamosság:** a számlálás a GitHub futásnaplójából történik (az AI nem írhatja), a futás-azonosító szerint – a saját futásnál korábbi és a saját futás számít, minden állapotban (a megszakított is). Párhuzamos indításnál így determinisztikus, melyik bukik. Újrafuttatás (`run_attempt > 1`) minden jobban tilos – a hibás job külön újrafuttatása sem kerülheti meg a kaput. `concurrency` csoport: egyszerre egy futás; a GitHub legfeljebb egy várakozót tart, a felülírt várakozó „cancelled” lesz és beleszámít a keretbe (konzervatív).

## 4. Hibakezelés
API-hiba (HTTP, hálózat, kvóta / `project_spend_limit_exceeded`), hiányos válasz (`incomplete`), elutasítás (`refusal`), hibás JSON, sémasértés → a komment csak a hiba típusát írja ki, **a modell szövegéből semmit**. A hibaüzenetek titokmintákra szűrve (`redact`).

## 5. Prompt-injekció elleni védelem
1. A diff véletlen (128 bites) határolók között, „csak adat” jelöléssel; a határoló garantáltan nem fordul elő a diffben.
2. A kérés paraméterei (modell, tokenkorlát, séma, `store=false`) kódból jönnek, a diff nem befolyásolhatja.
3. Szigorú JSON-séma (strict) + saját validátor: plusz mező, ismeretlen súlyosság (pl. „APPROVE”) → elutasítva.
4. A modell kimenete megbízhatatlan: `@`-említés, link, kép, HTML, HTML-komment, kódblokk, vezérlőkarakter semlegesítve; titokszerű minta kitakarva.
5. A publish csak kommentel; a review-jobnak nincs írási joga; a PR-kód nem fut.
6. Commit-SHA ellenőrzés publikálás előtt: ha a PR feje közben változott → „elavult”, a review szövege nem kerül ki.

## 6. Kötelező jóváhagyás egyszemélyes repóban
- A GitHub szerint a PR szerzője nem hagyhatja jóvá a saját PR-jét. **Ha a PR-t bot/app nyitja** (Claude Code), a tulajdonos jóváhagyása érvényes → a „required approval” rendesen működik.
- **Ha a tulajdonos maga a szerző**, a kötelező jóváhagyás nem teljesíthető → a ruleset **bypass-listáján csak a tulajdonos** szerepeljen („pull request only” móddal): így csak ő, naplózott felülbírálással egyesíthet; bot és Actions nem.
- Javasolt ruleset a `main`-re (nyilvános repóban ingyenes): PR kötelező · 1 jóváhagyás · régi jóváhagyás elvetése új push után · a legutóbbi push jóváhagyása kötelező · beszélgetések lezárása · kötelező státusz: `ci / test` · force push és törlés tiltva · bypass: csak a tulajdonos.
- Actions-beállítás: **„Allow GitHub Actions to create and approve pull requests” = KI** (a `GITHUB_TOKEN` így nem tud jóváhagyni). Külső közreműködő workflow-ja csak jóváhagyással fut.
- A Codex-komment nem jóváhagyás, nem is teljesítheti a szabályt.

## 7. Teszterv
| # | Teszt | Költség |
|---|---|---|
| T1 | `python3 -m unittest discover -s tests -v` – 34 teszt: kapuk, költség, injekció, séma, kimenet-semlegesítés, API-hibák, hibás JSON, SHA, titokmentesség (hamis kulccsal), workflow-szabályok | 0 |
| T2 | `actionlint` (shellcheck-kel) a workflow-kra | 0 |
| T3 | `ci.yml` minden PR-re, titok nélkül | 0 |
| T4 | Próbafutás egy teszt-PR-en: `dry_run=true` – a teljes lánc fut, API-hívás és kulcs nélkül | 0 |
| T5 | Kapuk élesben: újrafuttatás → leáll; nem main-ről → leáll; dry futások nem fogyasztanak keretet | 0 |
| T6 | Díjmentes modell-elérhetőség (`GET /v1/models/...`) – **jóváhagyással** | 0 |
| T7 | Első éles review egy apró PR-en – **jóváhagyással**; token/költség összevetése az OpenAI usage-oldallal | ≤ 0,093 USD |

## 8. Tulajdonosi beállítások az első futás előtt
1. Secret neve: `OPENAI_API_KEY` (ha más, jelezd – a workflow-ban egy helyen kell átírni).
2. OpenAI lab-projekt: 1,50 USD „Enforce a hard limit” (megerősítve 2026-10-14).
3. Ruleset + Actions-beállítás a 6. pont szerint.
4. Opcionális: `CODEX_REVIEW_MODEL` repó-változó (alapértelmezés: `gpt-6.1-sol`).

## 9. Visszaállítás
A workflow a GitHub Actions felületén letiltható („Disable workflow”), vagy a fájl törölhető egy PR-rel. Állapotot, adatbázist nem kezel.
