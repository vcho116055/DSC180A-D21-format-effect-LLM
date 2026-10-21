# Historical pilot artifact review

Reviewed October 20, 2026 for transfer from the personal progress repository.

- `REPORT.md`, `metadata.json`, and `summary.json` were copied unchanged. They contain narrative findings, aggregate counts, settings, source hash, and cost estimates without embedded dataset rows. No source credential value or common credential-pattern match was detected in any of the four original artifacts; this scan is not a proof that all possible secrets are absent.
- `summary.json` retains the original machine-local Windows results path as historical metadata. It is not a usable path on this checkout. The path was reviewed as a local directory reference, not a credential.
- **`trials.jsonl` was not copied.** Its 20 trial records include 16 table prompts, with row-level dataset projections in prompts and request messages. Source provenance and redistribution rights are unresolved, including for derived ID/label pairs. It remains at `results/luna_pilot_20261014T031651Z/trials.jsonl` in the personal source repository pending provenance/license review. No row payloads or credentials are reproduced here.

References to `trials.jsonl` in the unchanged historical report describe the original run archive; that file is intentionally absent from this shared checkout. The report, metadata, and summary preserve the completed pilot's **GPT-6 Luna** identity and historical rates. The planned GPT-5.6 Luna work requires separate calibration and an agreed protocol.

The root `.gitignore` excludes generated `results/**/trials.jsonl` as an additional safeguard. Review all new artifacts before publication, since dataset rows can also appear outside `data/` and in differently named logs. No failed run folders were included.
