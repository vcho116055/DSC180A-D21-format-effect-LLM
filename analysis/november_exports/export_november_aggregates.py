"""Export per-table aggregates of the November study from the local raw run.

The raw run (results/overall_replication_20261103_v2/) is git-ignored because some of its
files embed source rows. This script reads only its per-request score tables, which hold
IDs, correctness flags and token counts but no table values or model outputs, and writes
per-table averages and counts that are safe to commit:

  output_tokens_by_table_task_format.csv  primary stage, 36 tables x 3 tasks x 4 formats:
                                          mean output and input tokens over completed calls
  file_vs_inline_by_table_format.csv      file stage and its matched inline calls,
                                          12 tables x 4 formats x 2 deliveries:
                                          exact and precision-tolerant correct counts
  export_manifest.json                    input hashes and row counts

Inputs are checked against the hash sealed in FINAL_INTEGRITY.json where one exists.
No API calls. Only the exporter needs the local raw run; the analyses that use these
files run on a fresh clone.

Usage (from the repository root):
    python -m analysis.november_exports.export_november_aggregates
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = ROOT / 'results/overall_replication_20261103_v2'
FORMATS = ['csv', 'json', 'xml', 'txt']
TASKS = ['direct', 'attribute', 'join']


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    sealed = json.loads((RAW / 'FINAL_INTEGRITY.json').read_text(encoding='utf-8'))['sha256']
    requests_path = RAW / 'scored_requests.csv'
    assert sha256(requests_path) == sealed['scored_requests.csv'], 'scored_requests.csv differs from the sealed run'
    requests = pd.read_csv(requests_path)
    assert len(requests) == 8376
    sensitivity = pd.read_csv(RAW / 'file_precision_sensitivity_requests.csv')
    return requests, sensitivity


def output_tokens(requests):
    primary = requests[requests.stage == 'primary']
    assert len(primary) == 5184 and primary.block.nunique() == 36
    done = primary[primary.status == 'completed']
    table = (done.groupby(['block', 'dataset', 'n_rows', 'task', 'format'])
             .agg(completed_calls=('id', 'size'), mean_output_tokens=('output_tokens', 'mean'),
                  mean_input_tokens=('input_tokens', 'mean'))
             .reset_index())
    assert len(table) == 36 * 3 * 4, 'every table must have completed calls in every task and format'
    table['planned_calls'] = 12
    table[['mean_output_tokens', 'mean_input_tokens']] = table[['mean_output_tokens', 'mean_input_tokens']].round(4)
    return table[['block', 'dataset', 'n_rows', 'task', 'format', 'planned_calls', 'completed_calls',
                  'mean_output_tokens', 'mean_input_tokens']]


def file_vs_inline(sensitivity):
    table = (sensitivity.groupby(['block', 'dataset', 'n_rows', 'format', 'delivery'])
             .agg(attempts=('id', 'size'), completed=('completed', 'sum'),
                  exact_correct=('exact_correct', 'sum'), tolerant_correct=('tolerant_correct', 'sum'))
             .reset_index())
    assert len(table) == 12 * 4 * 2 and (table.attempts == 18).all(), 'expected 18 matched calls per cell'
    totals = table.groupby('delivery')[['attempts', 'exact_correct', 'tolerant_correct']].sum()
    # Must agree with the published totals (file 811/828, inline 862/862 of 864).
    assert totals.loc['file'].tolist() == [864, 811, 828] and totals.loc['inline'].tolist() == [864, 862, 862]
    return table


def main():
    requests, sensitivity = load()
    tokens = output_tokens(requests)
    files = file_vs_inline(sensitivity)
    tokens.to_csv(HERE / 'output_tokens_by_table_task_format.csv', index=False)
    files.to_csv(HERE / 'file_vs_inline_by_table_format.csv', index=False)
    manifest = dict(
        status='per-table aggregates exported from the local raw November run; no table values, prompts, '
               'model outputs or remote identifiers',
        source_directory='results/overall_replication_20261103_v2 (git-ignored, local only)',
        inputs_sha256={name: sha256(RAW / name) for name in
                       ('scored_requests.csv', 'file_precision_sensitivity_requests.csv')},
        outputs={'output_tokens_by_table_task_format.csv': len(tokens),
                 'file_vs_inline_by_table_format.csv': len(files)},
        notes=['Output-token means use completed calls only; one primary call (core_titanic_80_b0, direct, xml) '
               'was an API error, so that cell averages 11 calls.',
               'Output tokens include hidden reasoning tokens.',
               'File-vs-inline counts pool 3 tasks x 2 versions x 3 repeats (18 calls) per table, format and '
               'delivery; tolerant_correct accepts numeric differences up to 1e-12, as in '
               'results/november_replication/file_precision_sensitivity.json.'])
    (HERE / 'export_manifest.json').write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=1))


if __name__ == '__main__':
    main()
