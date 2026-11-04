"""Export reviewed aggregate results; never publishes table payloads or calls the API."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil

from experiments import overall_replication as r
from experiments.overall_replication_v2 import DIRECTORY

PUBLIC_DIRECTORY = r.ROOT/'results/november_replication'
AGGREGATES = (
    'analysis.json', 'summary_stage.csv', 'summary_task_format.csv', 'summary_size.csv',
    'summary_dataset.csv', 'summary_cue.csv', 'summary_version.csv', 'summary_repeat.csv',
    'primary_completed_response_accuracy.csv', 'primary_task_format_detail.csv',
    'primary_repeat_by_task.csv', 'primary_repeat_completed_only.csv',
    'file_delivery_by_task_format.csv', 'file_precision_sensitivity_summary.csv',
    'literal_copy_accuracy.csv', 'representation_overhead.csv',
    'target_position_diagnostics.csv', 'selector_width_diagnostics.csv',
)
FIGURES = ('primary_format_errors.png', 'present_vs_absent.png', 'repeat_consistency.png',
           'table_size_errors.png', 'file_delivery_precision.png')
FORBIDDEN_KEYS = {'expected', 'actual', 'record_id', 'response_id', 'file_id', 'output',
                  'prompt', 'payload', 'api_key', 'openai_api_key'}
PRIVATE_PATTERNS = re.compile(
    r'sk-[A-Za-z0-9_-]{16,}|resp_[A-Za-z0-9]{10,}|file-[A-Za-z0-9]{10,}'
    r'|[A-Za-z]:[\\/]Users[\\/]|/Users/|/home/')


def check_structure(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError(f'Row-level or private field in public export: {key}')
            check_structure(child)
    elif isinstance(value, list):
        for child in value:
            check_structure(child)


def review(directory):
    allowed = set(AGGREGATES + FIGURES + (
        'README.md', 'REPORT.md', 'provenance.json', 'audit.json',
        'file_precision_sensitivity.json', 'file_pilot_summary.json', 'PUBLICATION_REVIEW.json'))
    entries = list(directory.iterdir())
    if any(not p.is_file() or p.name not in allowed for p in entries):
        raise ValueError('Unexpected artifact in aggregate publication directory.')
    for path in entries:
        if path.suffix == '.png':
            continue
        text = path.read_text(encoding='utf-8')
        if PRIVATE_PATTERNS.search(text):
            raise ValueError(f'Credential, remote identifier, or personal path in {path.name}')
        if path.suffix == '.json':
            check_structure(json.loads(text))
        if path.suffix == '.csv':
            with path.open(encoding='utf-8', newline='') as stream:
                fields = next(csv.reader(stream))
            if FORBIDDEN_KEYS.intersection(k.lower() for k in fields):
                raise ValueError(f'Row-level columns in {path.name}')
    return entries


def export(source=DIRECTORY, destination=PUBLIC_DIRECTORY):
    seal = json.loads((source/'FINAL_INTEGRITY.json').read_text(encoding='utf-8'))
    for name, sha in seal['sha256'].items():
        if r.file_hash(source/name) != sha:
            raise ValueError(f'Sealed source artifact changed: {name}')
    destination.mkdir(parents=True, exist_ok=True)
    # Reject unrelated existing files rather than silently deleting them.
    review(destination)
    for name in AGGREGATES + FIGURES:
        shutil.copyfile(source/name, destination/name)
    sensitivity = json.loads((source/'file_precision_sensitivity.json').read_text(encoding='utf-8'))
    # Per-request IDs live only in the local sensitivity CSV, never this export.
    r.save(destination/'file_precision_sensitivity.json', sensitivity)
    summary = (source/'EXECUTIVE_SUMMARY.md').read_text(encoding='utf-8')
    summary = summary.replace('# Experiment conclusion for the checkpoint', '# Repeated tabular-evidence study')
    summary = summary.replace('Raw outputs, cases, and reports remain local and ignored by Git. Nothing was committed or pushed.',
        'Raw outputs and cases remain local and ignored by Git. This directory publishes reviewed aggregates and plots.')
    summary = summary.replace('[detailed findings](CONCLUSIONS.md)', '[detailed findings](REPORT.md)')
    summary += ('\n## Artifacts and reproduction\n\n'
        'These aggregate files and plots can be read on a fresh clone without datasets, API access, '
        'or withheld logs. The experiment code and frozen protocols are under `../../experiments/`. '
        'The historical results notebook has not been extended to this study.\n\n'
        'Rebuilding response-level analyses requires the local frozen run under '
        '`results/overall_replication_20261103_v2/`. Restore the authorized local artifacts matching '
        'the hashes in provenance.json; do not substitute arbitrary datasets or rerun paid requests '
        'to reconstruct historical responses. See ../../experiments/README.md for offline commands.\n')
    (destination/'README.md').write_text(summary, encoding='utf-8')
    report = (source/'CONCLUSIONS.md').read_text(encoding='utf-8')
    report = report.replace('Consult REPORT.md and analysis.json', 'Consult analysis.json')
    report = report.replace('Raw data and reports remain local and ignored by Git.',
        'Raw response-level artifacts remain local and ignored by Git; this report and its aggregate tables are published.')
    (destination/'REPORT.md').write_text(report, encoding='utf-8')
    audit = json.loads((source/'audit.json').read_text(encoding='utf-8'))
    public_audit = {key: audit[key] for key in (
        'planned', 'recorded', 'complete', 'coverage_unique', 'source_payload_and_score_checks',
        'returned_model', 'reasoning', 'calibration_passed', 'completed', 'file_uploads',
        'complete_matched_blocks', 'planned_matched_blocks')}
    public_audit.update(all_uploaded_files_deleted=seal['all_uploads_deleted'],
        api_failures=seal['api_failures'],
        inherited_calibration_prefix_verified=seal['inherited_calibration_prefix_verified'],
        source_snapshot_verified=seal['source_snapshot_verified'],
        calibration_note='Technical gate adopted before main responses; initial strict development gate was 23/24.')
    r.save(destination/'audit.json', public_audit)
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    provenance = {key: manifest[key] for key in (
        'created_utc', 'model', 'reasoning_effort', 'seed', 'max_output_tokens', 'tools', 'store',
        'repeats', 'planned', 'unique_cases', 'stages', 'data_sha256', 'protocol_revision',
        'effective_gate', 'inherited_calibration', 'pricing_checked', 'pricing_source', 'file_inputs_source')}
    provenance['sources_sha256'] = {key.replace('\\','/'): value
                                    for key,value in manifest['sources_sha256'].items()}
    provenance['supplementary_analysis_sha256'] = seal['supplementary_analysis_sha256']
    provenance['withheld_original_artifacts_sha256'] = seal['sha256']
    provenance['environment'] = []
    for runtime in audit['runtime']:
        item = {key: runtime.get(key) for key in (
            'started_utc', 'python', 'implementation', 'os', 'sdk', 'workers', 'git_head',
            'dirty', 'uv_lock_sha256', 'environment_deviation')}
        item['relevant_distributions'] = {name: runtime['distributions'].get(name) for name in
            ('openai', 'python-dotenv', 'numpy', 'pandas', 'matplotlib')}
        provenance['environment'].append(item)
    provenance['publication_note'] = ('Hashes identify the original local artifacts. Original row-level '
        'payloads, responses, remote IDs, full package inventory, and chat/session notes are not published. '
        'Collection-time source/raw hashes describe their original bytes; restore the local source snapshots '
        'for exact audits where Git normalized legacy helper line endings. Public export hashes use LF text.')
    r.save(destination/'provenance.json', provenance)
    pilot = r.ROOT/'results/file_input_pilot_20261103/summary.json'
    if pilot.exists():
        r.save(destination/'file_pilot_summary.json', json.loads(pilot.read_text(encoding='utf-8')))
    for path in destination.iterdir():
        if path.is_file() and path.suffix != '.png':
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
    entries = review(destination)
    r.save(destination/'PUBLICATION_REVIEW.json', dict(
        review='Aggregate-only allowlist, structured-field and credential/remote-ID/path checks passed.',
        exporter_sha256=r.file_hash(__file__),
        excluded=['source datasets', 'table stimuli', 'raw model responses', 'cell scores',
                  'individual error examples', 'remote response/file identifiers', 'session notes', 'credentials'],
        files_sha256={p.name: r.file_hash(p) for p in entries if p.name != 'PUBLICATION_REVIEW.json'}))
    review_path = destination/'PUBLICATION_REVIEW.json'
    review_path.write_bytes(review_path.read_bytes().replace(b'\r\n', b'\n'))
    review(destination)
    print(f'Exported {len(list(destination.iterdir()))} reviewed aggregate artifacts to {destination.relative_to(r.ROOT)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DIRECTORY)
    parser.add_argument('--destination', type=Path, default=PUBLIC_DIRECTORY)
    args = parser.parse_args()
    export(args.source, args.destination)
