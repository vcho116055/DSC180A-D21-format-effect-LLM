# Separate API file-input feasibility pilot

User authorized a maximum of $1.00 on November 3, 2026. This pilot is separate from the main inline-format experiment and its proposed replication. It establishes basic file acceptance, retrieval, and repeat consistency, not a format ranking.

Use one generated 20-row synthetic table, with three present conjunction queries and one absent conjunction. Serialize identical logical rows as native CSV, JSON, XML, and TXT files. Every present query requires both attributes, and each absent attribute value appears elsewhere in the table. The first round has four formats x inline/upload delivery = eight requests. Continue to two more identical rounds only if all eight initial requests complete strictly correctly using the intended model. Maximum total: 24 requests. Keep all failures. Do not expand to real datasets or larger tables automatically.

Model: `gpt-5.6-luna`, medium reasoning, 4,096 output-token maximum, no tools, fresh requests, `store=False`, default sampling, SDK retries disabled, one concurrent request. Prompts are identical across repetitions. Round order is randomized before collection. Files are uploaded through `client.files.create(..., purpose='user_data')` and supplied as `input_file` with the returned file ID. A local path is opened by the script and is never sent as an accessible path to the model.

Files contain only generated synthetic records. Hash the files, cases, runner, and imported helper before dispatch. The inline conditions supply the same serialized bytes as text. Original-to-altered comparisons are outside this small pilot. No source datasets are needed.

Scoring reuses the existing value scorer, additionally requiring exact keys, string values, and the intended returned model. Report results by format and delivery mode. Repeated calls share one logical table and are not independent table samples. If the initial gate fails, retain its eight results (or fewer if an operational/budget stop occurs) and diagnose without changing prompts mid-run.

Spending: reserve $0.5323728 before each response call, covering the documented full 1,050,000-token context at conservative long-context/cache-write rates plus the output cap. Input-file augmentation has unknown token expansion, so do not estimate its reservation from file byte length. Calls run sequentially. After success, replace the reservation with conservative usage accounting (without cache discounts); retain the full reservation for unknown billing. Stop when accounted spend plus the next reservation would exceed $1.00. Stop immediately on model mismatch, missing usage, connection failure, authentication/access errors, or rate limiting. This controls estimated model-token charges under the documented rates, excluding taxes or unreported provider fees.

Record actual runtime versions; the current available interpreter is Python 3.11 with OpenAI SDK 2.54.0, not the shared locked environment. Do not claim locked-environment parity. Preserve start records, outputs, usage, file IDs, and errors. Never silently retry or resume a started pilot. Delete only files uploaded by this pilot after the run and record cleanup outcomes. A cleanup failure does not justify another model call.

Local preparation and offline checks:

```powershell
python -m unittest experiments.test_file_input_pilot -v
python -m experiments.file_input_pilot prepare
```

Preparation refuses to overwrite an existing pilot directory. After the API key is configured locally, the authorized pilot is launched with:

```powershell
python -m experiments.file_input_pilot run
```

Current local artifacts: `results/file_input_pilot_20261103/` (ignored). Only `run` submits API requests. No key values are printed or logged. The script accepts `--env-file` if the user supplies another local configuration path.

Official documentation checked November 3, 2026:

- https://developers.openai.com/api/docs/guides/file-inputs
- https://developers.openai.com/api/docs/models/gpt-5.6-luna

CSV file inputs receive spreadsheet-specific augmentation; text/code files use text extraction. Consequently this comparison measures the file-delivery workflow, not raw serialization alone. Acceptance by this particular model/account is the empirical question for the pilot.
