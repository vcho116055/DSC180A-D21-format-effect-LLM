"""Does input format (CSV / JSON / XML / TXT) affect output tokens in the November study?

Out-of-sample check of the Round 2 finding (CSV produced the longest outputs). Uses the
November primary stage: 36 sampled tables, each run in all four formats for three tasks
(direct, attribute, join), 12 calls per table, task and format. Reads the per-table means
exported to ../november_exports/output_tokens_by_table_task_format.csv, so it runs on a
fresh clone. Post-collection, exploratory; no API calls; writes only inside this folder.

Same tests as ../round2_format_tests/ (shared code):
  Omnibus  H0: format labels are exchangeable within each table. Within-table permutation
           test of the repeated-measures F and Friedman statistics, 100,000 permutations.
  Pairwise H0: mean per-table difference = 0, for all 6 format pairs. Paired sign-flip
           permutation test, Holm-adjusted within each scope.
Main scope: pooled over tasks (each table's equal-weight mean of its three task means).
Each task alone is a consistency check.

Usage (from the repository root):
    python -m analysis.november_token_tests.november_token_tests
"""
import json
from pathlib import Path

import pandas as pd

from analysis.round2_format_tests.round2_format_tests import (
    ALPHA, FORMATS, SEED, among_others, decision, fmt_p, fmt_p_eq, longest_note, token_tests, versus_csv)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'analysis/november_exports/output_tokens_by_table_task_format.csv'
OUT = HERE / 'results'
TASKS = ('direct', 'attribute', 'join')


def load():
    data = pd.read_csv(SOURCE)
    assert len(data) == 36 * 3 * 4 and data.block.nunique() == 36
    assert (data.groupby(['block', 'task']).format.nunique() == 4).all()
    # token_tests() averages rows per table and format, and labels strata by dataset and size.
    return data.rename(columns={'mean_output_tokens': 'output_tokens'}).assign(study='november')


def run_all(data):
    pooled, table = token_tests(data, label='pooled over tasks')
    per_task = [token_tests(data[data.task == t], label=t)[0] for t in TASKS]
    return [pooled, *per_task], table


def summary(tokens):
    pooled = tokens[0]
    o = pooled['omnibus']['rm_F']
    L = ['# November output tokens by format: summary of results', '',
         'Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects how many output tokens Luna '
         '(gpt-5.6-luna, medium reasoning) produces, in the November repeated study. This is an out-of-sample '
         'check of the Round 2 result in `../round2_format_tests/`, where CSV produced the longest outputs.', '',
         '## Data', '',
         '- **November primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x 80/400 rows x 6), '
         'each run in all four formats for three tasks (direct lookup, attribute selection, two-table join). '
         '12 calls per table, task and format (original/altered x named/neutral x 3 repeats).',
         '- **Input:** `analysis/november_exports/output_tokens_by_table_task_format.csv`, per-table means exported '
         'from the local raw run (completed calls only; one API error leaves one cell with 11 calls).',
         '- **Unit of analysis:** the table. The pooled value for a table and format is the equal-weight mean of '
         'its three task means.',
         '- Output tokens include hidden reasoning tokens; the reasoning/answer split was not exported.', '',
         '## Method', '',
         f'- **Significance level:** alpha = {ALPHA}, two-sided. Same tests and code as the Round 2 analysis.',
         '- **Omnibus:** within-table permutation test (100,000 permutations) of the repeated-measures F statistic '
         'and the tie-corrected Friedman statistic. Critical values are the 95th percentiles of the permutation '
         'null distributions.',
         '- **Pairwise:** paired sign-flip permutation test on per-table differences for all 6 pairs '
         '(200,000 Monte Carlo sign assignments), Holm-adjusted within each scope; 95% intervals are a table '
         'bootstrap within dataset x size groups (6 tables each).',
         '- **Main scope:** pooled over tasks. Each task alone is a consistency check.', '',
         '## Results at a glance', '',
         f"- **Pooled:** format {'affects' if o['reject_H0'] else 'does not detectably affect'} output tokens "
         f"(omnibus F permutation p {fmt_p_eq(o['p_value'])}). " + longest_note(tokens),
         '- ' + versus_csv(tokens),
         '- ' + among_others(tokens), '',
         '## Omnibus tests', '',
         'H0: format labels are exchangeable within each table. H1: at least one format differs.', '',
         '| Scope | Tables | Statistic | Observed | Critical value (0.05) | p-value | Decision |',
         '| --- | --- | --- | --- | --- | --- | --- |']
    for t in tokens:
        for name, label in (('rm_F', 'Repeated-measures F'), ('friedman_chi2', 'Friedman chi-square')):
            r = t['omnibus'][name]
            L.append(f"| {t['scope']} | {t['tables']} | {label} | {r['statistic']:.2f} | "
                     f"{r['critical_value']:.2f} | {fmt_p(r['p_value'])} | {decision(r['reject_H0'])} |")
    L += ['', '## Pairwise tests', '', 'For each pair, H0: the mean per-table difference in output tokens is 0.', '']
    for t in tokens:
        means = ', '.join(f'{k} {v:.1f}' for k, v in t['format_means'].items())
        L += [f"**{t['scope']}** ({t['tables']} tables; mean output tokens: {means})", '',
              '| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | '
              'p-value | Holm p-value | Decision |', '| --- | --- | --- | --- | --- | --- | --- |']
        for p in t['pairwise']:
            crit = p['critical_abs_mean_difference']
            L.append(f"| {p['comparison']} | {p['mean_difference']:.2f} | {'n/a' if crit is None else f'{crit:.2f}'} | "
                     f"[{p['bootstrap_95'][0]:.2f}, {p['bootstrap_95'][1]:.2f}] | {fmt_p(p['p_value'])} | "
                     f"{fmt_p(p['holm_p_value'])} | {decision(p['reject_H0'])} |")
        L.append('')
    L += ['## Caveats', '',
          '- Exploratory and post-collection: the Round 2 result and a descriptive look at these November means '
          'were seen before testing. The direction (CSV longest) was therefore expected.',
          '- Input length differs by format (CSV is shortest), so format and prompt length are confounded.',
          '- Output tokens include reasoning tokens, so differences reflect how much the model reasoned, not only '
          'answer length; this was not separated.',
          '- Three source datasets with overlapping rows across tables; one model alias and reasoning setting.', '',
          '## Files', '',
          '- `november_token_tests.py`: the analysis. Run from the repository root: '
          '`python -m analysis.november_token_tests.november_token_tests`',
          '- `test_november_token_tests.py`: checks the exported data. Run: '
          '`python -m unittest analysis.november_token_tests.test_november_token_tests -v`',
          '- `results/results.json` (all numbers) and `results/output_tokens_by_table_format.csv` (the 36 x 4 '
          'pooled table tested).', '']
    return '\n'.join(L)


def main():
    data = load()
    tokens, table = run_all(data)
    OUT.mkdir(parents=True, exist_ok=True)
    table.round(4).to_csv(OUT / 'output_tokens_by_table_format.csv')
    (OUT / 'results.json').write_text(json.dumps(dict(
        status='post-collection exploratory tests; no API calls', seed=SEED, alpha=ALPHA,
        source='analysis/november_exports/output_tokens_by_table_task_format.csv',
        output_tokens=tokens), indent=1) + '\n', encoding='utf-8')
    text = summary(tokens)
    (HERE / 'SUMMARY.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
