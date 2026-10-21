# Luna exploratory pilot

Run: October 13, 2026 (America/Los_Angeles); October 14 UTC.

## Main finding

On one 802-row Titanic CSV trial, Luna returned the original dataset's 891 rows and 342 positives instead of the supplied 802 rows and 310 positives. This is the proposed full-dataset-answer failure pattern. It is evidence consistent with reliance on a familiar statistic, not proof of raw training-data memorization. Counting errors occurred in other conditions, including on the full table.

## Setup

- Model: requested and returned `gpt-6-luna`; reasoning effort `medium`; maximum generated tokens 8,000. No tools. `store=False`. No conversation IDs, previous response IDs, or reused output; the explicit-history positive control is the sole exception.
- Each table trial requested the same JSON answer containing row count, positive-label count, and positive fraction. Only input serialization changed between CSV and compact row-object JSON. Output schema was requested in text, not enforced through constrained decoding.
- Synthetic tables: 20 and 100 freshly generated binary records, each tested once per format.
- Titanic: first 891 rows of the local file, projected to `record_id` and `survived`. The local source uses `Passengerid` and `2urvived`. The last 418 rows were excluded because their labels are all zero and their provenance has not been verified. No historical ground-truth claim is made about the retained labels: scoring is against the supplied local values.
- The 100-row sample had 38 positives. In its modified counterpart, 20 randomly selected zeros became ones, yielding 58 positives. Original and modified tables retained identical row IDs and order; each was tested twice per format.
- A separate uniform sample of 802 rows contained 310 positives. Full 891-row and 802-row tables were tested once per format. Sampling and trial ordering used seed 1802026.
- One random-code isolation test, one explicit-history positive control, and one no-table prior-knowledge probe preceded the randomized table trials. The target model did not receive the research discussion or expected answers.

## Results

| Table | Correct rows / positives | CSV returned rows / positives | JSON returned rows / positives |
|---|---|---|---|
| Synthetic, 20 rows | 20 / 7 | 20 / 7 | 20 / 7 |
| Synthetic, 100 rows | 100 / 34 | 100 / 34 | 100 / 34 |
| Titanic sample, original; two runs per format | 100 / 38 | 100 / 38; 100 / 38 | 100 / 37; 100 / 38 |
| Titanic sample, modified; two runs per format | 100 / 58 | 100 / 58; 100 / 58 | 100 / 60; 100 / 60 |
| Titanic 90% sample | 802 / 310 | **891 / 342** | 800 / 307 |
| Titanic full retained table | 891 / 342 | 891 / 340 | 891 / 355 |

All fields were correct in 9/16 table responses: CSV 6/8, JSON 3/8. These are descriptive counts from very few distinct tables; repeats of one table are not independent dataset replications. No significance or general superiority claim is warranted.

The 802-row CSV answer was 0.383838, the full-data fraction. Its true fraction was 0.386534. The JSON answer was 0.383750, close to the familiar fraction, but accompanied by different incorrect counts. Numerical proximity alone cannot identify the cause.

- **Isolation:** the initial request received a random 128-bit code. A fresh request returned `UNKNOWN`; an explicit-history control returned the exact code. This detects no carryover in this one check, not universal absence of memory.
- **Prior knowledge:** without a table, Luna returned 891 rows, 342 positives, and fraction 0.383838. This shows availability of the familiar statistic in that response, not where it was learned.
- **Changed evidence:** CSV followed the 38-to-58 change exactly on both repeats. JSON shifted substantially too, but returned 60 rather than 58 on both modified trials. Thus the small-table behavior is not simply repetition of the full-data answer.
- **Large-table arithmetic:** neither format returned correct counts on the 891-row table. The proposed full-table sanity check therefore failed for this prompt and setting.
- **Input length:** the 802-row CSV request used 3,325 input tokens versus 8,934 for JSON. The format comparison includes this length difference and repeated field names.

## Validation

Four direct script launches encountered connection-refused errors before receiving a model response. Their sanitized logs are in separate sibling run folders and are not included in experimental results. The same script subsequently ran successfully through a PowerShell Python-stdin invocation. There were no automatic API retries. Successful responses all had completed status; none hit the output cap.

Each recorded CSV/JSON payload was independently reparsed locally after execution, and its row count and positive count matched the recorded ground truth. Source hash and settings are in `metadata.json`; exact prompts, final answers, usage, and scoring are in `trials.jsonl`. Internal reasoning content was not requested or recorded.

## Recommended next experiment

Replicate the 802-row comparison across independently sampled subsets and fresh calls. Cross CSV/JSON with named versus neutral dataset descriptions while keeping the numerical table fixed within each pair. Neutral naming removes an explicit identity cue but does not guarantee the rows are unrecognizable. Include size-matched synthetic arithmetic controls, and specify selection/scoring rules before viewing outputs. Count exact full-data answers separately from other counting errors. Do not interpret general error rates as memorization rates.

This pilot was exploratory, not preregistered. It supports further investigation of full-dataset answer substitution while showing why matched arithmetic controls are essential.
