# Local Titanic input

The harness requires `data/titanic.csv`, kept local and ignored by Git. **Dataset provenance remains unresolved.** A prompt in the existing harness calls the input Kaggle-derived; this is a historical description, not verified attribution or a license determination.

Historical pilot metadata records this SHA-256 of the entire source file (including excluded rows):

```text
5c3c684032fa169dcc8b4853e06a9a5296fbb2f1b8061a5527710c418f5feac4
```

The local copy matches this hash. An arbitrary Titanic download does not reproduce the pilot: versions, schema, row order, preprocessing, and file bytes can differ. Obtain the exact authorized file and verify its hash; do not rename another dataset and assume equivalence.

The script reads UTF-8 with optional BOM using Python's CSV reader. It looks up the exact, case-sensitive header names `Passengerid` (integer record ID) and `2urvived` (integer binary survival label; unusual spelling preserved). It projects these into `record_id` and `survived` and ignores all other columns. Each retained row must have both fields, with labels 0 or 1 and IDs suitable for identifying records. The supplied file also has Age, Fare, Sex, sibsp, Parch, Pclass, Embarked, and repeated `zero` columns; these are unused by the current counting harness. The draft lookup proposal would require separate checks of any additional columns.

Only the **first 891 data rows**, in existing order, are used. The harness asserts 891 retained rows and a sum of 342 positive labels. The local file has 1,309 data rows; the remaining 418 are excluded and have unverified labels/provenance. Assertions check these aggregate assumptions, not provenance or every schema constraint. Scoring uses supplied local values and makes no historical ground-truth claim.

Sampling uses a dedicated random generator seeded with 1802026. After generating synthetic tables, it samples 100 retained rows, flips 20 sampled zero labels to one in a paired copy, and samples 802 retained rows. Changing row order or earlier random draws changes the resulting payloads even if aggregate counts match.

Before redistribution, establish the source, preprocessing history, license/terms, attribution obligations, and permission to share derived row-level data. Before sending rows to an API, verify permission for that use as well. Do not publish this CSV or trial prompts while those questions remain unresolved. Historical `trials.jsonl` stays in the personal source repository because it embeds row-level projections; see the artifact review in the historical results folder.
