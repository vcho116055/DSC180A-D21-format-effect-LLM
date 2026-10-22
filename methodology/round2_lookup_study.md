# Round 2: Matched record lookup across four input formats

This retrospective reference describes the October 21, 2026 run in `results/week4_lookup`. Its 358 requests include the 288-request primary experiment and all planned secondary controls. The [original protocol](../experiments/week4_protocol.md) and case manifest were written before response collection; this more detailed reference was written afterward. The plan was frozen locally, not publicly preregistered.

## Research question and outcomes

The primary question was whether input representation changes how reliably a model follows supplied cell values, particularly when those values differ from the local source dataset. Direct record lookup replaced counting as the main task because the pilot mixed failures to follow supplied evidence with arithmetic errors.

The primary observation was correctness of each requested present-cell value. Secondary observations included whole-request correctness, correct reporting of absent IDs, literal copying, output structure, and exact returns of replaced original values. Counting was retained as a distinct secondary task. No overall error rate was defined as a leakage rate.

## Data sources and experimental schemas

All sources were read with Python's CSV reader using UTF-8 with optional BOM handling. Source hashes are recorded in the [manifest](../results/week4_lookup/manifest.json) and [archive index](README.md). Files were projected to the fields below; there was no imputation, standardization, train/test model fitting, or numerical feature normalization.

| Dataset | Local source rows | Eligible rows | Ordered experimental fields | Queried field |
|---|---:|---:|---|---|
| Titanic | 1,309 | First 891 | `record_id`, `age`, `sex`, `pclass`, `fare` | `fare` |
| Red Wine Quality | 1,599 | All 1,599 | `record_id`, `fixed_acidity`, `volatile_acidity`, `alcohol`, `density` | `density` |
| Medical Cost Personal Datasets | 1,338 | All 1,338 | `record_id`, `age`, `sex`, `bmi`, `smoker`, `region`, `charges` | `charges` |

For Titanic, these fields came from `Passengerid`, `Age`, `Sex`, `Pclass`, and `Fare`. The retained IDs were original local passenger IDs. For wine, names containing spaces were mapped to underscore names, and `record_id` was the one-based local data-row index. Medical data likewise received one-based local row IDs; the source `children` field was omitted. Wine's quality label and other unselected chemistry columns were omitted.

Values remained strings as read from the CSV. The loader asserted unique record IDs and nonempty strings in all selected fields. These checks do not authenticate the source versions or establish whether earlier preprocessing had occurred. The transformed Titanic file's repeated `zero` columns were irrelevant to the selected fields. Only its first 891 rows were used; the remaining 418 labels were not accepted as verified truth.

## Main factorial design

The primary comparison crossed:

| Factor | Levels |
|---|---|
| Dataset | Titanic, wine, medical |
| Rows per sampled table | 40, 200 |
| Sample block within dataset and size | 3 |
| Input representation | CSV, JSON, XML, TXT |
| Dataset-name cue | Named, neutral |
| Values | Original, altered |

This produces `3 × 2 × 3 = 18` sampled table blocks, each rendered under `4 × 2 × 2 = 16` conditions, for 288 primary requests. Every request asks for three present cells and one absent ID. Primary totals are 864 present-cell answers and 288 absent-record answers; 432 present-cell answers come from altered tables.

Sampling used `random.Random(18020261021)`. Each table was sampled without replacement from its eligible source rows. Different blocks can overlap in records. Within a block, all formats and cue conditions used exactly the same sampled row order and queried IDs. A new sample was not drawn for each representation.

The sampled table is the unit used for paired format contrasts. The 864 cell answers are not 864 independent experimental replications. The three source datasets are also a purposive selection rather than a random sample of all possible datasets.

## Target selection and altered values

For each block, the code counted numeric occurrences of the target field using `Decimal`. It divided table positions into three contiguous thirds and randomly selected one target from each third, restricting selection to values unique numerically within the table. A block would fail preparation if a third lacked an eligible target.

The altered table was a copy of the original. For each target, a replacement was sampled uniformly between the source field's numerical minimum and maximum, then formatted to five decimal places. A candidate was rejected if numerically equal to any source-field value or a replacement already generated for that table. Exactly three cells changed.

Consequently, each target's original numeric value disappeared from the altered table. An incorrect return of that original value could be classified separately from an answer copied from another unchanged occurrence. This does not establish where an incorrect value came from internally.

The manipulation has limitations: generated values can have distinctive precision and need not follow the source distribution or its relationships with other fields. Selecting only unique targets also changes task difficulty. Thus the original/altered contrast includes the characteristics of the generated replacements, not just an abstract distinction between familiar and unfamiliar data.

The absent ID was always `999999`, asserted not to occur in the table. The four questions were shuffled once per block, then held in that order across conditions. This conspicuous absent ID makes abstention relatively straightforward and does not test plausible near-match identifiers.

## Input serialization and instructions

| Representation | Implementation |
|---|---|
| CSV | Header plus rows; source field order; LF line endings |
| JSON | Compact array of row objects; every value a JSON string |
| XML | `records` root containing `record` elements and child elements for each field |
| TXT | One record per line, with `field: value` pairs separated by ` | ` |

Each serialized table was deserialized locally and compared with its original ordered list of dictionaries. This checks data equivalence across representations. It does not equalize input token count, repeated labels, or visual structure.

The named sentence was `Table source: Kaggle Titanic.`, `Table source: Red Wine Quality.`, or `Table source: Medical Cost Personal Datasets.` The neutral sentence was `Table source: a collection of records.` This was the only change in the cue comparison. Meaningful column names and original IDs remained, so neutral naming did not anonymize the dataset.

All primary requests used this separate instruction:

```text
Answer the user task. Use only the information supplied in this request. No tools are available.
```

After the source sentence, the common lookup prompt was:

```text
Look up the requested cells in exactly the supplied table. Copy each value; do not calculate, estimate, or replace it using outside knowledge. If a record_id is absent, use NOT_FOUND. Return only a JSON object mapping each requested record_id to its value as a string. Do not include an explanation.
Requested cells: [serialized record_id/field questions]
TABLE:
[serialized table]
```

The bracketed text above denotes substitutions, not literal transmitted text. Exact prompts are in `cases.jsonl`. Internal target positions and expected answers were saved as metadata but omitted from the question list sent to the model. The model necessarily saw the target values inside the table; it did not receive a separately labeled answer key.

Output was always requested as JSON, regardless of input format. No enforced schema was used. The experiment therefore tests input representation under a fixed JSON-output requirement, not all combinations of input and output format. No reasoning trace was requested or recorded.

## Planned secondary components

| Component | Construction | Requests |
|---|---|---:|
| Synthetic lookup | Three tables each at 40 and 200 rows, four formats, neutral label, original version only | 24 |
| Large-table lookup | Two 800-row Titanic samples, original/altered, four formats, named only | 16 |
| Exact-prompt repeats | One extra call for each dataset's block 0 altered/named 200-row case in each format | 12 |
| Counting | Titanic and synthetic tables at 40, 200, and 800 rows, CSV/JSON | 12 |
| Initial no-table probes | Three targets from each of the first two 40-row blocks per dataset | 6 |
| Secondary total | | 70 |

Synthetic lookup records had `record_id` values from 1 to N, a category drawn from A/B/C, and a five-decimal `value` drawn uniformly from 0 to 1,000. They used three columns, fewer than the real-source tables, and were basic controls rather than matched synthetic twins. The common generator still constructed unused altered values before emitting only the original synthetic conditions. This consumes RNG draws and matters when reproducing later cases from the seed.

Large-table lookup used the same unique-target and replacement procedure as the main study. The two samples were separate from the main 40-row and 200-row blocks. Repeat requests reused exact prompts and answer keys; they were not new blocks and were excluded from primary inference.

Counting used only `record_id` and `survived`, both serialized as strings. Titanic labels came from `2urvived` in the first 891 rows. Synthetic labels used `int(rng.random() < .4)`. Each source/size combination had one table reused in both formats. These prompts requested integer `n_rows` and `n_positive`, with no fraction and no explicit Titanic name. Their instructions and response task therefore differed from Round 1.

Initial no-table probes named the dataset and explained that Titanic IDs meant PassengerId, while wine/medical IDs meant one-based local row indices. They requested value strings or `UNKNOWN`. However, they inherited the supplied-information-only instruction, which conflicted with their purpose. All six reached the output cap. They are retained as inconclusive diagnostics, and their revision is documented separately in [Round 3](round3_knowledge_followup.md).

## Preparation and execution

Preparation saved 358 fully constructed cases, a manifest, model settings, source hashes, and a SHA-256 hash of the serialized case plan before execution. It refused to replace a nonempty plan directory. Request order was shuffled with the same local RNG after all cases were built.

| Setting | Actual configuration |
|---|---|
| Requested and returned model | `gpt-5.6-luna` |
| Reasoning effort | `medium` |
| Lookup and initial no-table output cap | 2,048 tokens |
| Counting output cap | 4,096 tokens |
| Tools and storage argument | `tools=[]`, `store=False` |
| Conversation input | One current user message; no history references |
| Temperature, top-p, model seed | Not explicitly set |
| Client | `AsyncOpenAI`, Responses API |
| Client timeout and retries | 120 seconds, `max_retries=0` |
| Concurrent requests | Up to 4 |
| Recorded Python | 3.11.6 |
| Recorded packages | openai 2.54.0; python-dotenv 1.2.2; numpy 2.4.2; matplotlib 3.10.8 |

The runner explicitly selected the model without changing the personal `.env` default. It verified the saved plan hash before dispatch. Each request start was appended to `started.jsonl` before the API call, and each response was appended to `trials.jsonl`. Completion order can differ from shuffled submission order because requests ran concurrently. Joins use case IDs, not log-line position.

Logs include response ID, returned model, status, prompt hash, final text, token usage, elapsed time, and incomplete details. Returned model mismatch triggers a stop flag. API errors are recorded with exception type and HTTP status rather than full potentially sensitive exception bodies. Authentication/not-found errors or three accumulated errors trigger stopping; already-running calls may finish. No API errors or model mismatches occurred in this run.

Resume behavior skips IDs with recorded responses, including failed or incomplete ones. It refuses to resume automatically if a request was marked started but has no response record. It does not silently resend uncertain requests. All 358 planned IDs have response records: 352 completed and six initial knowledge probes were incomplete.

## Scoring definitions and implementation details

The scorer parses a JSON object, then compares each expected key. `numeric_equal` rejects booleans and unsupported types. It first compares stripped string forms, then attempts exact finite `Decimal` equality. This accepts equivalent numerical spellings such as `7.2500` and `7.25`, and accepts a numeric JSON value for value accuracy even when a string was requested.

For each requested key, the saved fields include:

- `correct`: response completed and its value matches the expected value under the comparison above.
- `literal_match`: response completed, value is a string, and it exactly matches the expected string without normalization.
- `absent`: expected answer is `NOT_FOUND`.
- `original_value_reversion`: in an altered table, a completed incorrect answer numerically matches that ID's replaced original value.

Whole-request `all_correct` requires every expected answer to be correct. It does not itself reject extra keys or enforce string types. `exact_keys` and `string_values` separately record those requirements. All main outputs passed both value and structure checks, so permissive numerical scoring did not change the reported perfect accuracy.

Counting uses this same scorer. Although its prompts request integers, the implementation does not enforce integer JSON type as strictly as the Round 1 scorer. This is another cross-round measurement difference. Missing values, malformed responses, and incomplete responses fail expected-answer correctness. API errors would be recorded separately as operational failures, not automatically interpreted as reasoning errors.

The analysis joins recorded responses to cases, verifies prompt hashes, and recalculates scores. Its aggregates operate on recorded requests; it does not automatically add a zero-score row for an entirely unrecorded planned request. The combined validation separately checks complete case coverage. That check passed, so there is no missing-request denominator issue in this run.

## Statistical summaries

Primary present-cell accuracy was summarized by format, dataset, size, name cue, and version. Absent-ID accuracy and complete-request accuracy were reported separately. Secondary components were not pooled into the primary comparisons.

For each of the 18 blocks, the analysis computed the difference between average present-cell accuracy under two conditions, averaging across the other factors. Contrasts were JSON minus CSV, XML minus CSV, TXT minus CSV, named minus neutral, and altered minus original.

A stratified block bootstrap used NumPy's `default_rng(18020261021)` for 10,000 draws. Within each of the six dataset-by-size strata, it resampled three observed block differences with replacement. Draws were averaged over all 18 block contributions. The point estimate was the mean block difference; 2.5th and 97.5th percentiles were reported in percentage points.

All observed block differences were zero, producing zero-width bootstrap intervals. These degenerate intervals do not establish equivalence or exclude effects on harder tasks. There were only three blocks per stratum, overlapping source rows, no power calculation, and no confirmatory multiplicity-controlled hypothesis test.

## Recorded outcomes and limitations

All 288 main requests were correct, including all 864 present-cell answers, all 432 altered-value answers, and all 288 absent-record checks. Each format had 216/216 correct present values and 108/108 correct altered values. All synthetic, large-table, and repeat lookup requests also passed.

Counting was correct in 9/12 requests. Both formats returned 891 rows and 342 positives for an 800-row Titanic table containing 303 positives. The 800-row synthetic table had 313 positives: CSV returned 313 and JSON returned 312. All smaller counting checks passed. Only one table was tested per source/size combination, so these count patterns require replication.

Main input token averages were CSV 2,249.1, JSON 4,090.5, XML 6,361.8, and TXT 4,466.2. Representation includes length and labeling changes. Direct IDs, clear copy instructions, clean tables, and distinctive replacements likely made retrieval straightforward; the ceiling leaves the format question unresolved at higher difficulty. Arbitrary wine/medical row IDs also provide weak cues for probing familiarity.

The model change from `gpt-6-luna` to `gpt-5.6-luna` prevents assigning cross-week improvements solely to lookup. Neither model name records a dated snapshot. The study did not test whether using an earlier generation reduces model changes over time.

## Verification, artifacts, and reproduction

Six offline tests check serialized target truth, equality across formats and name cues, exactly three changed cells, absence of replaced values, scorer behavior, and counting ground truth. The combined validator also checks case/response coverage, unique IDs, response model identifiers, prompt hashes, and rescoring. All passed for this run.

- [Study implementation](../experiments/week4_study.py)
- [Protocol](../experiments/week4_protocol.md)
- [Integrity tests](../experiments/test_week4_study.py)
- [Manifest](../results/week4_lookup/manifest.json), [runtime](../results/week4_lookup/runtime.json), and [environment](../results/week4_lookup/environment.json)
- Cases and exact prompts (`../results/week4_lookup/cases.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md)), [dispatch records](../results/week4_lookup/started.jsonl), and responses (`../results/week4_lookup/trials.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- [Analysis](../results/week4_lookup/analysis.json), [request scores](../results/week4_lookup/scored_requests.csv), and cell scores (`../results/week4_lookup/scored_cells.csv`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))

Offline analysis from the repository root:

```powershell
python -m unittest experiments.test_week4_study -v
python experiments/week4_study.py analyze --directory results/week4_lookup
python -m experiments.summarize_week4
```

For a new live replication, prepare a new directory using `week4_study.py prepare --directory NEW_DIRECTORY`, then use `run --directory NEW_DIRECTORY`. Only `run` sends API requests. Preserve the original artifacts. Exact source files, code, and the full RNG sequence are required to recreate the cases; a local seed does not guarantee repeat model outputs.
