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

Post-collection, exploratory; no API calls; writes only inside this folder.

Usage (from the repository root):
    python -m analysis.file_vs_inline_tests.file_vs_inline_tests
"""
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.round2_format_tests.stat_tests import block_bootstrap_mean, critical_value, sign_flip_test
from analysis.attribute_selection_tests.classical_tests import paired_t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOV = ROOT / 'results/november_replication'
OUT = HERE / 'results'
CONTRAST = 'file/strict_correct/minus_inline_uniform'
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
        paired_t=dict(t, reject_H0=bool(t['p_value'] < ALPHA)))


# ------------------------------------------------------------------- summary markdown
def fp(p):
    return '<0.0001' if p < 1e-4 else f'{p:.4f}'


def fv(v, digits=2):
    return 'n/a' if v is None else f'{v:.{digits}f}'


def dec(reject):
    return '**Reject H0**' if reject else 'Fail to reject H0'


def summary(r, table, totals, by_format):
    f, i = totals['file'], totals['inline']
    s, w, t = r['sign_flip'], r['wilcoxon'], r['paired_t']
    ci = r['bootstrap_95_pp']
    L = ['# File upload vs inline: does delivery affect accuracy?', '',
         'Hypothesis test of whether giving Luna (gpt-5.6-luna, medium reasoning) a table as an **uploaded file** '
         'changes its accuracy, compared with **pasting the same table inline** in the prompt. Test 1 of the '
         'candidate tests: strict accuracy, pooled over tasks and formats.', '',
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
             'is as strong as 12 tables can give, but limited by the number of tables, not by the size of the effect.'),
          '', '### Where the drop comes from (descriptive, not tested here)', '',
          'Per-table data are published only pooled over formats, so the format breakdown below is totals only '
          '(72 matched calls per cell). Almost all of the loss is CSV uploads.', '',
          '| Task | Format | Inline strict % | File strict % | File minus inline (pp) |',
          '| --- | --- | --- | --- | --- |']
    for row in by_format.itertuples(index=False):
        L.append(f'| {row.task} | {row.format} | {row.inline_strict_pct:.2f} | {row.file_strict_pct:.2f} | '
                 f'{row.file_minus_inline_pp:.2f} |')
    L += ['', '## Caveats', '',
          '- Exploratory: chosen after data collection; the direction of the effect was known before testing.',
          '- 12 tables from three datasets, overlapping source rows, one model alias. File repeats reused the same '
          'uploaded file IDs, so variation across re-uploads is not measured.',
          '- The comparison includes the provider\'s file processing: CSV uploads go through a spreadsheet path, '
          'other formats through text extraction. The test shows that delivery matters, not why.',
          '- 17 file failures were only tiny numeric differences (about 1e-16). A rescoring allowing up to 1e-12 is '
          'candidate test 2, not tested here.', '',
          '## Files', '',
          '- `file_vs_inline_tests.py`: the analysis. Run from the repository root: '
          '`python -m analysis.file_vs_inline_tests.file_vs_inline_tests`. Reuses `sign_flip_test`, '
          '`block_bootstrap_mean` and `critical_value` from `../round2_format_tests/stat_tests.py` and `paired_t` '
          'from `../attribute_selection_tests/classical_tests.py`.',
          '- `test_file_vs_inline_tests.py`: unit tests. Run: '
          '`python -m unittest analysis.file_vs_inline_tests.test_file_vs_inline_tests -v`',
          '- `results/results.json`: every number above; `results/strict_correct_differences_by_table.csv`: the '
          '12 differences tested.', '']
    return '\n'.join(L)


def main():
    table, contrast, totals, by_format = load()
    result = analyze(table)
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / 'strict_correct_differences_by_table.csv', index=False)
    (OUT / 'results.json').write_text(json.dumps(dict(
        status='post-collection exploratory test; no API calls', test='candidate test 1', seed=SEED, alpha=ALPHA,
        source=f'results/november_replication/analysis.json: {CONTRAST}',
        published_bootstrap_95_pp=contrast['descriptive_95_pp'], result=result, totals=totals),
        indent=1) + '\n', encoding='utf-8')
    text = summary(result, table, totals, by_format)
    (HERE / 'SUMMARY.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
