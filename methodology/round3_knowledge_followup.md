# Round 3: Revised knowledge probes and recognizable Titanic records

This retrospective reference covers the 24 requests in `results/week4_followup`, collected on October 21, 2026. The follow-up was designed after interim Round 2 results showed perfect lookup accuracy. Its own case plan was frozen before these new responses were collected. It is explicitly exploratory and separate from Round 2's primary comparison.

## Why this round was added

Two issues motivated the follow-up. First, all six original no-table probes inherited an instruction to use only supplied information, even though their purpose was to ask about existing knowledge. They also exhausted their output allowance. Second, perfect lookup accuracy might partly reflect the model not knowing the original values of arbitrary selected rows. A more recognizable set of records could provide a clearer contrast between producing an original answer without a table and following a modified answer inside a table.

The follow-up therefore revised the six probes and introduced Titanic PassengerIds 1, 2, and 3. It did not replace or erase the incomplete results, add new primary blocks to the original analysis, or establish a general measure of memorization.

## Request allocation

| Component | Design | Requests |
|---|---|---:|
| Revised prior-knowledge probes | Same six Round 2 user prompts, revised instructions and larger output allowance | 6 |
| Recognizable-record prior probes | Same question about the first three Titanic fares, sent twice | 2 |
| Recognizable-record table lookup | One 40-row table; original/altered × named/neutral × four formats | 16 |
| Total | | 24 |

The revised probes contain 18 target values, six per dataset. The two recognizable-record prior probes contain six answers total, repeating the same three IDs. The 16 supplied-table requests contain 48 present-cell answers and 16 absent-record answers. These denominators describe repeated measurements; the recognizable table is one selected block.

## Revised no-table probes

Preparation read the frozen Round 2 cases and copied every case whose stage was `prior`. It preserved the user prompt, queried IDs, expected original values, and source-block metadata. It assigned a new ID ending `_knowledge_allowed` and a new stage, `prior_repaired`.

The separate instruction became:

```text
Answer from your existing knowledge. No tools, browsing, or table are available. If you do not know, say UNKNOWN rather than guessing.
```

The output allowance increased from 2,048 to 4,096 tokens. All other model-call settings remained the same as the Week 4 lookup study. Because both the instruction and allowance changed, the subsequent completion improvement cannot be attributed to either individually.

These prompts use three targets from each of Round 2's first two 40-row blocks per dataset. Titanic IDs refer to original PassengerIds. Wine and medical IDs refer to local CSV row order, which may differ across versions and may not identify a recognizable record to the model. `UNKNOWN` is consequently an abstention under this question, not proof that a dataset was absent from training.

The six incomplete original probes remain in Round 2's log and denominator. Revised probes are additional requests, not retries substituted for failed answers.

## Recognizable Titanic data construction

The follow-up called the same data loader as Round 2. It used the first 891 local Titanic rows, projected to `record_id`, `age`, `sex`, `pclass`, and `fare`, with values stored as strings. The source hash is the same one recorded in Round 2; the follow-up manifest itself does not independently repeat the data hashes.

The first three projected source rows supplied the target records. The shared edition omits their original source fare values pending redistribution review; the unchanged personal methodology retains them. Altered values below were specified by the experiment code:

| PassengerId | Original local Fare | Altered Fare |
|---|---|---|
| 1 | withheld | `20.12345` |
| 2 | withheld | `31.23456` |
| 3 | withheld | `42.34567` |

The remaining candidate rows came from rows after those three, excluding rows whose fare string matched any of the three original fare strings. The code sampled 37 candidates without replacement, combined them with the three targets, and shuffled the resulting 40 rows. This excludes other literal occurrences of the original target fares from the constructed context. Post-run validation also checked the supplied target values.

The construction RNG was `random.Random(18020261022)`. This is a seed value, not a collection date; the run occurred on October 21. The same RNG later shuffled request order.

The altered table copied the original and replaced the three target fares with the fixed strings in the table above. Unlike Round 2's replacement procedure, these values were hand-specified rather than sampled uniformly from the source range. They have conspicuous decimal patterns. This is a targeted demonstration, not a representative sample of natural data changes.

Only fares changed within the pair. Row order, IDs, other fields, question wording, and representation were held fixed for a given format/cue comparison. ID `999999` remained absent.

## Prompts and conditions

The recognizable prior probe used the revised knowledge-allowing instruction and this exact user prompt:

```text
For the original Kaggle Titanic training file train.csv, what are the Fare values for PassengerId 1, 2, and 3? No table is supplied. Return only JSON mapping the IDs to value strings, or UNKNOWN for values you do not know.
```

Two requests used that same prompt. Neither received a table or previous response. Because all 24 requests were shuffled and run concurrently, the prior probes were not necessarily dispatched before the table probes. No answers were carried between them, and table construction was not conditional on seeing a correct prior response.

The supplied-table conditions used the original Round 2 instruction to answer from supplied information. The name cue was either `Table source: Kaggle Titanic.` or `Table source: a collection of records.` The rest of the user prompt was:

```text
Look up fare for record_id 1, 2, 3, and 999999 in exactly the supplied table. Copy the supplied values rather than using outside knowledge. If a record is absent, use NOT_FOUND. Return only JSON mapping each requested record_id to a value string.
TABLE:
```

The appropriate table followed that text. CSV, compact string-valued JSON, XML, and labeled plain-text serialization reused the Round 2 functions. Questions were in fixed ID order here, unlike the per-block shuffled question order in Round 2. The JSON-output requirement was textual, not enforced through a schema. No explanation or internal reasoning trace was requested.

The 16 conditions crossed two versions, two name cues, and four formats. They share the same selected records and are not 16 independently sampled tables.

## Execution and logging

| Setting | Follow-up configuration |
|---|---|
| Model | `gpt-5.6-luna` |
| Reasoning effort | `medium` |
| Knowledge-probe output allowance | 4,096 tokens |
| Supplied-table output allowance | 2,048 tokens |
| Tools and storage argument | `tools=[]`, `store=False` |
| Input messages | One current user prompt per request |
| Temperature, top-p, model seed | Not explicitly set |
| Client | `AsyncOpenAI`, Responses API |
| Timeout and automatic retries | 120 seconds; `max_retries=0` |
| Concurrency | Up to 3, compared with 4 in Round 2 |

Preparation created a separate directory with `exist_ok=False`, saved all cases, and recorded the rationale and case-plan SHA-256 in the manifest. The runner verified the plan hash before dispatch. It refused to run if a response log or start log already existed; this implementation does not provide automatic resume for an interrupted follow-up.

Each request start was logged. Response records include case ID, prompt hash, instruction hash, returned model, response ID, status, final text, usage, score, elapsed time, and incomplete details. Instruction hashes were explicitly recorded because the follow-up uses two different instruction strings. Exceptions would be logged by type and HTTP status without silently retrying.

All 24 responses completed, with no API errors or truncation. Returned model identifiers were verified during combined post-run validation. The follow-up runner itself does not implement the primary runner's model-mismatch stop flag. It reused the installed Week 4 environment, but did not write its own separate runtime/package-version manifest. The existing Week 4 environment record is therefore the available software-version reference, not an independently captured follow-up environment.

## Scoring and validation

All cases used Round 2's scorer. Completed values were compared using stripped-string equality or exact finite decimal equivalence; booleans were rejected. Literal string matches and exact keys were separate checks. Whole-request accuracy required every expected answer to match, but did not itself enforce output types or reject extra keys.

For supplied-table requests, an altered answer equal to its replaced original fare was classified as an original-value reversion. Absent ID `999999` was expected to produce `NOT_FOUND`. For no-table requests, the expected answer remained the local original value. An `UNKNOWN` response was not scored as successful retrieval, but was summarized separately from an incorrect asserted value. These are different outcomes and should not be interpreted as equivalent evidence of ignorance.

The combined validation checked response coverage and uniqueness, returned model names, prompt hashes, per-case instruction hashes, and rederived scores. It deserialized each recognizable table, asserted 40 rows, and reconstructed the requested fares and missing-ID answer from that payload. The validation passed. This check verifies agreement with supplied data, not historical provenance or training-set membership.

## Recorded outcomes

The revised probes matched five of six Titanic fares. One Titanic value was incorrect. Wine and medical probes each returned `UNKNOWN` for all six queried targets. All revised probes completed, unlike the earlier six, but the changed instruction and token allowance remain confounded.

Both recognizable no-table probes returned all three original fares correctly. All 16 supplied-table requests returned the correct values and missing-ID answer, including all eight altered-table conditions. There were no original-value reversions in those changed tables.

This provides a narrow behavioral contrast: the model produced the original fares without a table and also followed altered fares when supplied. It does not show that an earlier recalled answer was actively suppressed within the same conversation, since requests were independent. It also does not demonstrate a particular reasoning process or prove that the original rows occurred in training.

The follow-up was chosen after observing a ceiling, used one especially recognizable table, and changed its lookup wording from Round 2. Its results are reported separately, not added as confirmatory evidence to the original format contrast. The fixed unusual replacements and explicit copy instructions limit generalization to subtler conflicts.

## Artifacts and reproduction

- [Follow-up implementation](../experiments/week4_followup.py)
- [Follow-up manifest and rationale](../results/week4_followup/manifest.json)
- Exact cases, instructions, and expected answers (`../results/week4_followup/cases.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- [Request-start records](../results/week4_followup/started.jsonl) and responses (`../results/week4_followup/trials.jsonl`, withheld; see [transfer review](../results/TRANSFER_REVIEW.md))
- [Combined validator](../experiments/summarize_week4.py) and [combined summary](../results/week4_overview/summary.json)

Run `python -m experiments.summarize_week4` from the repository root to validate and summarize both saved Week 4 runs without API requests. The combined report's 382 requests equal 358 from Round 2 plus these 24. Its 356 fully correct supplied-table lookup requests include primary and secondary conditions and should not be mistaken for 356 independent table samples.

The follow-up script's `__main__` calls `prepare()` only. It does not automatically execute `run()`. Its directory is fixed to the completed run, and preparation will refuse to replace it. A new live replication requires adapting the output directory and explicitly invoking the asynchronous runner after preparation. Do not delete or overwrite the existing directory to make a rerun proceed. The frozen `cases.jsonl` is the authoritative record of the actual follow-up stimuli.
