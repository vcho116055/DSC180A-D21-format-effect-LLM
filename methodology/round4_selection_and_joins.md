# Round 4: Attribute selection and retrieval across tables

This reference describes the next exploratory round developed on October 21, 2026 after reading `LAPTOP-CONTEXT.md`, the completed desktop studies, and the discussion of more demanding tasks. It belongs to the personal progress repository. The shared repository was not changed, and this round is not presented as a protocol jointly approved by Xiao.

## Motivation and chronology

The earlier 288 primary direct-ID requests were all correct. That ceiling left little ability to compare input representations. The new round adds selection by a conjunction of attributes and retrieval through a second table while retaining exact, locally computable answers and avoiding arithmetic as the primary task.

The repository was synchronized to laptop commit `73d743e186029a3246bf0e7b4ed88eae4ac32c42` before case preparation. The initial pull was blocked by session permissions on Git metadata; the user completed the pull. A temporary read-only review checkout had already confirmed the new context, whose actual filename uses a hyphen: `LAPTOP-CONTEXT.md`.

The protocol, both case batches, and source snapshots were frozen before model outputs. An initial conservative reservation limit was insufficient during local preparation and was increased before any plan files or API requests were written. No stimuli or scoring were changed in response to that preparation check. The frozen source and manifest record the final configuration.

## Sources and row construction

The real sources are the same hashed Titanic, Red Wine Quality, and Medical Cost files as Round 2. The [archive index](README.md) records their hashes and source dimensions. Titanic is still restricted to its first 891 local rows. Wine and medical use all eligible rows. The earlier data projections, meaningful column names, and one-based IDs for wine/medical are retained. These local versions remain unauthenticated against external canonical originals.

All values remain strings. The real-data loader checks unique record IDs and nonempty selected fields. The queried fields are Titanic fare, wine density, and medical charges. No labels are predicted, no model is trained on a data split, and no numerical calculation is requested.

Main sizes are 80 and 400 rows, with two sampled blocks for each of three sources and sizes: 12 real table blocks. Sampling is without replacement within a block but allows overlap between blocks. `random.Random(18020261023)` drives the complete main generation sequence and final request shuffle. The seed's digits are not the collection date.

Synthetic controls use fresh rows with `record_id`, three categorical fields (`group_a` drawn from 15 labels, `group_b` from 8, `group_c` from 4), and a five-decimal `value` uniformly drawn between 0 and 1,000. Two blocks at each main size are generated. They are simple task controls, not distribution-matched synthetic copies of each real source. No causal claim about familiarity is inferred solely from real-versus-synthetic comparisons.

## Selector requirements

Each block has three present queries, one for a target in each positional third of the sampled row order. The target output value must occur exactly once numerically in that block. Query criteria use two or three fields other than record ID, link ID, or the output field.

Every present selector must satisfy two constraints:

1. All criteria together match exactly one supplied row.
2. Dropping any one criterion leaves at least two matching rows.

This creates genuine partial-match distractors in the supplied table. For example, a selector cannot be resolved just by an age that already occurs once. The constraints are checked against the supplied rows, not against an external dataset or a model answer.

The generator enumerates eligible field combinations and selects among them with the seeded RNG. If a sampled table lacks a suitable target in a third, it draws another table, up to 50 attempts, before any model request. Attempt counts are recorded in the manifest. Conditioning on these constraints makes the resulting tables and targets a selected test set, not a representative random sample of all records.

The fourth selector is absent. Each of its individual attribute values occurs somewhere in the table, but their combination matches no row. This tests conjunction-based abstention rather than a conspicuous nonexistent ID. The direct-ID baseline uses the older absent-ID style, so absent-query comparisons between baseline and new tasks are not perfectly matched.

Questions use `q1` through `q4`; their order is shuffled once per block and held across conditions. The query IDs label answers, not source records.

## Tasks, table splitting, and edits

A seeded permutation assigns an arbitrary `link_id` to every row. The **attribute** task shows one flattened table, including that key and the output field, and asks the model to find the row matching all criteria and copy its output value.

The **join** task shows two labeled tables. `RECORDS_TABLE` contains the selection fields, native/local record ID, and link ID. `VALUES_TABLE` contains link ID and the output value. Its rows are independently shuffled. The model must select a record, use its key, and retrieve the corresponding output field from the second table. The second table remains complete, with exactly one value row per key.

For each block, the flattened and split layouts describe the same logical records and answers. The task comparison changes the retrieval operation, layout, repeated joining keys, and prompt wording together. It is not an isolated intervention on a single internal reasoning ability.

Original and altered versions differ in exactly three output cells. A replacement is generated within the full source field's range, formatted to five decimals, and rejected if numerically equal to any source value or an earlier replacement for that table. Each original target value is absent from the altered output column. Selectors, native IDs, link IDs, other fields, and table orders stay fixed. The precision, uniqueness, and selection constraints can make the alterations distinctive.

## Conditions and sample sizes

| Component | Construction | Requests |
|---|---|---:|
| Primary | 12 real blocks × 2 tasks × 2 versions × 2 name cues × 4 formats | 384 |
| Synthetic controls | 4 blocks × 2 tasks × 2 versions × 4 formats, neutral only | 64 |
| Direct-ID baselines | 12 real blocks × 4 formats, altered/neutral only | 48 |
| Exact-prompt repeats | Three real 400-row block-0 tables × 2 tasks × 4 formats, altered/named | 24 |
| Main batch | | 520 |
| Separate calibration | Four 80-row development blocks × 2 tasks × 4 formats, altered/neutral | 32 |

Every request contains three present queries and one absent query. The primary therefore contains 1,152 present-cell answers, including 576 from altered tables, and 384 absent-query answers. There are 12 primary sampled table blocks, not 384 or 1,152 independent replications. Two blocks per source/size stratum provide limited information about variability; source rows can overlap.

Calibration uses seed `18020261024` and one separate block from each real source plus one fresh synthetic block. These are not exact duplicates of main stimuli, although finite real sources allow overlapping rows. Both case batches were prepared before calibration. Repeats are exact copies of selected primary prompts and are excluded from primary block inference.

## Prompt and representation controls

Input formats reuse Round 2's CSV, compact row-object JSON, XML, and labeled TXT serializers. All preserve strings and field/row order. Join cases use explicit `RECORDS_TABLE` and `VALUES_TABLE` sections in every format. Local deserialization reconstructs each table and independently resolves each expected answer.

Named descriptions explicitly identify the source; neutral descriptions say `a collection of records`. Semantically meaningful columns and record IDs remain visible. No claim of complete anonymization is made.

The fixed instruction is the earlier supplied-information-only instruction. User prompts require matching all criteria exactly as written, using supplied tables, copying the output field, returning `NOT_FOUND` when no row matches, and responding only with the requested JSON query-ID mapping. The output format is constant across input formats and is not enforced through constrained decoding. Answer keys and target-position metadata remain local. No reasoning trace is requested or saved.

## Calibration gate and transport deviation

The frozen gate requires at least 30/32 strict whole-request successes overall and at least 15/16 per task, plus all 32 records, completed status, the correct model identifier, and valid output schemas. Main dispatch is forbidden if this gate fails. Calibration is reported separately and not used to tune these frozen prompts.

The first direct module launch attempted four calibration calls; all failed with APIConnectionError before returning a response ID or model output. The stop flag prevented the remainder from dispatching. The four logs, start records, and runtime record are preserved in [transport_attempt_01](../results/week4_selection/transport_attempt_01/README.md).

Read-only model-access checks succeeded with both urllib and the SDK through Python stdin. A documented restart then used the identical 32 frozen cases through that working invocation. This process-launch restart was not predefined in the protocol and is retained as an operational deviation introduced before any model answers. It is not a replacement of incorrect model responses. The restarted calibration completed 32/32 strictly correctly and passed the original gate.

Consequently, distinguish 552 planned experimental requests across completed batches from the four additional failed dispatches. Read-only access checks did not call the Responses endpoint. The completed output logs and the failed attempt are both retained.

## Execution settings and preservation

Requested model: `gpt-5.6-luna`; medium reasoning; Responses API; `tools=[]`; `store=False`; one current user message; no conversation references; provider-default sampling, with no temperature or model seed set. Maximum generated output is 4,096 tokens, compared with 2,048 in the earlier lookup round. Client timeout is 120 seconds, SDK retries are disabled, and up to four calls run concurrently.

The manifest saves model configuration, instruction hash, case-plan hashes, data hashes, generation seeds, base Git revision, dirty state, Python version, block sampling attempts, and reservation limits. Runtime files record SDK version and batch settings. Source snapshots include the new generator/runner, tests, protocol, imported Round 2 helper, and pinned dependency requirements. Credentials and source datasets remain ignored.

Starts are logged before dispatch. Responses record IDs, prompt and instruction hashes, returned model, status, output, usage, elapsed time, incomplete details, and scores. A model mismatch or relevant API errors stops further dispatch, although in-flight requests may finish. An already-started batch is not automatically resumed; uncertain outcomes require explicit inspection. Concurrent completion order is not treated as randomized request order.

## Scoring and analysis

The existing scorer compares completed values by stripped-string equality or exact finite Decimal equivalence and rejects booleans. Whole-request value correctness and strict success are separate: strict success additionally requires exactly the expected keys and string values. Literal copying is recorded too. Missing, malformed, incomplete, and extra-key outputs therefore cannot silently pass strict scoring.

The expected values are independently reconstructed by deserializing every payload, applying the criteria, and joining on link ID when needed. Integrity checks also compare logical data across formats, cues, and tasks; verify only three cells changed; ensure every criterion is necessary; and confirm original values disappeared from altered tables.

Incorrect cell answers are classified as replaced-original matches, other supplied values, false `NOT_FOUND`, answers to absent queries, invalid/missing answers, other values, or operational/incomplete failures. This taxonomy describes behavior rather than identifying memorization. Schema-only failures are reflected in strict request accuracy even if every expected cell value is correct.

Primary results are summarized by task and format, with altered values, absent queries, sources, sizes, and cues also reported. Synthetic, baseline, repeat, and calibration results stay separate. Contrasts compare averages within each sampled block. A 10,000-draw bootstrap resamples the two blocks inside each source/size stratum using NumPy seed `18020261023`. The intervals are descriptive and can collapse at ceiling. No powered superiority, equivalence, or confirmatory significance claim is made.

## Artifacts and reproduction

- [Frozen protocol](../results/week4_selection/source_snapshot/week4_selection_protocol.md)
- [Manifest](../results/week4_selection/manifest.json)
- Calibration prompts (`../results/week4_selection/calibration_cases.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md)) and responses (`../results/week4_selection/calibration_trials.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- Main prompts (`../results/week4_selection/main_cases.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md)) and responses (`../results/week4_selection/main_trials.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- Analysis (`../results/week4_selection/analysis.json`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- [Archived source](../results/week4_selection/source_snapshot/week4_selection.py) and [tests](../experiments/test_week4_selection.py)

Offline commands from the project root:

```powershell
python -m unittest experiments.test_week4_selection -v
python -m experiments.week4_selection analyze
```

Only `run` sends model requests. Existing batch logs prevent automatic repeat collection. A new replication needs a separate output directory and frozen plan; do not delete or overwrite the completed logs. A successful local seed reproduction reconstructs stimuli, not deterministic hosted-model outputs.

Final outcomes are reported in the run's analysis and report rather than inferred from the protocol. The six integrity tests passed before calibration. Post-run analysis checks recorded scores against rescoring, validates hashes and returned model names, and reconstructs payload truth again.
