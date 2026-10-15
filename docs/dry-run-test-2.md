# Codex review – 2. dry-run teszt (NE merge-eld)

Ez a fájl csak a `codex-review` workflow második próbafutásának céltárgya, a `pr_number`
javítás (PR #3) után. A teszt után ezt a PR-t **merge nélkül** le kell zárni, az ágát törölni.

## Elvárt eredmény (`dry_run=true`)
- Futás neve: `codex-review PR #<szám> [dry]` (nem `.0` végű szám).
- Step summary: `Kapu: True – DRY_RUN – Environment: ENV_OK`.
- Review napló: `REVIEW status=ok`, a token-használat 0; OpenAI-hívás nincs.
- Ezen a PR-en egy „DRY RUN” komment; jóváhagyás vagy merge nincs.
