# Round 2 lookup on new datasets: protocol

Written and frozen before any response collection. Exploratory, not a public preregistration. It repeats the [Round 2 lookup design](week4_protocol.md) on three datasets not used before, to see whether its ceiling accuracy holds on other sources. Implementation: [round2_newdata.py](round2_newdata.py), which reuses `week4_study.py` for table construction, serialization, scoring, the runner, and analysis without modifying it.

## What stays the same as Round 2

Model, instruction, prompt wording, the four formats, named/neutral cues, original/altered versions, target selection (one value unique within the table from each third), the replacement rule, the absent ID `999999`, scoring, output caps, the runner's logging/resume/stop rules, and the stratified block bootstrap. The primary design is again 3 datasets × 40/200 rows × 3 sampled tables × 16 conditions = **288 requests**, 864 present cells and 288 absent IDs.

## Datasets

| Key | Local file | Rows | `record_id` | Other fields | Queried field |
|---|---|---:|---|---|---|
| `ibm` | `IBM.csv` | 1,470 | `EmployeeNumber` | `age`, `gender`, `department`, `job_role` | `monthly_income` |
| `avocado` | `avocado.csv` | 18,249 | one-based row index | `date`, `region`, `type`, `average_price` | `total_volume` |
| `creditcard` | `creditcard.csv` | 284,807 | one-based row index | `time`, `v1`, `v2` | `amount` |

Values stay as strings read from the CSV. Named cues are `IBM HR Analytics Employee Attrition`, `Avocado Prices`, and `Credit Card Fraud Detection`. Source hashes are in the manifest. Provenance of these local copies is unverified, as for the earlier datasets.

## What differs from Round 2

| Component | Round 2 | Here | Requests |
|---|---|---|---:|
| Primary lookup | Titanic, wine, medical | IBM, avocado, credit card | 288 |
| Synthetic lookup | 24 | unchanged | 24 |
| 800-row stress lookup | Titanic | IBM (1,470 rows available) | 16 |
| Exact-prompt repeats | 12 | unchanged, on the new datasets | 12 |
| Counting | 12 | dropped: it counted Titanic survivors | 0 |
| No-table probes | 6 | dropped: Round 2's version was inconclusive (see [Round 3](../methodology/round3_knowledge_followup.md)) | 0 |
| **Total** | 358 | | **340** |

Seed `18020261025`.

## Spending cap and dispatch order

The cap is **$1.00** of actual estimated cost (Round 2: $4.25 of summed worst-case reservations). Round 2's runner reserved every request's worst case and never released the unused part, so a $1 cap would have stopped it after about a fifth of this plan (worst case for all 340 requests: $4.78). This runner, in `round2_newdata.py`, reserves a request's worst case only while it is in flight, then counts its actual cost from token usage at $0.20/$1.20 per million. A request is sent only if spent + in-flight reservations + its own worst case fit the cap, so the cap cannot be exceeded. A failed request keeps its full worst case counted, since it may have been billed. Expected cost at Round 2's actual-to-bound ratio is about $0.47.

Requests are sent in priority order (seed `18020261026`): block 0 of all six dataset × size strata, then block 1, then block 2, each block's 16 conditions together; then repeats, synthetic, and finally the 800-row stress tables. If the cap stops the run:

- `results/round2_newdata/budget_status.json` records the amount spent, the stop reason, unsent requests by stage, and the complete primary blocks.
- `python -m experiments.round2_newdata analyze` analyzes only complete primary blocks plus recorded secondary requests, in `results/round2_newdata/partial/`.
- `python -m experiments.round2_newdata run --budget <higher cap>` resumes and sends only the unsent requests. Raising the cap is a deliberate decision recorded in `runtime.jsonl`, not automatic.

A simulation that bills every request its full output allowance, far above typical usage, finished all 288 primary requests and the repeats under $1, leaving 16 stress and 12 synthetic requests unsent.

## Known limitations specific to these datasets

- **Replacements are conspicuous.** Round 2 draws replacements uniformly between the field's minimum and maximum, at five decimals. These fields are skewed, so altered cells are mostly far larger than their neighbours (avocado `total_volume` up to the ~62 million national rows; credit card `amount` up to 25,691 where most are under 100), and IBM's whole-number incomes gain decimals. Altered cells are therefore easier to spot than in Round 2, which can inflate altered-table accuracy. The rule is kept unchanged for comparability.
- **Target selection is biased toward unusual values** where values repeat often (credit card `amount`: about 6% of values are unique across the file), because targets must be unique within the sampled table.
- **Familiarity differs by design.** IBM and avocado are widely used Kaggle datasets; credit card fields `v1`, `v2` are anonymized PCA components, so its rows are unlikely to be recalled. This is a purposive contrast, not a measured familiarity level. Avocado and credit card IDs are local row indices, which give weak cues for recall.
