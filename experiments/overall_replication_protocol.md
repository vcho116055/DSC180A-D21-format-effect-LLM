# November 3 repeated three-task study

This exploratory follow-up is authorized by the user's request to run the larger experiment across all three previously tested query types, with deeper analysis and no restrictive spending preference. The operator sets a $50 estimated-token spending backstop. Preserve all historical records. Freeze this protocol, stimuli, order, and implementation before new responses. No change to sample size, prompts, or grading in response to model accuracy is permitted.

## Questions and fixed sample

1. Do CSV, JSON, XML, and labeled TXT differ consistently in following supplied evidence?
2. Are observed errors stable under three identical, fresh API requests, and do they recur across fresh sampled tables?
3. How do direct-ID lookup, attribute conjunction selection, and two-table retrieval differ on matched tables?
4. Separately, how do actual file inputs, empirical replacement values, and 800-row tables affect outcomes?

| Stage | Construction | Requests |
| --- | --- | ---: |
| Calibration | One fresh synthetic 80-row block, 3 tasks x 4 formats x inline/file, altered/neutral, one call | 24 |
| Primary | 3 sources x 80/400 rows x 6 blocks x 3 tasks x original/altered x named/neutral x 4 formats x 3 repetitions | 5,184 |
| Breadth | IBM/avocado/credit card x 80/400 x 4 blocks x direct-ID only x 2 versions x 2 cues x 4 formats x 3 repetitions | 1,152 |
| Synthetic | 80/400 x 2 blocks x 3 tasks x 2 versions x neutral x 4 formats x 3 repetitions | 288 |
| Empirical edits | First 2 primary blocks per source/size x 3 tasks x altered x neutral x 4 formats x 3 repetitions | 432 |
| Longer-table stress | 3 core sources x 800 rows x 2 blocks x 3 tasks x 2 versions x neutral x 4 formats x 3 repetitions | 432 |
| Actual files | First 2 primary blocks per source/size x 3 tasks x 2 versions x neutral x 4 formats x 3 repetitions | 864 |
| Total | 2,808 distinct cases; calibration once, all other cases three times | 8,376 |

The primary sources are Titanic, wine, and medical. Their established projections permit necessary conjunctions with partial-match distractors. The extra sources extend direct lookup; they are not a matched three-task comparison. This avoids silently relaxing conjunction constraints for mostly unique fields in the other projections. The study is purposive, not a random sample of all datasets or models, and is not powered for a specified minimum difference.

## Construction and equivalence

Use source files with hashes matching the historical manifests. Seed 18020261104 fixes generation; generation and each stage/repeat's randomized order are frozen before dispatch. Reuse the existing supplied-data projection, serializers, selector constraints, value scorer, prompt wording, and uniform min-max replacement rule. Use the Round 4 direct-ID variant to hold the q1-q4 output structure and present targets fixed across tasks; it is not a literal rerun of Round 2's record-ID output schema.

Each block has three present targets, one per positional third, and one absent query. In attribute and join tasks all selector criteria together identify exactly one present row; dropping any criterion leaves multiple candidates. Every individual value in an absent conjunction occurs somewhere, but no row satisfies the combination. Direct lookup uses absent ID 999999 and therefore has an easier missing-record construction. Task differences also change layout, prompts, and joining keys; do not interpret them as isolated internal reasoning abilities.

Alter exactly the three present queried output cells, preserving selectors, row order, linking keys, and all other values. Uniform replacements are absent numerically from the full source field; original target values disappear from altered output columns. Empirical replacements instead draw existing source-field strings whose values are absent from the selected table and previous replacements. This keeps observed precision and field scale but still conditions on uniqueness. The empirical arm reuses primary tables/queries and compares to their altered/neutral uniform counterparts, with no changes to primary scoring.

For joins, put selectors and link_id in RECORDS_TABLE and shuffled link_id/value rows in VALUES_TABLE. Flat tasks include the same logical records. Deserialize all payloads and independently reconstruct expected answers. Check source hashes, target uniqueness, necessary criteria, absent conjunctions, original/altered differences, file equivalence, and repeat identity before calls. Different sampled blocks can overlap in source records; 800-row Titanic subsets overlap especially heavily. Quantify overlap; never count cells or repeated conditions as independent tables.

Files are genuine native .csv/.json/.xml/.txt assets, sent through Files API uploads and referenced by file_id. Join requests receive two files labeled by their table roles. Compare files only with the exact preselected primary inline/neutral counterparts. Files contain supplied rows, never answer keys. CSV has provider-side spreadsheet augmentation, while other text/code types use extraction, so this is an end-to-end delivery comparison and cannot isolate serialization. All files are at most 400 rows per table in the file arm, below the documented first-1,000-row spreadsheet parsing limit.

## Execution, calibration, and stopping

Keep GPT-5.6 Luna, medium reasoning explicitly set on every request, no tools, no history or conversation references, store=False, 4,096 max output tokens, provider-default sampling, no temperature/model seed, no SDK retries, 180-second timeout, at most 12 concurrent requests. Local generation seeds do not make model outputs deterministic. Repeat the exact case three times in fresh requests; finish each randomized round before the next. Treat contemporary repeats separately from historical observations and the preceding feasibility pilot.

Calibration includes all 3 tasks and, for joins, both file inputs. Require all 24 calibration records, correct returned model, completed response, exact keys/string values, and correct values. If the gate fails, preserve results and stop this frozen main batch. No prompt tuning follows calibration output. Ordinary incorrect completed main answers are retained and do not stop or trigger replacement requests.

Log starts before submission and outputs/usage/status after completion. Preserve raw final outputs, returned reasoning configuration, instruction/payload hashes, response IDs, file IDs, source snapshots, actual package versions, Python/OS, Git base and dirty state, and lockfile hash. The actual runtime is Python 3.11.6/OpenAI 2.54.0, as in the successful file pilot; installed uv could not resolve the pinned 3.12.14 interpreter. Record this deviation and all installed versions. Do not change the project pins or claim a locked run.

Reserve conservative worst-case token spend before each dispatch: inline input UTF-8 bytes plus 4,096 overhead at $0.50/M, plus output allowance at $1.80/M; file requests reserve the full documented 1,050,000-token context at those rates because augmentation expansion is unobservable. Rates cover long-context and input-cache-write multipliers. Count successful usage conservatively without cache discounts; retain full reservation when billing is uncertain. Accounted spend plus concurrent reservations must fit $50. These are model-token estimates, excluding tax or unreported provider fees. Stop for insufficient reservation, model mismatch, missing usage, exceeded reservation, authentication/access/not-found/rate-limit errors, or three API errors. Preserve in-flight completions. No automatic retries. A safe resume skips logged request IDs and requires every start to have a response record; ambiguous starts block resume. A completed batch is never automatically rerun. Delete only study-created remote files after collection, logging cleanup outcomes.

## Predefined analysis

The main unit for comparisons is a sampled table block. Score individual calls, then average the three binary success indicators within a case. Never average numeric answer values, replace failed calls with successful repeats, or report majority voting as single-call accuracy.

Report strict whole-request accuracy, present-cell accuracy, altered-cell accuracy, absent-query accuracy, literal-copy accuracy, schema/completion incidence, and original-value reversions. Separate operational failures, false NOT_FOUND, answers for absent queries, other supplied values, replaced originals, and other/invalid outputs. Trace supplied-value errors to partial-match rows as a descriptive diagnostic, not a mechanism claim. Tabulate task, format, source, size, cue, version, alteration type, delivery, and repetition.

Primary format contrasts: JSON-CSV, XML-CSV, TXT-CSV in strict request accuracy, equal-weighted within primary table blocks, retaining task/cue/version/repeat pairing. Use 10,000 stratified block bootstrap draws (six blocks in each source/size stratum), seed 18020261105. Report descriptive 95% intervals and 98.333% intervals for the three prespecified format contrasts (Bonferroni family adjustment). Task-specific, cell-level, naming, size, delivery, and empirical-edit contrasts are exploratory with descriptive 95% intervals; do not cherry-pick unadjusted comparisons as confirmatory. Bootstrap intervals can collapse at ceiling and do not prove equivalence. Pooled averages must not obscure task-specific differences.

Report each unique case's 0/3, 1/3, 2/3, or 3/3 strict successes, parsed-answer disagreement, and cell-level error recurrence across repetitions. Count errors by distinct block/query as well as by call. Use repeated patterns to distinguish localized persistent difficulties from occasional observed variability, without claiming internal causes.

Analyze stages separately. For file/uniform-neutral and empirical/uniform-neutral comparisons, use only the exact preselected shared blocks, tasks, and versions. If interrupted, show planned versus recorded counts and summarize only complete matched units for contrasts; never silently mix unbalanced conditions. Historical comparisons are contextual and cannot isolate time, model alias behavior, prompt changes, or software environment effects.

Deliver a detailed Markdown report, machine-readable analysis and audit, scored request/cell tables, error examples retained locally, and standalone plots. State whether a consistent format advantage was observed, what types of errors recur, how reliable altered values and abstention are, and what remains unresolved. A nonsignificant or zero observed contrast is not proof that formats are equivalent; no result establishes training-data leakage.

Official documentation checked November 3, 2026:

- https://developers.openai.com/api/docs/models/gpt-5.6-luna
- https://developers.openai.com/api/docs/guides/file-inputs
