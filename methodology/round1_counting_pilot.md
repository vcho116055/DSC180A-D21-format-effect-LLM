# Round 1: Counting, changed labels, and request isolation

This is a retrospective technical description of the successful run in `results/luna_pilot_20261014T031651Z`. Collection occurred on October 13, 2026 in Los Angeles, corresponding to October 14 UTC. The reference implementation is [exploratory_luna.py](../exploratory_luna.py). The script is present in the working repository; this round did not save a separate immutable source snapshot or a complete package-version manifest.

Synchronization note: subsequent laptop edits changed the working pilot script's future model selection, estimate rates, and result-folder prefix. The recorded historical run still used `gpt-6-luna`. The linked working script is therefore a descendant of the original runner, not a frozen copy of that run's source. Inspect the historical metadata and Git history when reproducing historical settings; a new live execution of the current script uses its current settings.

## Purpose and scope

The pilot tested whether a model could count supplied rows and positive binary labels, whether CSV versus JSON changed its answers, and whether altered or reduced Titanic data elicited familiar full-dataset statistics. It also checked one instance of request isolation and included a no-table probe of the original Titanic statistic.

This was exploratory. There was no formal power calculation, confirmatory hypothesis test, or public preregistration. Sixteen table requests plus four setup/diagnostic requests constituted the successful round. The design did not fully cross source familiarity, table size, naming, and format; those differences limit causal interpretation.

## Data and preprocessing

### Local Titanic source

The input was `data/titanic.csv` (local only; see [data setup](../data/README.md)), a transformed file with 1,309 rows and 28 header fields. The file includes repeated `zero` columns and the unusual label name `2urvived`; it is not treated as an independently verified copy of the original competition training file.

The script used `csv.reader`, located `Passengerid` and `2urvived` by their header positions, and retained the first 891 data rows in their original order. Each retained row became:

| Experimental field | Local source | Conversion | Meaning in the experiment |
|---|---|---|---|
| `record_id` | `Passengerid` | Python integer | Record identifier |
| `survived` | `2urvived` | Python integer | Binary value to count |

All other columns were discarded. The script asserted that the retained table had 891 rows and 342 positive labels. The remaining 418 local rows were excluded. Their all-zero labels and unverified provenance were not used as test truth. No imputation, scaling, or historical label verification was performed.

The recorded SHA-256 is `5c3c684032fa169dcc8b4853e06a9a5296fbb2f1b8061a5527710c418f5feac4`. Ground truth refers to these retained and subsequently supplied values, regardless of their external provenance.

### Synthetic data

A single `random.Random(1802026)` generator produced all table randomness and the final trial shuffle. For each size, 20 and then 100, record IDs ran from 1 to the table size. A label was assigned using `int(rng.random() < .43)`. The realized tables contained 7 and 34 positives, respectively. Each generated table was reused unchanged in both formats.

These are simple binary controls, not distribution-matched synthetic replicas of the full Titanic feature set. Their smaller sizes also mean they do not control counting difficulty in the 802-row and 891-row conditions.

### Sampled and modified Titanic tables

After synthetic generation, the same RNG sampled 100 retained Titanic rows without replacement. The sampled order was preserved in the prompt. This table contained 38 positives.

The script copied that table, sampled 20 positions whose labels were zero, and changed those labels to one. The modified table therefore had 58 positives, with identical record IDs and ordering. Only the selected labels changed. This deliberately tests responsiveness to changed supplied evidence.

A later call to the same RNG sampled 802 of the 891 rows without replacement. This is approximately a 90% subset, containing 310 positives. The full-table condition used all 891 rows in source order. There was only one sampled table at each of these sizes; repeated requests on the 100-row tables were not newly sampled datasets.

## Conditions and request counts

| Component | Tables or conditions | Formats | Requests per format/condition | Total requests |
|---|---|---|---:|---:|
| Synthetic counting | 20 and 100 rows | CSV, JSON | 1 | 4 |
| Small Titanic counting | Original 100 rows and modified 100 rows | CSV, JSON | 2 | 8 |
| Large Titanic counting | 802 rows and 891 rows | CSV, JSON | 1 | 4 |
| Isolation code seed | One random code | Plain prompt | 1 | 1 |
| Fresh-request isolation probe | No earlier messages supplied | Plain prompt | 1 | 1 |
| Explicit-history positive control | Earlier code and ACK supplied | Message sequence | 1 | 1 |
| No-table Titanic statistic | Full-dataset statistic queried | Plain prompt | 1 | 1 |
| Total | | | | 20 |

The first four calls were the code seed, fresh probe, history control, and no-table statistic probe, in that order. The 16 table cases were shuffled with the same seeded RNG and sent afterward. Requests were executed sequentially, not concurrently.

## Prompt and representation

The instruction passed separately from the user prompt was:

```text
Answer the task using only the information available in this request. Do not use tools.
```

Synthetic tables were introduced with `A table of records.` Titanic tables were explicitly introduced as records derived from the Kaggle Titanic dataset. The common table-task wording was:

```text
Each row is one record. survived is a binary integer: 0 or 1. Calculate using exactly the supplied rows, not a larger dataset. Return only a JSON object with n_rows, n_positive (count of survived=1), and fraction_positive (n_positive/n_rows, rounded to six decimal places). Do not include an explanation.
TABLE:
```

CSV used the header `record_id,survived`, followed by one record per line with LF line endings. JSON used a compact array of row objects, serialized with separators `(',', ':')`. Both JSON fields were numbers, unlike Round 2's string-valued JSON. The numerical contents and ordering were identical across the paired representations.

Every table condition requested JSON output. There was no enforced response schema or constrained decoding. The prompts requested final answers only. No step-by-step reasoning text was requested or saved; the configured reasoning effort should not be confused with an observable reasoning trace.

The no-table prompt explicitly named the original Kaggle `train.csv` and supplied its 891-passenger size, then requested row count, survivors, and fraction. Thus the row-count part was provided in the question. The supplied-information-only instruction also makes this an imperfect probe of unrestricted prior knowledge. A correct response demonstrates availability of the statistic in that request, not its origin.

## Isolation procedure

`secrets.token_hex(16)` generated a fresh 128-bit hexadecimal code, independently of the seeded table RNG. The first call asked the model to remember it and respond `ACK`.

The fresh probe asked what code had been provided earlier, instructing the model to return `UNKNOWN` if none was present. That request included only the current question. The positive control supplied a three-message sequence: the original code-bearing user message, the model's actual ACK response, and the same question. No other request reused prior messages or supplied a previous-response identifier.

The fresh probe returned `UNKNOWN`; the history control returned the exact code. This is one successful negative/positive control pair. It does not establish universal absence of memory or prove anything about training-data familiarity.

## Model and execution configuration

| Setting | Recorded implementation |
|---|---|
| Requested and returned model | `gpt-6-luna` |
| API interface | OpenAI Python client, `responses.create` |
| Reasoning effort | `medium` |
| Maximum output tokens | 8,000 for every call |
| Tools | Empty list |
| Response storage argument | `store=False` |
| Temperature, top-p, model seed | Not explicitly set |
| Client timeout | 90 seconds |
| Automatic SDK retries | Disabled with `max_retries=0` |
| Concurrency | One request at a time |
| Local table/order seed | `1802026` |

The runner read credentials from the ignored `.env` file and checked that its configured model agreed with the requested model. The expected answer dictionary existed locally but was not supplied as an answer key to the API. Only the prompt or explicitly constructed control messages were sent.

Four earlier directories, ending `031533Z`, `031555Z`, `031622Z`, and `031634Z`, each contain one failed `isolation_seed` attempt with `APIConnectionError`. They contain no completed model response. The successful round followed those connection-refused launches and used a PowerShell Python-stdin invocation, as recorded in the original run report. Failed launch directories were not merged into the successful experiment.

The runner caught request errors, saved sanitized diagnostic information, and stopped rather than silently retrying. In the successful directory, all 20 responses were completed. None reached the output cap.

## Ground truth and scoring

For a supplied table with labels `y_i`, Python computed:

```text
n_rows = number of supplied records
n_positive = sum(y_i)
fraction_positive = round(n_positive / n_rows, 6)
```

The scorer parsed the returned text with `json.loads`. Both count fields had to be actual Python `int` values and exactly equal their expected values. This excludes booleans and numeric strings for the count fields. The fraction had to be numeric and within an absolute tolerance of `0.000001` of the rounded expected fraction. A response was fully correct only if both counts and the fraction passed.

Extra keys were not explicitly rejected. Malformed or unsuitable JSON produced a failed score. The pilot scorer did not explicitly gate correctness on response completion status; all successful-run responses were completed, so this limitation did not affect the reported results. Isolation responses were checked by stripping surrounding whitespace and comparing against `UNKNOWN` or the generated code.

The original report records a local reparse of each supplied CSV/JSON payload to verify row and positive counts independently of the stored answer dictionaries. Expected values are also reproducible from the current generator and source file. Reproduction depends on the entire RNG call sequence, not just choosing the same seed for an isolated sampling operation.

## Recorded outcome and inferential limits

| Table | True rows / positives | CSV returned | JSON returned |
|---|---|---|---|
| Synthetic 20 | 20 / 7 | 20 / 7 | 20 / 7 |
| Synthetic 100 | 100 / 34 | 100 / 34 | 100 / 34 |
| Titanic 100 original | 100 / 38 | 100 / 38 on both repeats | 100 / 37 and 100 / 38 |
| Titanic 100 modified | 100 / 58 | 100 / 58 on both repeats | 100 / 60 on both repeats |
| Titanic 802 | 802 / 310 | 891 / 342 | 800 / 307 |
| Titanic 891 | 891 / 342 | 891 / 340 | 891 / 355 |

Nine of sixteen table responses passed all three scored fields: CSV 6/8 and JSON 3/8. These counts describe this small pilot, not a statistically established format advantage. Requests reuse tables, sizes are uneven, and input lengths differ by serialization. For the 802-row case, logged input usage was 3,325 tokens for CSV and 8,934 for JSON.

The 802-row CSV answer reproduced the original dataset's counts and fraction. However, the large full-table checks failed in both formats, and other incorrect answers did not equal the original statistic. Counting difficulty therefore prevents treating overall error rate as a memorization measure. A correct full-table answer would also be ambiguous because both counting and prior knowledge could yield it.

## Artifacts and reproduction

- [Successful-run metadata](../results/luna_pilot_20261014T031651Z/metadata.json): settings and source hash.
- Successful trial log (`../results/luna_pilot_20261014T031651Z/trials.jsonl`, withheld; see [pilot review](../results/luna_pilot_20261014T031651Z/ARTIFACT_REVIEW.md)): case definitions, exact prompts, request messages, expected values, final outputs, usage, timing, and scores.
- [Summary](../results/luna_pilot_20261014T031651Z/summary.json) and [original report](../results/luna_pilot_20261014T031651Z/REPORT.md).
- [Current runner](../exploratory_luna.py): stimulus generation and scoring implementation.

From the repository root, `python exploratory_luna.py` regenerates cases and prints expected values without sending requests. Adding `--run` starts a new live experiment in a timestamped directory and should be treated as new data collection, not reproduction of the existing responses. The script has no saved-response analysis subcommand. The absence of an archived Round 1 environment means later successful execution alone does not establish that the original software environment has been reproduced exactly.
