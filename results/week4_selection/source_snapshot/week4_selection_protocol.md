# Round 4: Attribute selection and two-table retrieval

Plan written before response collection on October 21, 2026. This is an exploratory extension of the direct-ID study, informed by `LAPTOP-CONTEXT.md` and the desktop discussion. It is a personal-repository experiment, not a change to the shared project's approved protocol.

## Question and fixed design

Does input representation affect following supplied values when the model must select a row from multiple attributes, or select it and then retrieve a field through a second table? Keep `gpt-5.6-luna`, medium reasoning, four input formats, fixed JSON output, no tools, and fresh single-message requests. No model sampling seed or temperature is specified.

Primary: three local sources (Titanic, wine, medical), two sizes (80, 400), two independently sampled blocks per source/size, two tasks (attribute, join), original/altered, named/neutral, and four formats. This gives 12 blocks and 384 requests. Three present queries and one absent query occur in every request. Primary answers total 1,152 present cells and 384 absent queries, with half the present answers from altered tables.

Secondary: 64 fresh synthetic requests (two sizes, two blocks, two tasks, two versions, four formats, neutral only); 48 direct-ID baseline requests (one altered/neutral request per real block and format); 24 exact-prompt repeats (400-row real block 0, altered/named, both tasks and all formats). Total planned main batch: 520 requests. A separate 32-request calibration uses disjoint development stimuli, not additional primary blocks. Total maximum if the calibration gate passes: 552 requests.

## Construction and matching

Use the same local projections and hashes as Round 2. All fields remain strings. Sample without replacement within blocks; different blocks can overlap. Synthetic rows have a fresh numeric value and three categorical attributes, not distribution-matched twins of the sources. Synthetic controls establish basic task feasibility, not an isolated effect of familiarity.

For each real or synthetic block, choose three targets, one in each positional third, whose output values are unique numerically within the block. A query uses two or three non-ID, non-output attributes. All criteria together must match exactly one row. Dropping any single criterion must leave at least two matches. Thus every criterion is needed to resolve the supplied table, and single-attribute shortcuts do not suffice. Select among eligible combinations with a seeded RNG. If a sampled table lacks eligible targets, reject it during preparation, before model calls, for at most 50 draws; record the number of attempts.

The absent query combines attribute values present individually in the table but whose combination matches no row. There is no conspicuous impossible sentinel in its selector. Questions use fixed query IDs q1-q4, shuffled within each block and held across conditions.

Generate one arbitrary link_id per record. The attribute task shows one flattened table. The join task shows the same selection fields and link_id in `records`, with output values in a separately ordered `values` table keyed by link_id. It does not require a numerical calculation. Value-table ordering is shuffled independently of record ordering. Keys, order, selectors, and values are fixed across formats, cues, and versions. Task contrasts include the change in layout and required retrieval operation, not an isolated latent measure of reasoning.

In altered tables change only the three queried output cells. Replacements are newly generated, five-decimal, in-range values absent numerically from the source field. Replaced originals no longer occur in the block's output field. All selectors and joining keys stay unchanged. The precision and uniqueness restrictions can make changes distinctive and limit generalization.

CSV, compact JSON, XML, and labeled TXT use the existing serialization functions. Join inputs have two explicitly labeled table sections in every format. Name cues change only the source-description sentence; column semantics and local record IDs remain visible. Output always maps query IDs to strings, using NOT_FOUND for an absent selection. No step-by-step reasoning or enforced output schema.

## Calibration and execution gate

Use one separate 80-row development block from each real source and one fresh synthetic block; altered/neutral only, two tasks and four formats: 32 requests. Development blocks use a separate seed and are never added to primary estimates. They may share source rows with main blocks because the sources are finite, but not exact generated stimuli.

Freeze all calibration and main cases before calibration responses. Gate: at least 30/32 strict whole-request successes overall and at least 15/16 per task. Also require all 32 response records to exist, with no API errors, truncation, model mismatches, or invalid schemas. If the gate fails, retain calibration results and do not run this frozen main batch. A revision would need a separately documented protocol rather than silently changing these prompts.

Responses API, tools=[], store=False, medium reasoning, max_output_tokens=4096, SDK retries disabled, timeout 120 seconds, at most four concurrent requests. A larger allowance than the older lookup study is deliberate for the harder tasks and is a cross-round difference. Stop dispatch after authentication/model mismatch or three API errors; already-running requests may finish. Log starts before dispatch, refuse ambiguous resumes, and retain incomplete responses without replacement. Use conservative byte-based input/output reservations and a combined calibration-plus-main ceiling of $13, within the original quarter allowance including previous recorded runs. This conservative reservation is not an expected bill. An initial $8 reservation limit failed locally during preparation, before any requests or plan files were written; the limit was raised before freezing cases, with no changes to stimuli or scoring. Actual usage estimates and caps stay in technical logs rather than the class summary.

## Scoring and analysis

Reconstruct answers from every serialized payload, independently matching selector criteria and joining on link_id where applicable. Present selectors must have exactly one match and the absent selector none. Verify all representations agree, both task types resolve the same values, only three output cells change, and all partial-match constraints hold.

Value scoring uses the existing Decimal-equivalence scorer. Report strict whole-request correctness separately, requiring exact keys and string values as well as every value correct. Incomplete, malformed, missing, or extra-key outputs fail strict correctness. Classify replaced-original matches separately from other supplied values, false NOT_FOUND, and other errors. This is an error taxonomy, not a memorization detector.

Report primary task-by-format accuracy, altered-value accuracy, absent-query accuracy, completion/schema incidence, size/source/cue results, and paired original/altered success. Keep synthetic, baseline, repeat, and calibration outcomes separate. Compare formats and tasks within sampled blocks, not by treating every cell/request as independent. A 10,000-draw stratified block bootstrap resamples the two blocks within each source/size stratum; with only two blocks it is descriptive and can degenerate at ceiling. No confirmatory significance or equivalence claim. Overlapping source rows and purposive datasets further limit inference.

Do not increase difficulty or add runs simply to obtain an error or a preferred format ranking. If these tasks also reach ceiling, report that result and consider a separately planned future task.

## Provenance and preservation

Freeze prompts, selectors, answer keys, generation seeds, source hashes, Git base revision/dirty status, package versions, instruction hash, and current source/protocol snapshot before calls. Store responses, statuses, returned model IDs, usage, and timing separately. Never send local answer keys to the API. Preserve all earlier frozen rounds. The laptop pilot model edits are forward-looking and do not change the historical GPT-6 results.

API settings and estimate rates were checked against [the official model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [reasoning documentation](https://developers.openai.com/api/docs/guides/reasoning) on October 21, 2026. These establish available settings, not a guarantee of unchanged hosted behavior.
