# Evaluating Format Effects on Evidence Following in Large Language Models

DSC180A D21 research project investigating how CSV and JSON input formats affect evidence following in large language models.

Research question: how does input serialization affect whether a model follows supplied table evidence, including edited values, rather than returning familiar dataset answers? This repository is exploratory. Counting errors alone do not establish memorization or training-data leakage.

The [experiment design proposals](docs/experiment_design_proposals.md) are a **draft for discussion**, not an approved protocol. The root script implements the earlier counting pilot, not the proposed direct-lookup study. The [historical pilot report](results/luna_pilot_20261014T031651Z/REPORT.md) records GPT-6 Luna results; it is not a GPT-5.6 Luna replication.

## Project structure

```text
exploratory_luna.py              # pilot harness; keep at repository root
pyproject.toml                  # Python compatibility and direct dependencies
uv.lock                         # full dependency lock, including hashes
.python-version                 # exact Python 3.12.14 pin
requirements.txt                # legacy direct-dependency list
.env.example                    # blank credential template
.env                            # local only, ignored
data/README.md                 # schema, assumptions, source hash, provenance
data/titanic.csv               # local only, ignored
docs/experiment_design_proposals.md
results/luna_pilot_20261014T031651Z/
   REPORT.md
   metadata.json
   summary.json
   ARTIFACT_REVIEW.md
```

`trials.jsonl` was withheld because prompts embed dataset rows. No other datasets, failed pilot folders, personal course reflection, editor files, or source Git history were copied.

## Environment installation and configuration

Use **CPython 3.12.14**, recorded in `.python-version`. The project restricts Python to the 3.12 series in `pyproject.toml`; `.python-version` selects the exact patch release. A local 3.12.14 interpreter is available and passed syntax and local data validation. The required third-party releases remain `openai==3.35.1` and `python-dotenv==1.2.4`; no additional third-party imports are required by the harness.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed. On macOS with Homebrew:

```sh
brew install uv
```

On Windows, install uv using the official PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Setup was verified with **uv 0.13.4** and Python 3.12.14: locked sync, dependency imports, and local validation pass. The lockfile records exact transitive dependency versions and artifact hashes. Keep `pyproject.toml`, `uv.lock`, and `.python-version` together when sharing changes. A collaborator still needs the authorized local dataset and their own local API key for future paid execution.

**Xiao and every collaborator** should run these exact commands from the repository root:

```sh
uv python install 3.12.14
uv sync --locked
uv run --locked python --version
uv run --locked python -c "from openai import OpenAI; from dotenv import dotenv_values; print('Dependency imports OK')"
uv run --locked python -m py_compile exploratory_luna.py
uv run --locked python exploratory_luna.py
```

`uv sync --locked` checks that the lockfile matches `pyproject.toml` and installs the locked dependencies into `.venv`. It fails instead of silently updating an outdated lockfile. See [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/). Run validation with `--locked` as well. Activation is optional with `uv run`. `requirements.txt` is retained as a legacy direct-dependency list; use the uv files to reproduce transitive dependencies. When intentionally updating dependencies, regenerate and review the lockfile, then rerun validation before sharing it.

If `.env` does not exist, copy `.env.example` to `.env`. Set your own `OPENAI_API_KEY` locally and use `OPENAI_MODEL=gpt-5.6-luna`. Preserve any existing `.env`; never put a real key in the example or commit credentials. The harness reads the root `.env` directly only with `--run`, and rejects a model value that differs from its authorized model constant. Local validation requires neither a key nor an API call. API dependencies are imported only after the explicit `--run` gate, so direct local validation can also run before dependency installation using `.venv/bin/python exploratory_luna.py` on macOS/Linux.

## Data setup

Provide the specific local `data/titanic.csv` described in [data/README.md](data/README.md). It is intentionally excluded from Git. Provenance remains unresolved; an arbitrary Titanic download is not a reproduction of this pilot. Local copies do not establish permission to redistribute the dataset or embedded rows.

## Local validation and execution

```sh
uv run --locked python -m py_compile exploratory_luna.py
uv run --locked python exploratory_luna.py
```

Without `--run`, the script constructs and validates 16 table cases, prints expected counts, and returns before reading credentials or creating an API client. Run from the repository root; data and output paths are resolved relative to the script.

Only after agreeing on the protocol, verifying dataset permissions, configuring credentials and model access, and reviewing cost, a future paid pilot can be launched explicitly:

```sh
uv run --locked python exploratory_luna.py --run
```

This setup did not launch experiments. A run adds four controls to the 16 table trials, uses fresh Responses API requests except for the explicit-history control, medium reasoning, an 8,000 output-token cap, no tools, `store=False`, and no automatic retries. The spending reservation cap remains **$0.50 per invocation**, not an account-wide limit across repeated runs. Token estimates exclude taxes and endpoint surcharges.

## Week 4 experiments and historical environment

The [experiment workspace](experiments/README.md) contains the lookup, follow-up, selection/join studies, protocols, offline tests, and analysis tools. The [methodology archive](methodology/README.md) explains all four rounds and their limitations. Selected Week 4 evidence is under `results/week4_lookup/`, `results/week4_followup/`, `results/week4_selection/`, and `results/week4_overview/`. [results_overview.ipynb](results_overview.ipynb) charts and tabulates every recorded result from these committed aggregate files, without API calls; open it with the project `.venv` as the kernel (`uv sync` installs the dev dependency `ipykernel`).

`requirements-experiments.txt` is preserved unchanged as a historical dependency record because frozen source audits compare it byte-for-byte. Do not install it over the shared environment. The original runs recorded Python 3.11.6 and older OpenAI/dotenv versions; `pyproject.toml` retains the shared OpenAI 3.35.1 and python-dotenv 1.2.4 versions and adds NumPy 2.4.2, Matplotlib 3.10.8, pandas 3.0.6 (for `results_overview.ipynb`), and the dev-only ipykernel 7.4.0. The shared Python remains 3.12.14. Frozen settings, prompts, responses, source snapshots, and historical dependency records describe collection time and are not rewritten to match this environment.

The Week 4 uv lock update and dependency imports have been verified. The 14 row-level artifacts listed in the [transfer review](results/TRANSFER_REVIEW.md) remain in the personal repository and are ignored in this shared checkout pending redistribution review. That document includes exact restoration and regeneration instructions; [the machine-readable manifest](results/withheld_artifacts.json) records their SHA-256 hashes. The [selection summary](results/week4_selection/summary.json) exports aggregate metrics while excluding row-level failure details. Case files embed source-derived tables, and some response/scoring/diagnostic files contain original cell values. Keep them out of publication until redistribution permission has been verified. No source datasets, chat archives, personal weekly summaries, or presenter notes are included. The original pilot's withheld trial log remains excluded.

Only the Week 4 runner's explicit `run` action submits model requests. The root counting pilot keeps its $0.50 cap; the frozen Week 4 protocols record separate historical budgets and are not changed by this transfer. No experiments were launched for this setup.

## Runtime provenance in future results

New `metadata.json` files include an `environment` object with the exact Python version and implementation, all installed distribution versions (direct and transitive), OS system/release/version/architecture, Git HEAD commit, whether the working tree has tracked or untracked changes, and the SHA-256 of `uv.lock`. Ignored credentials, data, and `.venv` do not make the Git tree dirty. No credential contents, environment variables, or local executable paths are collected. An unavailable Git value or missing lockfile is recorded as JSON `null`, rather than inventing provenance. A commit plus `dirty=true` does not identify the exact modified source; use a reviewed clean commit for reproducible runs.

These fields describe the actual runtime, not a guarantee that it matches the lockfile; use the locked commands above. Existing historical results are preserved byte-for-byte and have not been backfilled with this machine's environment.

## Model and pricing

The planned primary model is **GPT-5.6 Luna with medium reasoning**. The existing code already matches the [official GPT-5.6 Luna documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna), checked October 20, 2026: standard input/output estimates are $0.20/$1.20 per million tokens. Reservations use $0.40/$1.80, matching the documented 2× input and 1.5× output long-context multipliers; each call reserves the full output cap and a conservative input bound. Cached-input discounts are not credited. Recheck prices before paid execution. The model alias is not a guarantee of immutable behavior; record requested and returned identifiers and recalibrate for the new model.

Historical GPT-6 Luna model identifiers, prices, and results remain unchanged in the pilot metadata and report. They describe that completed run, not current pricing.

## Publication review

The historical report, metadata, and aggregate summary were reviewed for credentials and embedded source rows. No credentials were detected; these files contain no row-level dataset payloads. See [artifact review](results/luna_pilot_20261014T031651Z/ARTIFACT_REVIEW.md) for the withheld trial log and historical path note. Trial logs from future runs also embed dataset rows and are ignored by default; review every generated artifact before sharing it. Ignoring `data/` alone does not prevent redistribution through logs.
