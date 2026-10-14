"""Codex-alapú PR-ellenőrzés (AI Developer Lab).

Biztonsági alapelvek (docs/codex-review.md):
- a PR kódját soha nem futtatjuk, csak a diffet olvassuk szövegként;
- az OpenAI-kulcs kizárólag a review-lépés környezetében él, naplóba/artifactba nem kerül;
- a kimenet csak PR-komment, soha nem jóváhagyás vagy merge.
"""
