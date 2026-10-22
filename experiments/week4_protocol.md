# Week 4 exploratory protocol

Written before the Week 4 response collection. This is a locally frozen exploratory design, not a public preregistration.

## Question and primary comparison

Does input representation affect how reliably a model copies supplied record values, especially when the values differ from the original local dataset? The primary outcome is correct retrieval of the supplied value. Errors that exactly reproduce a replaced original value are counted separately and are not automatically classified as memorization.

The main experiment crosses four representations (CSV, compact row-object JSON, XML, and plain text), two dataset labels (named and neutral), and two table versions (original and altered). Three local datasets are used: Titanic, Red Wine Quality, and Medical Cost Personal Datasets. For each dataset, draw three independently sampled tables of 40 rows and three of 200 rows. Each table appears in all 16 conditions, giving 288 main requests and 18 table blocks. Source rows can overlap across blocks.

## Tasks and manipulation

Each request asks for three values and one absent record. Choose one target in each third of the table, with target values unique within that table. The value fields are fare, density, and charges, respectively. In the altered version, replace exactly those three cells with newly generated, in-range values at five decimal places. Replacements must differ numerically from every value in the source field. The original target value therefore no longer appears in its altered table. This reduces ambiguity from copying the old value from another row, but it does not prove a mistaken original-value response came from training.

All representations contain exactly the same ordered rows and fields. Values are serialized as strings; equivalent decimal spellings are accepted in scoring, with literal string matches tracked separately. Plain text is specifically one record per line, with `field: value` pairs separated by ` | `. XML uses a `records` root, `record` elements, and child elements for fields. These choices do not represent every possible JSON, XML, or text layout.

The table name changes only the source-description sentence. Column names remain meaningful in neutral conditions, so neutral labeling is not anonymization. Instructions ask for supplied values and do not identify which cells were altered. All conditions request the same JSON output, without an enforced output schema. Correct abstention is NOT_FOUND for the absent ID.

## Secondary checks

- Six synthetic tables (three each at 40 and 200 rows), in all four formats: 24 requests. Newly generated values and a simpler three-column schema provide a basic lookup check, not a perfectly matched control for dataset familiarity.
- Two 800-row Titanic tables, original and altered, in four formats with the dataset named: 16 stress requests.
- Six count tasks (Titanic-derived and synthetic binary tables at 40, 200, and 800 rows), in CSV and JSON: 12 arithmetic requests. These are secondary outcomes and do not estimate leakage.
- Six no-table probes use the target IDs from two small-table blocks per dataset: 6 requests. Row-index conventions limit the sensitivity of this probe, especially outside Titanic.
- Repeat the altered, named, 200-row condition once per dataset and format: 12 requests. These repeats assess response variability and are excluded from the primary independent-block analysis.

Total planned: 358 requests. Request order is shuffled with a fixed local seed. Previous pilot isolation checks are not treated as proof that the new model has no memory. Instead, verify each outgoing request contains only a single current prompt, with no conversation references, tools, retrieval, or inherited research discussion.

## Model, scoring, and limits

Use GPT-5.6 Luna, matching the latest screenshot agreement. The previous pilot used GPT-6 Luna. Do not attribute differences between weeks solely to the task design. Use medium reasoning, provider-default sampling, no tools, no stored conversation, and no automatic retries. Lookup responses allow 2,048 generated tokens and arithmetic responses 4,096. Record incomplete responses separately, including whether a token cap caused them. Limits define the tested configuration and can affect performance.

Score every planned cell against values independently reconstructed from the exact serialized payload. Record numeric accuracy, literal-copy accuracy, output-schema compliance, absent-record accuracy, original-value reversions, other errors, token usage, and completion status. Invalid or incomplete responses count as failures in the primary accuracy denominator; report their incidence separately. Transport failures are reported and not called model reasoning errors.

Analyze CSV/JSON and other format contrasts within matched table blocks. Summarize uncertainty with a stratified block bootstrap over the three table samples within each dataset-size stratum. These intervals are descriptive: the study has few blocks, repeated source records, and exploratory comparisons. Ceiling performance can yield degenerate intervals and does not establish equivalence. Do not choose or discard trials based on whether they show a preferred outcome.

## Data limitations and reproducibility

Titanic uses the first 891 rows from the local transformed file and a projection of its columns. The labels of the last 418 rows remain unverified and are excluded. Wine and medical record IDs are assigned from one-based local row order. Source versions are not independently authenticated. Ground truth here is the supplied local table, not a claim about historical or medical accuracy.

Freeze exact prompts, targets, expected answers, seed, source hashes, conditions, and model settings before response collection. Save responses and usage separately. Keep credentials out of every artifact. The weekly presentation should use first-person singular for the author's work, attribute joint decisions and Xiao's observations accurately, omit API cost discussion, avoid em dashes and the word "trap," and be delivered as Markdown without HTML.
