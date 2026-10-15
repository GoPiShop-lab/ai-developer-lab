# Codex-alapú PR-ellenőrzés (AI Developer Lab)

Folyamat: **Claude Code fejleszt → Codex-szerepű modell ellenőriz (csak komment) → a tulajdonos dönt.**
Állapot: DRAFT, élesítés és az első fizetős hívás csak külön tulajdonosi jóváhagyással.

## 1. Működés
`.github/workflows/codex-review.yml`, kézi indítás (`workflow_dispatch`): `pr_number`, `dry_run` (alapértelmezés: **igen**).

| Job | Titok | GitHub-jog | Feladat |
|---|---|---|---|
| prepare | nincs | contents/pull-requests/actions: read | kapuk; PR-adat + diff **szövegként** (PR-kód nem kerül checkoutra, nem fut) |
| review | `OPENAI_API_KEY` – csak éles futásnál, egy lépésben | **nincs** (`permissions: {}`) | 1 db `POST /v1/responses` hívás, újrapróbálkozás nélkül |
| publish | nincs | pull-requests: write | commit-SHA ellenőrzés, **PR-komment** (soha nem approve/merge) |

Adatátadás csak artifact-fájlokkal (`meta.json`, `diff.txt`, `result.json`); a workflow shell-szkriptjeiben nincs `${{ }}` kifejezés (script-injection ellen). Az artifactok titkot nem tartalmaznak (teszt ellenőrzi), megőrzés 3 nap.

## 2. Modell és ár (ellenőrizve 2026-10-14, hivatalos OpenAI-oldalak)
- `gpt-5.3-codex`: **elavult** (deprecation 2026-10-01, megszűnés 2027-04-01; ajánlott utód: `gpt-6-sol`). Minden korábbi `*-codex` modell már megszűnt (2026-07-23). → A kód ezeket tiltja.
- `gpt-6-sol` az árlistán nem szerepel → nem használjuk, amíg az ára nem ellenőrizhető.
- **Választott: `gpt-6.1-sol`** – hivatalos ár: 2,00 USD / 1M bemeneti, 10,00 USD / 1M kimeneti token (Standard, rövid kontextus).
- **NEM IGAZOLT:** hogy a lab-projekt API-kulcsa eléri-e ezt a modellt. Ellenőrzés: díjmentes `GET /v1/models/gpt-6.1-sol` – csak tulajdonosi jóváhagyással.
- Modellcsere: `CODEX_REVIEW_MODEL` repó-változó; csak a `review/config.py` árlistáján szereplő modell engedélyezett.

## 3. Költség- és futáskorlátok (kódba rögzítve, futáskor nem emelhetők)

### 3.1 Garantált felső korlát vs. becslés
A korábbi „60 000 karakter / 2,5 karakter/token” **csak becslés volt, nem korlát**: többbájtos
karaktereknél (ékezet, emoji, CJK) egy karakter több token is lehet. Most:

- **Bemenet:** a teljes kérés (rendszerutasítás + JSON-séma + diff + JSON-mezők) UTF-8
  **bájtszámát** mérjük, és 36 000 bájt felett **nincs hívás** (fail-closed). Bájtszintű
  BPE-tokenizálónál minden token ≥ 1 bájt, ezért **token ≤ bájt**. Ehhez +2 000 token tartalék
  a szerveroldali keretezésre (szerepjelölők, a séma belső formája).
- **Kimenet:** `max_output_tokens = 4 000` – ezt az API szerveroldalon érvényesíti, az érvelési
  tokenekkel együtt.
- **Garantált maximum / futás:** (36 000 + 2 000) × 2 USD/M + 4 000 × 10 USD/M = **0,116 USD**.
  A havi keret erre épül.
- **Tájékoztató becslés / futás** (nem korlát): ~4 bájt/token, ~1 500 kimeneti token →
  teljes méretű diffnél ≈ 0,033 USD, kis PR-nél ≈ 0,02 USD.

**Ami nem bizonyítható kliensoldalon** [N]: (1) hogy a `gpt-6.1-sol` tokenizálója bájtszintű BPE
(minden nyilvános OpenAI-tokenizáló az, de erre a modellre nincs nyilvános adat); (2) a
szerveroldali keretezés pontos mérete. Védelem: a hívás után a tényleges `usage` összevetése a
korláttal – túllépésnél `bound_exceeded: true` és figyelmeztetés a kommentben; végső védelem az
**OpenAI-projekt 1,50 USD kemény korlátja** (változatlan).

### 3.2 Korlátok
| Korlát | Érték |
|---|---|
| teljes kérés | ≤ 36 000 bájt (review job, hívás előtt; döntő ellenőrzés) |
| diff | ≤ 32 000 bájt (prepare job, korai kapu) |
| kimeneti token | ≤ 4 000 (érveléssel együtt), `reasoning.effort=low` |
| garantált maximum / futás | 0,116 USD |
| éles futás / PR | ≤ 3 |
| éles futás / nap | ≤ 5 (≤ 0,58 USD) |
| éles futás / hónap | ≤ 10 → garantáltan ≤ 1,16 USD |
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
5. A publish csak kommentel; a review-jobnak semmilyen GitHub-joga nincs (`permissions: {}`); a PR-kód nem fut.
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
| T1 | `python3 -m unittest discover -s tests -v` – 41 teszt: kapuk, garantált költségkorlát (bájtalapú, határérték-tesztekkel), injekció, séma, kimenet-semlegesítés, API-hibák, hibás JSON, SHA, titokmentesség (hamis kulccsal), workflow-szabályok | 0 |
| T2 | `actionlint` (shellcheck-kel) a workflow-kra | 0 |
| T3 | `ci.yml` minden PR-re, titok nélkül; benne a `review-permissions-probe` (a review-job mintája `permissions: {}` mellett) | 0 |
| T4 | Próbafutás egy teszt-PR-en: `dry_run=true` – a teljes lánc fut, API-hívás és kulcs nélkül | 0 |
| T5 | Kapuk élesben: újrafuttatás → leáll; nem main-ről → leáll; dry futások nem fogyasztanak keretet | 0 |
| T6 | Díjmentes modell-elérhetőség (`GET /v1/models/...`) – **jóváhagyással** | 0 |
| T7 | Első éles review egy apró PR-en – **jóváhagyással**; token/költség összevetése az OpenAI usage-oldallal | ≤ 0,116 USD (garantált), várhatóan ~0,02 |

## 8. Tulajdonosi beállítások az első futás előtt
1. Secret neve: `OPENAI_API_KEY` (ha más, jelezd – a workflow-ban egy helyen kell átírni).
2. OpenAI lab-projekt: 1,50 USD „Enforce a hard limit” (megerősítve 2026-10-14).
3. Ruleset + Actions-beállítás a 6. pont szerint.
4. Opcionális: `CODEX_REVIEW_MODEL` repó-változó (alapértelmezés: `gpt-6.1-sol`).

## 9. GitHub-jogok
- **review job: `permissions: {}`.** A `GITHUB_TOKEN`-nek nincs jogosultsága. A checkout nyilvános
  repóban így is működik; az azonos futáson belüli artifact-letöltés nem a `GITHUB_TOKEN`-t
  használja. **Bizonyíték:** a `ci.yml` `review-permissions-probe` jobja ugyanazt a mintát
  (rögzített checkout + download-artifact + `python3 -m review review`) futtatja `permissions: {}`
  mellett, minden PR-en.
- Ha a repó privát lenne: a checkouthoz `contents: read` kell (minimum). Ezt a próba-job jelezné.
- prepare: `contents/pull-requests/actions: read` (PR-adat, diff, futásnapló); publish:
  `pull-requests: write` (komment) – mindkettő a feladat minimuma.

## 10. `workflow_dispatch` előfeltételek
- A „Run workflow” gomb **csak akkor jelenik meg**, ha a workflow-fájl a **default ágon (main)**
  van. A PR #1 merge-e előtt tehát nem indítható – ezért a próbafutás a merge **után** jön.
- Indításkor a „Use workflow from” ág **saját** workflow-verziója fut. Az első lépés a main-en
  kívüli indítást leállítja – **de egy másik ágon módosított workflow ezt a lépést kihagyhatja**.
  Repository-secretet minden ág workflow-ja megkaphat; jelenleg csak a tulajdonosnak van írási
  joga, ezért ez elfogadható kockázat. **Javasolt (külön döntés):** a kulcs áthelyezése egy
  `codex-review` Environmentbe „Deployment branches: main” szabállyal – így más ágról a kulcs
  technikailag sem érhető el.
- Indítani csak írási joggal rendelkező felhasználó tud (egyszemélyes repóban: a tulajdonos).

## 11. Merge utáni próbafutás (dry_run=true) – pontos sorrend
Minden lépés díjmentes; OpenAI-hívás nincs. Kulcs nem kell hozzá.
1. **Beállítások merge előtt:** Settings → Actions → General: „Workflow permissions” = *Read
   repository contents*; „Allow GitHub Actions to create and approve pull requests” = **KI**.
   Ruleset a 6. pont szerint.
2. **PR #1 merge** (csak tulajdonos). Ellenőrzés: a main-en lefut a `ci` (zöld), és az Actions
   listában megjelenik a `codex-review`.
3. **Teszt-PR nyitása** a main-re (egysoros README-módosítás, külön ágon). Számát jegyezd fel (N).
4. **Indítás:** Actions → codex-review → Run workflow → *Use workflow from: `main`* ·
   `pr_number` = N · **`dry_run` bejelölve** (alapértelmezés – ne vedd ki).
5. **Elvárt eredmény:**
   - futás neve: `codex-review PR #N [dry]`;
   - prepare összefoglaló: `Kapu: True – DRY_RUN`;
   - review napló: `REVIEW status=ok … usage={'input_tokens': 0, 'output_tokens': 0}`;
   - a teszt-PR-en egy komment „DRY RUN” szöveggel; approve/merge nincs;
   - OpenAI usage-oldal: nincs új hívás.
6. **Negatív próbák** (mindegyik `dry_run` bejelölve):
   - a: a 4. lépés futásán „Re-run all jobs” → az első lépésnél leáll („Újrafuttatás tilos”);
   - b: „Use workflow from” = a teszt-PR ága → az első lépésnél leáll („Csak a main ágról”).
7. **Lezárás:** a teszt-PR-t merge nélkül zárd le, az ágát töröld.
8. Éles futás (T6 → T7) csak ezután, **külön tulajdonosi jóváhagyással**.

## 12. Visszaállítás
A workflow a GitHub Actions felületén letiltható („Disable workflow”), vagy a fájl törölhető egy PR-rel. Állapotot, adatbázist nem kezel.
