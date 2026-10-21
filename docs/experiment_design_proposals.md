# Proposals for the experiment-design call

Draft for discussion, October 20, 2026. Based on `initial_findings.md`, the Luna pilot report, and the existing experiment script. These are proposed decisions, not an approved protocol.

Suggested opener: “I think our next experiment should focus on whether the model follows changed values in the supplied table. The counting experiments mix that question with arithmetic ability. Can we agree on a simpler task, one shared model, and scoring rules before expanding?”

## 1. Make direct lookup the primary task

Ask for one field from one uniquely identified record: “Using only this table, return the Age for Passengerid X. Return UNKNOWN if the record is absent.” Keep counting and fractions as a separate diagnostic arm.

For every table, create an original and edited version. Change the queried value while preserving its type and plausible range; keep all other cells, row IDs, and ordering identical within the pair. Each version goes in a fresh request. Do not tell the model the old value or show both versions together.

Use a field with multiple possible values, such as Age or Fare, for the main lookup task. A binary survival label provides only two choices, so returning the original label is weak evidence by itself. Ensure each edited value differs from the original and is not a missing value.

This measures response to supplied evidence with less arithmetic burden. Lookup still involves search and attention, so it does not isolate memorization completely. It also changes the research question from aggregate statistics to individual values; retain a small aggregate arm later if both behaviors matter.

## 2. Use one shared primary model

Selected primary model: both partners use **`gpt-5.6-luna`**, initially with medium reasoning. We prefer an older model to reduce potential model drift, but lower update risk is an assumption, not a guarantee. The completed October 14 UTC pilot used **`gpt-6-luna`** and remains a separate exploratory result; the new model needs its own calibration. Use **`gpt-6.1-sol`** as a later capability comparison if budget allows. Choose models before examining the main results; do not choose whichever gives the most suspicious failures.

Official OpenAI documentation positions Luna for cost-sensitive, high-volume work and Sol as a balance of intelligence and cost. That supports this practical choice; it does not establish which model is more likely to rely on prior knowledge. See the [official model catalog](https://developers.openai.com/api/docs/models).

Record requested and returned model identifiers, date, reasoning setting, sampling settings where supported, token caps, and tool configuration. Pin a model snapshot if one is available. Use the API with fresh requests and no tools for the primary experiment.

## 3. Keep the main comparison small and paired

Start with Titanic and a fixed table size of 100 rows. For each original/edited table pair, cross:

| Factor | Conditions |
|---|---|
| Input format | CSV / compact row-object JSON |
| Explicit identity cue | Titanic named / neutral description |
| Supplied value | Original / edited |

Within every format and naming comparison, use the exact same rows, values, order, question, and answer specification. Neutral wording removes an explicit cue; it does not make recognizable records anonymous.

Keep the response format fixed, for example `{"record_id": X, "value": Y}`, with a defined representation for UNKNOWN. JSON input and JSON output are separate choices.

Record input tokens. The existing 802-row comparison used 3,325 CSV tokens and 8,934 JSON tokens, so any difference includes serialization length and repeated keys. Describe this as the practical effect of these CSV/JSON representations. A claim about syntax independent of length would need another experiment.

## 4. Add controls that distinguish different failures

- **Matched synthetic tables:** same schema, size, value ranges, target-position schedule, and edit procedure. These estimate lookup difficulty without the same known dataset identity.
- **Unedited counterparts:** establish whether the model can retrieve each target before evaluating its response to an edit.
- **Missing-record trials:** remove the requested record and expect UNKNOWN. These test whether it invents an answer when evidence is absent.
- **Small no-table probe set:** ask for selected original values in separate fresh calls. Repeated correct original answers would support availability of those values without the table. Failure to recall them does not prove absence of prior knowledge. Keep these probes out of the main prompts.

Distribute target records across the beginning, middle, and end. Randomize trial execution order. Keep ordering fixed within each paired comparison; vary it across independently generated tables.

## 5. Agree on outcomes before running

Primary outcome: **accuracy on edited-table lookups**, compared within matched tables across CSV/JSON and named/neutral conditions.

For edited trials, classify responses as supplied-value correct, original-value match, other incorrect value, UNKNOWN, or invalid/incomplete output. Track pair success separately: correct retrieval on both original and edited versions. Report all trials, rather than silently excluding pairs whose originals were incorrect.

Original-value matches are a descriptive outcome, not a memorization rate. Compare their frequency with synthetic controls and consider value frequency and chance matches. Evidence becomes more suggestive if original-value matches recur across distinct targets, exceed matched-control behavior, and increase with explicit dataset naming. Even that would not prove training-data leakage or identify the source of prior knowledge.

Generate expected answers locally. Define numeric equivalence, missing-value handling, invalid-output scoring, API failure handling, and retries in advance. Separate service failures from completed but incorrect responses. Analyze comparisons as paired; repeated calls and multiple targets from the same table are not independent dataset replications.

## 6. Run a calibration stage, then freeze the protocol

First use separate development examples to check unique IDs, correct serialization, valid edits, output parsing, and whether the lookup task is feasible. Agree on a practical synthetic-lookup accuracy threshold before this calibration. If it fails, revise task difficulty and recalibrate before the main run. Do not tune prompts against the main test tables.

Suggested small main batch:

- 10 independently sampled Titanic table pairs × 2 versions × 2 formats × 2 naming conditions × 2 fresh repeats = **160 calls**.
- 10 synthetic table pairs × 2 versions × 2 formats × 2 fresh repeats, using neutral descriptions = **80 calls**.
- Predeclare a separate small allowance for missing-record and no-table controls.

The 240-call batch is a planning starting point, not a powered sample-size claim. Table samples can overlap in source records, and all Titanic samples come from one dataset. Use distinct targets where practical, report uncertainty at the table-pair level, and limit conclusions accordingly. Estimate cost from calibration token usage and agree on a spending cap before launch. Expand table sizes, datasets, and models after establishing that this protocol answers the intended question.

## Decisions to leave the call with

1. Is the main question formatting's effect on following supplied evidence, or specifically substitution of prior dataset values? Proposed priority: evidence-following, with original-value substitution as a secondary outcome.
2. Adopt direct lookup with original/edited pairs, and choose the target field and table size.
3. Confirm GPT-5.6 Luna settings as the shared primary model and whether Sol replication is in scope.
4. Approve the conditions, controls, scoring rules, calibration gate, and budget.
5. Obtain Xiao's exact Iris prompts, source/version, retained rows, expected values, model identifier, and responses. Treat the current Iris observations as exploratory until these are reconciled.
6. Verify Titanic provenance and the meaning of the local columns before making claims about historical/original values. Until then, score against the supplied local file and call them local reference values.
7. Divide work: one partner owns table generation and ground truth; the other independently checks payloads and scoring. Both use the same harness. Review the protocol together before executing it.
