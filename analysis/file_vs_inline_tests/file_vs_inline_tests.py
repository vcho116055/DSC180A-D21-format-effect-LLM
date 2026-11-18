"""Does uploading the table as a file change strict accuracy, compared with pasting it inline?

Test 1 (main): November study, file stage. 12 tables, each run as an uploaded
file and inline (neutral description; 3 tasks x 4 formats x 2 versions x
3 repeats = 72 calls per table and delivery). The value tested is each table's
file-minus-inline difference in strict accuracy, pooled over tasks and formats,
read from the published `file/strict_correct/minus_inline_uniform` contrast.

H0: the mean per-table difference is 0 (delivery does not affect accuracy).
H1: it is not 0. Two-sided, alpha = 0.05.
  Decides:  exact paired sign-flip permutation test.
  Checks:   exact Wilcoxon signed-rank test; classical paired t-test.
  Sensitivity: the same three tests with numeric differences up to 1e-12 scored
           as correct (published `tolerant_correct` contrast).

Test 2 (by format): the same 12 tables, file minus inline difference computed separately
for each format (18 matched calls per table, format and delivery), from the per-table
export in ../november_exports/file_vs_inline_by_table_format.csv. Exact sign-flip test
per format, Holm-adjusted across the 4 formats; strict and precision-tolerant scoring.

Post-collection, exploratory; no API calls; writes only inside this folder.

Usage (from the repository root):
    python -m analysis.file_vs_inline_tests.file_vs_inline_tests
"""
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.round2_format_tests.stat_tests import block_bootstrap_mean, critical_value, holm, sign_flip_test
from analysis.attribute_selection_tests.classical_tests import paired_t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOV = ROOT / 'results/november_replication'
OUT = HERE / 'results'
CONTRAST = 'file/strict_correct/minus_inline_uniform'
BY_FORMAT = ROOT / 'analysis/november_exports/file_vs_inline_by_table_format.csv'
FORMATS = ('csv', 'json', 'xml', 'txt')
ALPHA = 0.05
SEED = 20261117


def wilcoxon_exact(differences, alpha=ALPHA):
    """Exact two-sided Wilcoxon signed-rank test (zeros dropped, midranks for ties).

    Returns W+ (sum of ranks of positive differences), the two-sided p-value from
    enumerating all sign assignments, and the critical distance d: reject H0 when
    |W+ - n(n+1)/4| >= d (None if no outcome is extreme enough).
    """
    d = np.asarray(differences, dtype=float)
    d = d[np.abs(d) > 1e-12]
    n = int(d.size)
    if n == 0:
        return dict(W_plus=0.0, n_nonzero=0, center=0.0, p_value=1.0, critical_distance=None)
    absd = np.round(np.abs(d), 9)
    order = np.argsort(absd)
    ranks = np.empty(n)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and absd[order[j + 1]] == absd[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    w_plus = float(ranks[d > 0].sum())
    center = float(ranks.sum() / 2)
    null = np.array(list(product((0.0, 1.0), repeat=n))) @ ranks
    distance = np.abs(null - center)
    p = float(np.mean(distance >= abs(w_plus - center) - 1e-9))
    return dict(W_plus=w_plus, n_nonzero=n, center=center, p_value=p,
                critical_distance=critical_value(distance, alpha))


def load():
    contrasts = json.loads((NOV / 'analysis.json').read_text(encoding='utf-8'))['contrasts']
    c = contrasts[CONTRAST]
    table = pd.DataFrame(dict(block=c['block_ids'], difference_pp=c['block_differences_pp']))
    parts = table.block.str.split('_')
    table['dataset'], table['n_rows'] = parts.str[1], parts.str[2].astype(int)
    assert len(table) == 12 and table.block.is_unique
    # Cross-check against the independently written precision-sensitivity file.
    sensitivity = json.loads((NOV / 'file_precision_sensitivity.json').read_text(encoding='utf-8'))
    assert np.allclose(table.difference_pp, sensitivity['contrasts']['exact_correct']['block_differences_pp'])
    table['tolerant_difference_pp'] = sensitivity['contrasts']['tolerant_correct']['block_differences_pp']
    totals = {r['delivery']: r for r in sensitivity['totals']}
    by_format = pd.read_csv(NOV / 'file_delivery_by_task_format.csv')
    return table, c, totals, by_format


def analyze(table):
    d = table.difference_pp.to_numpy()
    strata = (table.dataset + '_' + table.n_rows.astype(str)).tolist()
    flip = sign_flip_test(d, seed=SEED)
    wil = wilcoxon_exact(d)
    t = paired_t(d)
    m = flip['nonzero']
    return dict(
        tables=len(d), mean_difference_pp=float(d.mean()),
        bootstrap_95_pp=block_bootstrap_mean(d, strata, seed=SEED),
        tables_file_worse=int((d < -1e-12).sum()), tables_file_better=int((d > 1e-12).sum()),
        tables_tied=int((np.abs(d) <= 1e-12).sum()),
        smallest_attainable_p=2 / 2 ** m if m else 1.0,
        sign_flip=dict(p_value=flip['p_value'], method=flip['method'], nonzero=m,
                       critical_abs_mean_pp=flip['critical_abs_mean'], reject_H0=bool(flip['p_value'] < ALPHA)),
        wilcoxon=dict(wil, reject_H0=bool(wil['p_value'] < ALPHA)),
        paired_t=dict(t, reject_H0=bool(t['p_value'] < ALPHA)),
        tolerant=tolerant_check(table.tolerant_difference_pp.to_numpy()))


def tolerant_check(d):
    """Same tests on the precision-tolerant differences (|numeric error| <= 1e-12 scored correct)."""
    flip, wil, t = sign_flip_test(d, seed=SEED), wilcoxon_exact(d), paired_t(d)
    return dict(mean_difference_pp=float(d.mean()), tables_file_worse=int((d < -1e-12).sum()),
                tables_file_better=int((d > 1e-12).sum()), nonzero=flip['nonzero'],
                sign_flip_p=flip['p_value'], wilcoxon_p=wil['p_value'], paired_t_p=t['p_value'],
                reject_H0=bool(flip['p_value'] < ALPHA))


def per_format():
    """Test 2: file minus inline per table, separately for each format; Holm across formats."""
    data = pd.read_csv(BY_FORMAT)
    assert len(data) == 12 * 4 * 2 and (data.attempts == 18).all()
    out, tables = {}, {}
    for metric in ('exact_correct', 'tolerant_correct'):
        wide = data.assign(pct=100 * data[metric] / data.attempts).pivot_table(
            index=['block', 'format'], columns='delivery', values='pct')
        diff = (wide['file'] - wide['inline']).unstack('format')[list(FORMATS)]
        tables[metric] = diff
        rows = []
        for fmt in FORMATS:
            d = diff[fmt].to_numpy()
            flip = sign_flip_test(d, seed=SEED)
            rows.append(dict(format=fmt, mean_difference_pp=float(d.mean()),
                             tables_file_worse=int((d < -1e-12).sum()), tables_file_better=int((d > 1e-12).sum()),
                             nonzero=flip['nonzero'], p_value=flip['p_value'], method=flip['method']))
        for row, adj in zip(rows, holm([r['p_value'] for r in rows])):
            row['holm_p_value'] = adj
            row['reject_H0'] = bool(adj < ALPHA)
        out[metric] = rows
    return out, tables


# ------------------------------------------------------------------- summary markdown
def fp(p):
    return '<0.0001' if p < 1e-4 else f'{p:.4f}'


def fv(v, digits=2):
    return 'n/a' if v is None else f'{v:.{digits}f}'


def dec(reject):
    return '**Reject H0**' if reject else 'Fail to reject H0'


def summary(r, table, totals, by_format, fmt_tests):
    f, i = totals['file'], totals['inline']
    s, w, t = r['sign_flip'], r['wilcoxon'], r['paired_t']
    ci = r['bootstrap_95_pp']
    tol = r['tolerant']
    L = ['# File upload vs inline: does delivery affect accuracy?', '',
         'Hypothesis test of whether giving Luna (gpt-5.6-luna, medium reasoning) a table as an **uploaded file** '
         'changes its accuracy, compared with **pasting the same table inline** in the prompt. Outcome: strict '
         'accuracy, pooled over tasks and formats, with a precision-tolerant scoring sensitivity check.', '',
         '## Data', '',
         '- **November repeated study, file stage** (Nov 3-4): 12 tables (the first 2 primary tables per dataset '
         'and size: Titanic, red wine, medical x 80/400 rows).',
         '- Each table was run both ways with the neutral description: 3 tasks (direct, attribute, join) x '
         '4 formats x original/altered x 3 repeats = 72 calls per table and delivery. The inline calls are the '
         'matching primary-stage calls.',
         f"- **Totals:** uploaded {f['exact_correct']}/{f['attempts']} strict correct "
         f"({f['exact_correct'] / f['attempts']:.2%}; {f['attempts'] - f['completed']} API failures); "
         f"inline {i['exact_correct']}/{i['attempts']} ({i['exact_correct'] / i['attempts']:.2%}).",
         f'- **Input:** the published per-table differences in `results/november_replication/analysis.json` '
         f'(`{CONTRAST}`), cross-checked against `file_precision_sensitivity.json` (identical). No API calls.',
         '- **Unit of analysis:** the table. Each value is a table\'s file-minus-inline difference in strict '
         'accuracy over its 72 matched calls.', '',
         '### Per-table differences (file minus inline, percentage points)', '',
         '| Table | Dataset | Rows | Difference (pp) |', '| --- | --- | --- | --- |']
    for row in table.itertuples(index=False):
        L.append(f'| {row.block} | {row.dataset} | {row.n_rows} | {row.difference_pp:.2f} |')
    L += ['', f"Mean {r['mean_difference_pp']:.2f} pp (table bootstrap 95% CI [{ci[0]:.2f}, {ci[1]:.2f}]). "
          f"Upload worse in {r['tables_file_worse']} tables, better in {r['tables_file_better']}, tied in "
          f"{r['tables_tied']}.", '',
          '## Method', '',
          '- **H0:** the mean per-table difference is 0 (delivery does not affect strict accuracy). '
          '**H1:** it is not 0. Two-sided, alpha = 0.05.',
          '- **Decides: exact paired sign-flip permutation test.** Under H0 each table\'s difference is equally '
          f"likely to be positive or negative; all {2 ** s['nonzero']} sign assignments of the "
          f"{s['nonzero']} nonzero differences are enumerated. Statistic: |mean difference|. Critical value: "
          'the smallest |mean difference| with exact two-sided p <= 0.05.',
          '- **Check: exact Wilcoxon signed-rank test.** Zeros dropped, midranks for ties, p from enumerating all '
          'sign assignments. Statistic W+ (sum of ranks of positive differences); reject when |W+ - center| is at '
          'least the critical distance.',
          '- **Check: classical paired t-test**, t(11). Assumes normally distributed differences, which 5 zeros '
          'and a cap at 100% make doubtful; reported for comparison only.',
          f"- **Minimum attainable p:** with {s['nonzero']} nonzero tables, an exact two-sided test cannot give "
          f"p below 2/2^{s['nonzero']} = {r['smallest_attainable_p']:.4f}.", '',
          '## Results', '',
          '| Test | Statistic | Critical value (0.05) | p-value | Decision |', '| --- | --- | --- | --- | --- |',
          f"| Exact sign-flip (decides) | abs. mean diff = {abs(r['mean_difference_pp']):.2f} pp | "
          f"{fv(s['critical_abs_mean_pp'])} pp | {fp(s['p_value'])} | {dec(s['reject_H0'])} |",
          f"| Exact Wilcoxon signed-rank | W+ = {w['W_plus']:.1f} (center {w['center']:.1f}, "
          f"distance {abs(w['W_plus'] - w['center']):.1f}) | distance {fv(w['critical_distance'], 1)} | "
          f"{fp(w['p_value'])} | {dec(w['reject_H0'])} |",
          f"| Classical paired t-test, t({t['df']}) | t = {fv(t['t'])} | {fv(t['critical_value'])} | "
          f"{fp(t['p_value'])} | {dec(t['reject_H0'])} |", '',
          '### Sensitivity: precision-tolerant scoring', '',
          f"{f['precision_only_failures']} uploaded answers failed only by tiny numeric differences (about 1e-16). "
          'Rescoring numeric differences up to 1e-12 as correct (published `tolerant_correct` contrast) and '
          'rerunning the same tests:', '',
          '| Scoring | Mean diff (pp) | Tables worse / better | Exact sign-flip p | Wilcoxon p | Paired t p | '
          'Decision |', '| --- | --- | --- | --- | --- | --- | --- |',
          f"| Strict (main) | {r['mean_difference_pp']:.2f} | {r['tables_file_worse']} / {r['tables_file_better']} | "
          f"{fp(s['p_value'])} | {fp(w['p_value'])} | {fp(t['p_value'])} | {dec(s['reject_H0'])} |",
          f"| Tolerant (1e-12) | {tol['mean_difference_pp']:.2f} | {tol['tables_file_worse']} / "
          f"{tol['tables_file_better']} | {fp(tol['sign_flip_p'])} | {fp(tol['wilcoxon_p'])} | "
          f"{fp(tol['paired_t_p'])} | {dec(tol['reject_H0'])} |", '',
          '## Conclusion', '',
          (f"{dec(s['reject_H0'])} (exact sign-flip p = {fp(s['p_value'])}). "
           + ('Uploading the table as a file lowered strict accuracy compared with pasting it inline: '
              f"by {abs(r['mean_difference_pp']):.2f} percentage points on average (95% CI "
              f"[{ci[0]:.2f}, {ci[1]:.2f}]), and every table that differed did worse when uploaded. "
              if s['reject_H0'] and r['mean_difference_pp'] < 0 else
              'The data do not show that delivery method affects strict accuracy. ')
           + f"The Wilcoxon test (p = {fp(w['p_value'])}) and paired t-test (p = {fp(t['p_value'])}) "
           + ('agree. ' if w['reject_H0'] == s['reject_H0'] == t['reject_H0'] else 'do not all agree. ')
           + f"The p-value is the smallest this design allows ({r['smallest_attainable_p']:.4f}), so the evidence "
             'is as strong as 12 tables can give, but limited by the number of tables, not by the size of the effect. '
           + f"Under precision-tolerant scoring the drop shrinks to {abs(tol['mean_difference_pp']):.2f} pp and the "
             f"exact sign-flip p rises to {fp(tol['sign_flip_p'])} ({tol['nonzero']} tables differ, all worse when "
             'uploaded); ' + ('H0 is still rejected, so the effect is not explained by numeric precision alone.'
                              if tol['reject_H0'] else 'H0 is no longer rejected at 0.05.')),
          '', '### Where the drop comes from (descriptive, not tested here)', '',
          'Totals by task and format from the published summary (no test; test 2 below tests each format per table). '
          '(72 matched calls per cell). Almost all of the loss is CSV uploads.', '',
          '| Task | Format | Inline strict % | File strict % | File minus inline (pp) |',
          '| --- | --- | --- | --- | --- |']
    for row in by_format.itertuples(index=False):
        L.append(f'| {row.task} | {row.format} | {row.inline_strict_pct:.2f} | {row.file_strict_pct:.2f} | '
                 f'{row.file_minus_inline_pp:.2f} |')
    L += ['', '## Test 2: which formats are affected?', '',
          'Same 12 tables, but the file-minus-inline difference is computed separately for each format: 18 matched '
          'calls per table, format and delivery (3 tasks x original/altered x 3 repeats). Input: '
          '`analysis/november_exports/file_vs_inline_by_table_format.csv`, per-table counts exported from the local '
          'raw run. For each format, H0: the mean per-table difference is 0. Exact sign-flip test, Holm-adjusted '
          'across the 4 formats within each scoring. With m tables that differ, the smallest attainable p is 2/2^m.', '',
          '| Scoring | Format | Mean diff (pp) | Tables worse / better | Exact sign-flip p | Holm p | Decision |',
          '| --- | --- | --- | --- | --- | --- | --- |']
    for metric, label in (('exact_correct', 'Strict'), ('tolerant_correct', 'Tolerant (1e-12)')):
        for row in fmt_tests[metric]:
            L.append(f"| {label} | {row['format']} | {row['mean_difference_pp']:.2f} | {row['tables_file_worse']} / "
                     f"{row['tables_file_better']} | {fp(row['p_value'])} | {fp(row['holm_p_value'])} | "
                     f"{dec(row['reject_H0'])} |")
    rejected = {m: [r['format'].upper() for r in rows if r['reject_H0']] for m, rows in fmt_tests.items()}
    L += ['', 'Formats where uploading significantly changed accuracy: strict scoring: '
          f"{', '.join(rejected['exact_correct']) or 'none'}; tolerant scoring: "
          f"{', '.join(rejected['tolerant_correct']) or 'none'}. A format that does not reject may still have a "
          'small effect: with few tables that differ, these tests have little power.', '',
          '## Caveats', '',
          '- Exploratory: chosen after data collection; the direction of the effect was known before testing.',
          '- The table-bootstrap 95% CI resamples within 6 dataset x size groups of only 2 tables each, which '
          'understates variability (resampling 2 values from 2 roughly halves the variance), so the interval is too '
          'narrow. The exact permutation p-values do not depend on it.',
          '- 12 tables from three datasets, overlapping source rows, one model alias. File repeats reused the same '
          'uploaded file IDs, so variation across re-uploads is not measured.',
          '- The comparison includes the provider\'s file processing: CSV uploads go through a spreadsheet path, '
          'other formats through text extraction. The test shows that delivery matters, not why.',
          f"- {f['precision_only_failures']} file failures were only tiny numeric differences (about 1e-16); the "
          'precision-tolerant sensitivity above shows how much of the effect they account for.', '',
          '## Files', '',
          '- `file_vs_inline_tests.py`: the analysis. Run from the repository root: '
          '`python -m analysis.file_vs_inline_tests.file_vs_inline_tests`. Reuses `sign_flip_test`, '
          '`block_bootstrap_mean` and `critical_value` from `../round2_format_tests/stat_tests.py` and `paired_t` '
          'from `../attribute_selection_tests/classical_tests.py`.',
          '- `test_file_vs_inline_tests.py`: unit tests. Run: '
          '`python -m unittest analysis.file_vs_inline_tests.test_file_vs_inline_tests -v`',
          '- `results/results.json`: every number above; `results/strict_correct_differences_by_table.csv`: the '
          '12 differences tested in test 1; `results/differences_by_table_format.csv`: the 12 x 4 differences '
          'tested in test 2 (strict and tolerant).', '']
    return '\n'.join(L)


def main():
    table, contrast, totals, by_format = load()
    result = analyze(table)
    fmt_tests, fmt_tables = per_format()
    OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(fmt_tables, names=['scoring']).round(4).to_csv(OUT / 'differences_by_table_format.csv')
    table.to_csv(OUT / 'strict_correct_differences_by_table.csv', index=False)
    (OUT / 'results.json').write_text(json.dumps(dict(
        status='post-collection exploratory test; no API calls', tests='test 1 (pooled) and test 2 (by format)', seed=SEED, alpha=ALPHA,
        source=f'results/november_replication/analysis.json: {CONTRAST}',
        published_bootstrap_95_pp=contrast['descriptive_95_pp'], result=result, totals=totals,
        tolerant_source='results/november_replication/file_precision_sensitivity.json: tolerant_correct',
        by_format_source='analysis/november_exports/file_vs_inline_by_table_format.csv',
        by_format=fmt_tests),
        indent=1) + '\n', encoding='utf-8')
    text = summary(result, table, totals, by_format, fmt_tests)
    (HERE / 'SUMMARY.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
