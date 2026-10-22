# Week 4 transfer review

The October 22, 2026 transfer preserves the personal source repository. Source datasets, credentials, virtual environments, chat archives, class summaries, and presenter notes are excluded. The source `requirements-experiments.txt` is retained unchanged for historical snapshot checks; use the shared uv setup for installation.

No source credential value or common credential pattern was detected in the reviewed transfer candidates. Detection is a check, not proof that every possible secret is absent.

## Row-level artifacts pending redistribution review

The following requested files remain in the personal repository. Case files embed source-derived tables. Response, scoring, audit, and report files can contain source cell values or row-level examples. Source provenance and redistribution permission have not been established in this session. Aggregate results and source hashes do not establish that permission. These files are intentionally absent pending that review; they have not been silently redacted or replaced.

- `results/week4_followup/cases.jsonl`
- `results/week4_followup/trials.jsonl`
- `results/week4_lookup/cases.jsonl`
- `results/week4_lookup/scored_cells.csv`
- `results/week4_lookup/trials.jsonl`
- `results/week4_overview/REPORT.md`
- `results/week4_selection/REPORT.md`
- `results/week4_selection/analysis.json`
- `results/week4_selection/audit.json`
- `results/week4_selection/calibration_cases.jsonl`
- `results/week4_selection/calibration_trials.jsonl`
- `results/week4_selection/main_cases.jsonl`
- `results/week4_selection/main_trials.jsonl`
- `results/week4_selection/transport_attempt_01/calibration_trials.jsonl`

## Validation and reproduction limits

All 12 lookup and selection integrity tests passed using the transferred shared code, the original frozen artifacts as read-only fixtures, and the shared Python 3.12.14 interpreter, with network connections prohibited. The documented aggregate export reproduced the published summary byte-for-byte. The documented preparation steps were exercised in a temporary tree using the exact local source inputs; all three generated plan hashes matched the historical manifests, and the temporary outputs were removed. Transferred Python syntax and JSON parse checks passed; selection source snapshots are unchanged. The shared checkout cannot yet run the artifact-dependent suites because the files listed above are absent. Full source-hash auditing additionally requires the exact authorized wine and medical source CSVs, which have not been copied.

Dependency definitions preserve OpenAI 3.35.1 and python-dotenv 1.2.4 and add the historical NumPy 2.4.2 and Matplotlib 3.10.8 pins. The uv lock update was completed through the user’s Terminal. Locked offline sync and imports of OpenAI, python-dotenv, NumPy, and Matplotlib passed at the pinned versions. No paid model requests were made.

## What is included

Code and protocols, retrospective methodology, source hashes and runtime records, dispatch-start logs, lookup aggregate analysis and request-level success flags, the combined overview summary, and historical selection source snapshots are included. `week4_selection/summary.json` is a clearly labeled derivative of the original selection analysis with the `failures` field omitted. Its source hash identifies the unchanged local analysis. The shared Round 3 methodology also omits three original source fare cells; the altered values are experiment-defined, and all original documentation remains local.

The older pilot trial log remains excluded under its [existing artifact review](luna_pilot_20261014T031651Z/ARTIFACT_REVIEW.md). Overview source snapshots were outside the requested transfer; shared methodology links instead point to corresponding copied code/protocol files whose content was checked against those snapshots.

## Restore the exact historical files locally

The 14 originals remain under the same relative paths in the sibling `../dsc180a-personal-progress` repository. [withheld_artifacts.json](withheld_artifacts.json) records every path, its SHA-256, and whether it is raw, derived, or a narrative report. The shared `.gitignore` excludes these exact paths, so a local restoration does not make them publishable. This setup left the originals in place rather than making additional shared-repository copies.

If you need offline analysis before publication review, run this from the shared repository root. It verifies source hashes, preserves any existing identical local file, and refuses to overwrite differing content. It never stages files or reads `.env`:

```sh
uv run --locked python - <<'PY'
import hashlib
import json
import shutil
from pathlib import Path

manifest = json.loads(Path('results/withheld_artifacts.json').read_text())
source = Path(manifest['source_repository'])
for item in manifest['artifacts']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    original = source / relative
    content = original.read_bytes()
    assert hashlib.sha256(content).hexdigest() == item['sha256'], relative
    target = Path(item['path'])
    if target.exists():
        assert target.read_bytes() == content, f'Local conflict: {relative}'
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
print('Historical files restored locally; they remain ignored by Git.')
PY
```

Keep the original archive backed up. Response logs, API identifiers, usage/timing records, transport failures, and historical narrative reports cannot be recreated exactly by rerunning a model. Restore their original bytes from that archive. A new API run would create new observations and could incur charges; it is not required or authorized by these offline restoration instructions.

## Regenerate derived analysis without API calls

After local restoration, the following commands regrade saved responses and regenerate `week4_lookup/scored_cells.csv`, lookup analysis/request scores, `week4_selection/analysis.json`, `week4_selection/audit.json`, and the combined overview summary. Tests and the first three analysis commands use frozen cases/responses; the final audit also needs all three exact authorized source datasets with the manifest hashes. These commands write derived files, so use a disposable local copy if you want to preserve every original byte:

```sh
uv run --locked python -m unittest experiments.test_week4_study experiments.test_week4_selection -v
uv run --locked python -m experiments.week4_study analyze --directory results/week4_lookup
uv run --locked python -m experiments.week4_selection analyze
uv run --locked python -m experiments.summarize_week4
uv run --locked python -m experiments.audit_week4_selection
```

Neither report Markdown file is generated by these tools. Preserve the original reports locally and review their row-level examples before publishing them later. The failed transport log is a historical event record, not a target for regeneration.

The published selection aggregate can be regenerated from the local original analysis without including its row-level failure details:

```sh
uv run --locked python - <<'PY'
import hashlib
import json
from pathlib import Path
raw = Path('results/week4_selection/analysis.json').read_bytes()
analysis = json.loads(raw)
summary = {key: value for key, value in analysis.items() if key != 'failures'}
summary['publication_note'] = 'Aggregate-only export of the original analysis; row-level failures are withheld. Historical source analysis is unchanged.'
summary['source_analysis_sha256'] = hashlib.sha256(raw).hexdigest()
summary['excluded_fields'] = ['failures']
Path('results/week4_selection/summary.json').write_text(json.dumps(summary, indent=2) + '\n')
PY
```

## Reconstruct case plans locally without API calls

Exact source data, the copied code, and its RNG sequence are required to reconstruct prompts and answer keys. This is separate from restoring historical responses. With the authorized source files at the manifest hashes, the following calls only preparation functions and writes to the ignored, initially absent `results/local_regeneration/` tree. Do not substitute another dataset version or overwrite the archived run directories:

```sh
uv run --locked python - <<'PY'
import hashlib
import json
from pathlib import Path
from experiments import week4_study as study
from experiments import week4_followup as followup
from experiments import week4_selection as selection

root = Path.cwd()
lookup_manifest = json.loads((root / 'results/week4_lookup/manifest.json').read_text())
for name, definition in study.DATASETS.items():
    assert hashlib.sha256((root / 'data' / definition[0]).read_bytes()).hexdigest() == lookup_manifest['source_sha256'][name]

scratch = root / 'results/local_regeneration'
scratch.mkdir(exist_ok=False)
(scratch / 'results').mkdir()
study.prepare(scratch / 'results/week4_lookup')
followup.ROOT = scratch  # read the regenerated primary cases
followup.DIRECTORY = scratch / 'results/week4_followup'
followup.prepare()       # its imported data loader still reads the real local data/
selection.DIRECTORY = scratch / 'results/week4_selection'
selection.prepare()
for name in ('week4_lookup', 'week4_followup', 'week4_selection'):
    saved = json.loads((root / 'results' / name / 'manifest.json').read_text())
    generated = json.loads((scratch / 'results' / name / 'manifest.json').read_text())
    assert generated['plan_sha256'] == saved['plan_sha256'], name
print('Case plan hashes match; no model calls were made.')
PY
```

Preparation manifests contain new timestamps and runtime/Git provenance. Matching case-plan hashes do not recreate historical response IDs, model behavior, timings, charges, or narrative reports. Future publication requires a separate review of dataset sources, preprocessing history, licenses/terms, attribution, and permission to redistribute both source-derived tables and cell-level outputs. Do not force-add the excluded files before that review.
