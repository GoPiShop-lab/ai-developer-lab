# Codex review – dry-run teszt

Ez a fájl kizárólag a `codex-review` workflow próbafutásának (dry run) céltárgya. Ez a PR **nem
merge-elendő**; a teszt után merge nélkül lezárandó.

## Cél
A main ágon lévő `codex-review` workflow teljes láncának ellenőrzése OpenAI API-hívás és
költség nélkül (`dry_run=true`): kapuk, Environment-ellenőrzés, artifactok, PR-komment.

## Elvárt eredmény
- A futás neve: `codex-review PR #<szám> [dry]`.
- Step summary: `Kapu: True – DRY_RUN – Environment: ENV_OK`.
- A review job a `codex-review` Environmenttel fut; OpenAI-kulcs nem kerül a környezetbe.
- Review napló: `REVIEW status=ok`, a token-használat 0.
- Ezen a PR-en egy „DRY RUN” megjelölésű komment jelenik meg; jóváhagyás vagy merge nem történik.
- Az OpenAI usage-oldalon nem jelenik meg új hívás.

Részletek: `docs/codex-review.md`, 11. fejezet.
