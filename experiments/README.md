# Week 4 experiments

The Week 4 study uses the discussion with Xiao as its starting point: record lookup is the primary task, four input formats are compared, and arithmetic is a secondary check. All model calls are made through the API with no tools or conversation history.

For detailed retrospective documentation of every recorded round, including the original counting pilot, see the [methodology archive](../methodology/README.md).

The later attribute-selection and two-table experiment uses `week4_selection.py`, its separate frozen protocol, `test_week4_selection.py`, and `results/week4_selection/`. After restoring the local-only frozen files, run `uv run --locked python -m experiments.week4_selection analyze` to analyze saved responses without API requests. Its calibration and secondary requests are separate from the original Week 4 primary comparison. See [Round 4 methodology](../methodology/round4_selection_and_joins.md) for details, including the documented transport restart.

## Files

- `week4_protocol.md`: design written before response collection, definitions, controls, and limitations.
- `week4_study.py`: deterministic stimulus generation, API runner, and analysis.
- `test_week4_study.py`: offline checks of target values, changed cells, serialization equivalence, and scoring.
- `week4_followup.py`: the separate follow-up added after the main lookup results reached ceiling accuracy.
- `summarize_week4.py`: validates recorded responses and combines both finished runs without API calls.
- `../results/week4_lookup/`: source hashes, model settings, start logs, and aggregate analysis; cases, responses, and cell scores are withheld.
- `../results/week4_followup/`: the frozen follow-up manifest and start logs; prompts and responses are withheld.
- `../results/week4_overview/summary.json`: aggregate combined results; the original narrative report is withheld because it includes source cell values.
- `../results/week4_selection/summary.json`: aggregate selection results with row-level failures omitted.
- [Transfer review](../results/TRANSFER_REVIEW.md): excluded file list and local restoration/regeneration instructions.
- Personal class summaries and presenter notes stay in the personal repository and are not part of this shared checkout.
- `../requirements-experiments.txt`: historical direct-dependency pins, preserved for source-snapshot audits. The shared environment is managed with `../pyproject.toml` and `../uv.lock`.

## Reproduce locally

Use the shared Python 3.12.14 environment from the repository root. The historical run used Python 3.11.6, OpenAI 2.54.0, and python-dotenv 1.2.2; those records and source snapshots remain unchanged. The shared environment retains OpenAI 3.35.1 and python-dotenv 1.2.4, adding the recorded NumPy 2.4.2 and Matplotlib 3.10.8 dependencies. Passing offline checks under this environment does not establish identical live model outputs.

```sh
uv python install 3.12.14
uv sync --locked
```

The published checkout intentionally omits the 14 files listed in the transfer review. Restore those local-only files before running the artifact-dependent tests or analysis commands below; a fresh clone alone cannot execute them. The original files remain in the personal repository pending redistribution review. These checks do not require API calls. The full source-hash audit additionally requires all three exact authorized local datasets; do not download an arbitrary replacement or commit those files.

After restoring the local-only artifacts, integrity tests and saved-response analysis make no model calls:

```sh
uv run --locked python -m unittest experiments.test_week4_study experiments.test_week4_selection -v
uv run --locked python -m experiments.week4_study analyze --directory results/week4_lookup
uv run --locked python -m experiments.summarize_week4
```

To start a genuinely new run, choose a new directory. Never overwrite the frozen plan or raw responses from a completed run.

```powershell
uv run --locked python -m experiments.week4_study prepare --directory results/week4_lookup_replication
uv run --locked python -m experiments.week4_study run --directory results/week4_lookup_replication
uv run --locked python -m experiments.week4_study analyze --directory results/week4_lookup_replication
```

The runner skips completed request IDs when resuming, logs requests before dispatch, and stops if a prior interruption left a request without a recorded response. It does not retry silently. API failures and incomplete outputs remain visible in the results.

The source datasets are local and are not committed here. The source hashes in the manifest identify the exact files used. Tests validate the supplied data, not independent historical provenance.
