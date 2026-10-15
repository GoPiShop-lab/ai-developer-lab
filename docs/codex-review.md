# Codex-alapú PR-ellenőrzés (AI Developer Lab)

Folyamat: **Claude Code fejleszt → Codex-szerepű modell ellenőriz (csak komment) → a tulajdonos dönt.**
Állapot: DRAFT, élesítés és az első fizetős hívás csak külön tulajdonosi jóváhagyással.

## 1. Működés
`.github/workflows/codex-review.yml`, kézi indítás (`workflow_dispatch`): `pr_number` (szöveg, csak számjegy – a `number` típus „2” helyett „2.0”-t adott át, run 38694866799), `dry_run` (alapértelmezés: **igen**).

| Job | Titok | GitHub-jog | Feladat |
|---|---|---|---|
| prepare | nincs | contents/pull-requests/actions: read | kapuk; PR-adat + diff **szövegként** (PR-kód nem kerül checkoutra, nem fut) |
| review (`environment: codex-review`) | `OPENAI_API_KEY` **Environment-secret** – csak éles futásnál, egy lépésben | **nincs** (`permissions: {}`) | 1 db `POST /v1/responses` hívás, újrapróbálkozás nélkül |
| publish | nincs | pull-requests: write | commit-SHA ellenőrzés, **PR-komment** (soha nem approve/merge) |

Adatátadás csak artifact-fájlokkal (`meta.json`, `diff.txt`, `result.json`); a workflow shell-szkriptjeiben nincs `${{ }}` kifejezés (script-injection ellen). Az artifactok titkot nem tartalmaznak (teszt ellenőrzi), megőrzés 3 nap.

## 2. Modell és ár (ellenőrizve 2026-10-14, hivatalos OpenAI-oldalak)
- `gpt-5.3-codex`: **elavult** (deprecation 2026-10-01, megszűnés 2027-04-01; ajánlott utód: `gpt-6-sol`). Minden korábbi `*-codex` modell már megszűnt (2026-07-23). → A kód ezeket tiltja.
- `gpt-6-sol` az árlistán nem szerepel → nem használjuk, amíg az ára nem ellenőrizhető.
- **Választott: `gpt-6.1-sol`** – hivatalos ár: 2,00 USD / 1M bemeneti, 10,00 USD / 1M kimeneti token (Standard, rövid kontextus).
- **NEM IGAZOLT:** hogy a lab-projekt API-kulcsa eléri-e ezt a modellt. Ellenőrzés: díjmentes `GET /v1/models/gpt-6.1-sol` – csak tulajdonosi jóváhagyással.
- Modellcsere: `CODEX_REVIEW_MODEL` repó-változó; csak a `review/config.py` árlistáján szereplő modell engedélyezett.

## 3. Költség- és futáskorlátok (kódba rögzítve, futáskor nem emelhetők)

### 3.1 Elméleti felső becslés – nem igazolt garancia
A korábbi „60 000 karakter / 2,5 karakter/token” csak átlagbecslés volt: többbájtos karaktereknél
(ékezet, emoji, CJK) egy karakter több token is lehet. A mostani számítás konzervatívabb, de
**szintén becslés**, mert a szerveroldali tokenelszámolás felső határa nem igazolt.

- **Bemenet (előzetes, kikényszerített méretkorlát):** a teljes kérés (utasítás + JSON-séma + diff +
  JSON-mezők) UTF-8 bájtszáma ≤ 36 000, különben **nincs hívás** (fail-closed). Ez a *kérés
  méretére* biztos korlát, a *tokenszámra* csak feltevésen keresztül: bájtszintű BPE-nél token ≤ bájt.
  +2 000 token tartalék a szerveroldali keretezésre.
- **Kimenet:** `max_output_tokens = 4 000` – az API dokumentációja szerint szerveroldalon érvényes,
  az érvelési tokenekkel együtt (a mi oldalunkról nem ellenőrizhető).
- **Konzervatív elméleti becslés / futás:** (36 000 + 2 000) × 2 USD/M + 4 000 × 10 USD/M =
  **≈ 0,116 USD**; 10 futás/hó → **≈ 1,16 USD/hó**. A havi keret erre épül.
- **Tájékoztató átlagbecslés / futás:** ~4 bájt/token, ~1 500 kimeneti token → teljes méretnél
  ≈ 0,033 USD, kis PR-nél ≈ 0,02 USD.

**Nem igazolt feltevések** [N]: (1) a `gpt-6.1-sol` tokenizálója bájtszintű BPE; (2) a szerveroldali
keretezés (szerepjelölők, a séma belső formája) belefér a 2 000 tokenbe; (3) a számlázott tokenek
megegyeznek a fentiekkel.

**A hívás utáni ellenőrzés NEM előzetes költségkorlát.** A tényleges `usage` összevetése az
elméleti becsléssel csak *utólag észlel*: a költség ekkor már felmerült. Túllépésnél
`bound_exceeded: true` és figyelmeztetés a kommentben; további éles futás csak felülvizsgálat után.

**Ténylegesen kikényszerített költséghatár egyedül az OpenAI-projekt 1,50 USD kemény korlátja**
(változatlan).

### 3.2 Korlátok
| Korlát | Érték | Jelleg |
|---|---|---|
| teljes kérés | ≤ 36 000 bájt | kikényszerített (hívás előtt) |
| diff | ≤ 32 000 bájt | kikényszerített (prepare, korai kapu) |
| kimeneti token | ≤ 4 000 (érveléssel együtt), `reasoning.effort=low` | API-oldali paraméter |
| költség / futás | ≈ 0,116 USD | konzervatív elméleti becslés |
| éles futás / PR · nap · hónap | ≤ 3 · ≤ 5 · ≤ 10 | kikényszerített (futásnapló) |
| költség / hónap | ≈ 1,16 USD | konzervatív elméleti becslés |
| havi saját keret | 1,20 USD | a becslésre épülő kapu |
| OpenAI-projekt kemény korlát | 1,50 USD | kikényszerített (OpenAI) |
| időkorlát / job | 5 perc | kikényszerített |

**Hónapváltás:** a nap és a hónap UTC szerint számít (a futásnapló-lekérdezés és a kapu egyaránt).
Az előző hónap utolsó napjának futásai nem számítanak az új hónapba. A saját futás mindig az
értékelés hónapjába számít (akkor is, ha a GitHub `created_at` még az előző hónapra esik). Ha a
saját futás a hónapváltás miatt kimarad a lekérdezésből, a kapu `OWN_RUN_NOT_FOUND`-dal elutasít
(fail-closed) – ilyenkor új indítás kell.

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
| T1 | `python3 -m unittest discover -s tests -v` – 49 teszt: workflow_dispatch PR-szám bemenet (regresszió), kapuk, hónapváltás (UTC), Environment-ellenőrzés, bájtalapú méretkorlát (határérték-tesztekkel), injekció, séma, kimenet-semlegesítés, API-hibák, hibás JSON, SHA, titokmentesség (hamis kulccsal), workflow-szabályok | 0 |
| T2 | `actionlint` (shellcheck-kel) a workflow-kra | 0 |
| T3 | `ci.yml` minden PR-re, titok nélkül; benne a `review-permissions-probe` (a review-job mintája `permissions: {}` mellett) | 0 |
| T4 | Próbafutás egy teszt-PR-en: `dry_run=true` – a teljes lánc fut, API-hívás és kulcs nélkül | 0 |
| T5 | Kapuk élesben: újrafuttatás → leáll; nem main-ről → leáll; dry futások nem fogyasztanak keretet | 0 |
| T6 | Díjmentes modell-elérhetőség (`GET /v1/models/...`) – **jóváhagyással** | 0 |
| T7 | Első éles review egy apró PR-en – **jóváhagyással**; token/költség összevetése az OpenAI usage-oldallal | elméleti becslés ≤ ~0,116 USD, várhatóan ~0,02; kemény határ: 1,50 USD |

## 8. Tulajdonosi beállítások
A pontos sorrend a 11. fejezetben.

## 9. GitHub-jogok
- **review job: `permissions: {}`.** A `GITHUB_TOKEN`-nek nincs jogosultsága. A checkout nyilvános
  repóban így is működik; az azonos futáson belüli artifact-letöltés nem a `GITHUB_TOKEN`-t
  használja. **Bizonyíték:** a `ci.yml` `review-permissions-probe` jobja ugyanazt a mintát
  (rögzített checkout + download-artifact + `python3 -m review review`) futtatja `permissions: {}`
  mellett, minden PR-en.
- Ha a repó privát lenne: a checkouthoz `contents: read` kell (minimum). Ezt a próba-job jelezné.
- prepare: `contents/pull-requests/actions: read` (PR-adat, diff, futásnapló); publish:
  `pull-requests: write` (komment) – mindkettő a feladat minimuma.

## 10. `workflow_dispatch` előfeltételek és Environment
- A „Run workflow” gomb **csak akkor jelenik meg**, ha a workflow-fájl a **default ágon (main)**
  van → a próbafutás a PR #1 merge-e **után** jön.
- Indításkor a „Use workflow from” ág **saját** workflow-verziója fut. A main-en kívüli indítást az
  első lépés leállítja, de egy másik ágon módosított workflow ezt kihagyhatja. Ezért:
- **A kulcs a `codex-review` Environment secretje**, az Environment „Deployment branches” szabálya:
  **Selected branches → `main`**. Ezt a GitHub kényszeríti ki: más ágról induló job nem kapja meg
  az Environment secretjét. A review job `environment: codex-review` beállítással fut.
- **Ellenőrzés, nem feltételezés:** a prepare job minden futásnál lekérdezi
  `GET /repos/{repo}/environments/codex-review` és `…/deployment-branch-policies`. Éles futás csak
  akkor engedett, ha: az Environment létezik, *custom* ágszabály van bekapcsolva (nem „protected
  branches”), és **pontosan egy** szabály van: ág, `main`. Bármi más vagy API-hiba → `ENV_*`
  elutasítás (fail-closed). Próbafutás Environment nélkül is mehet, az eredményt a step summary mutatja.
- [N] Nem igazolt még, hogy a prepare job `actions: read` tokenje olvashatja ezeket a végpontokat.
  Ha nem, a próbafutás summary-ja `ENV_MISSING`-et mutat (lásd 11/6.) – éles futás ekkor nem indul.
- **Azonos nevű repository-secret:** ha az Environmentben nincs `OPENAI_API_KEY`, a GitHub a
  repository-szintűt adná. Ezért a repository-szintű secretet törölni kell (11/4.). Ezt a workflow nem
  tudja ellenőrizni (a `GITHUB_TOKEN` nem olvashat secret-listát) → kézi ellenőrzés.
- Ha az Environment még nem létezik az első futáskor, a GitHub **szabályok nélkül** automatikusan
  létrehozza → ezért az Environmentet a merge **előtt** kell beállítani.
- Indítani csak írási joggal rendelkező felhasználó tud (egyszemélyes repóban: a tulajdonos).

## 11. Tulajdonosi beállítások és merge utáni próbafutás – pontos sorrend
1–5. lépés merge előtt, a GitHub webes felületén. Minden lépés díjmentes, OpenAI-hívás nincs.
1. **Actions-jogok:** Settings → Actions → General → „Workflow permissions” = *Read repository
   contents and packages*; „Allow GitHub Actions to create and approve pull requests” = **KI** → Save.
2. **Environment:** Settings → Environments → New environment → név: `codex-review`.
   - „Deployment branches and tags” → **Selected branches and tags** → Add rule → típus *Branch*,
     minta: `main` (pontosan így, csillag nélkül). Más szabály ne legyen.
   - Required reviewers / wait timer: nem kell (opcionális).
3. **Environment-secret:** ugyanitt „Environment secrets” → Add secret → név `OPENAI_API_KEY`,
   érték: a lab-projekt kulcsa.
4. **Repository-secret törlése:** Settings → Secrets and variables → Actions → Repository secrets →
   `OPENAI_API_KEY` → Remove. Ellenőrzés: a listában csak az Environment alatt szerepeljen.
5. **Ruleset a main-re** a 6. fejezet szerint (kötelező státusz: `ci / test`).
6. **PR #1 merge** (csak tulajdonos). Ellenőrzés: a main-en lefut a `ci` (zöld), és az Actions
   listában megjelenik a `codex-review`.
7. **Teszt-PR** a main-re (egysoros README-módosítás, külön ágon); a száma: N.
8. **Próbafutás:** Actions → codex-review → Run workflow → *Use workflow from: `main`* ·
   `pr_number` = N · **`dry_run` bejelölve** (alapértelmezés – ne vedd ki).
9. **Elvárt eredmény:**
   - futás neve: `codex-review PR #N [dry]`;
   - step summary: `Kapu: True – DRY_RUN – Environment: ENV_OK` ← **ez igazolja a main-only szabályt**;
     ha `ENV_*` hiba látszik: állj meg, javítsd a 2. lépést, és jelezd;
   - a review job az Environmenttel fut (a futás oldalán „codex-review” környezet látszik);
   - review napló: `REVIEW status=ok … usage={'input_tokens': 0, 'output_tokens': 0}`;
   - a teszt-PR-en egy „DRY RUN” komment; approve/merge nincs; OpenAI usage-oldal: nincs új hívás.
10. **Negatív próbák** (mindegyik `dry_run` bejelölve):
    - a: a 8. lépés futásán „Re-run all jobs” → az első lépésnél leáll („Újrafuttatás tilos”);
    - b: „Use workflow from” = a teszt-PR ága → az első lépésnél leáll („Csak a main ágról”).
11. **Lezárás:** a teszt-PR-t merge nélkül zárd le, az ágát töröld.
12. Éles futás (T6 → T7) csak ezután, **külön tulajdonosi jóváhagyással**.

## 12. Visszaállítás
A workflow a GitHub Actions felületén letiltható („Disable workflow”), vagy a fájl törölhető egy PR-rel. Állapotot, adatbázist nem kezel.
