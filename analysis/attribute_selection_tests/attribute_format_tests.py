"""Does input format (CSV / JSON / XML / TXT) affect accuracy on multi-attribute selection?

Data: November repeated study, primary stage, attribute task: 36 sampled tables,
each run in all four formats (x 2 versions x 2 cues x 3 repeats = 12 calls per
table and format). Reads the published per-table differences in
results/november_replication/analysis.json, so all outputs are aggregate.
Post-collection, exploratory; no API calls; writes only inside this folder.

For each outcome (strict_correct = main; present_accuracy, absent_accuracy =
secondary):
  Omnibus  H0: format labels are exchangeable within each table.
           Permutation repeated-measures F (main) and Friedman, 100,000
           within-table permutations; plus classical RM-ANOVA (F distribution)
           and Friedman chi-square approximation for comparison.
  Pairwise H0: mean per-table difference = 0, for all 6 format pairs.
           Paired sign-flip permutation test, Holm-adjusted within outcome;
           plus classical paired t-test (also Holm-adjusted) for comparison.

Usage (from the repository root):
    python -m analysis.attribute_selection_tests.attribute_format_tests
"""
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.round2_format_tests.stat_tests import (
    block_bootstrap_mean, clopper_pearson_upper, friedman_statistic, holm, rm_f_statistic, sign_flip_test,
    within_block_permutation)
from analysis.attribute_selection_tests.classical_tests import friedman_classical, paired_t, rm_anova

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOV = ROOT / 'results/november_replication'
R4 = ROOT / 'results/week4_selection/summary.json'
OUT = HERE / "results"  # default output folder for the attribute task
FORMATS = ('csv', 'json', 'xml', 'txt')
METRICS = {'strict_correct': 'Strict accuracy (whole answer correct)',
           'present_accuracy': 'Present-record values correct',
           'absent_accuracy': 'Absent records reported as NOT_FOUND'}
MAIN = 'strict_correct'
ALPHA = 0.05
SEED = 20261117

# Task-specific wording and file listings; the tests themselves are identical for every task.
TASKS = {
    'attribute': dict(
        name='multi-attribute selection', title='Multi-attribute selection',
        description='find the single record matching several attribute values and copy its output field',
        files=['- `attribute_format_tests.py`: the analysis. Run from the repository root: '
               '`python -m analysis.attribute_selection_tests.attribute_format_tests`',
               '- `classical_tests.py`: classical RM-ANOVA, Friedman and paired t-tests (numpy/math only). '
               'Permutation helpers are imported from `../round2_format_tests/stat_tests.py`.',
               '- `test_classical_tests.py`: unit tests. Run: '
               '`python -m unittest analysis.attribute_selection_tests.test_classical_tests -v`']),
    'join': dict(
        name='two-table join', title='Two-table join',
        description=('find the record matching several attribute values in a records table, then use its '
                     '`link_id` to look up the requested value in a separate, shuffled values table'),
        files=['- `join_format_tests.py`: runs the analysis for the join task. Run from the repository root: '
               '`python -m analysis.two_table_join_tests.join_format_tests`. The test code is shared with '
               '`../attribute_selection_tests/` (`attribute_format_tests.py`, `classical_tests.py`) and '
               '`../round2_format_tests/stat_tests.py`.',
               '- `test_join_format_tests.py`: checks the join data loads correctly and the tests behave as '
               'expected. Run: `python -m unittest analysis.two_table_join_tests.test_join_format_tests -v`']),
    'direct': dict(
        name='direct lookup', title='Direct lookup',
        description='look up the requested field for given `record_id` values and copy it, or answer NOT_FOUND',
        context=('Other direct-lookup data, for context only (not tested here): the two Round 2 lookup studies '
                 '(Oct 21 and Oct 25, 576 primary requests) and the November breadth stage (IBM, avocado, credit '
                 'card; 1,152 requests) were 100% correct in every format. Round 2 is tested in '
                 '`../round2_format_tests/`.'),
        error_bounds=True,
        tokens_note=('- Output tokens are not tested here. November output tokens for all three tasks are tested in '
                     '`../november_token_tests/`, and Round 2 output tokens in `../round2_format_tests/`.'),
        files=['- `direct_format_tests.py`: runs the analysis for the direct-lookup task. Run from the repository '
               'root: `python -m analysis.direct_lookup_tests.direct_format_tests`. The test code is shared with '
               '`../attribute_selection_tests/` (`attribute_format_tests.py`, `classical_tests.py`) and '
               '`../round2_format_tests/stat_tests.py`.',
               '- `test_direct_format_tests.py`: checks the direct-lookup data and error bounds. Run: '
               '`python -m unittest analysis.direct_lookup_tests.test_direct_format_tests -v`']),
}


def table_matrix(contrasts, metric, task='attribute'):
    """36 x 4 matrix in percentage points relative to each table's CSV value.

    Within-table tests are invariant to adding a constant to a table's row, so
    anchoring CSV at 0 is equivalent to using absolute accuracies.
    """
    columns, block_ids = [np.zeros(36)], None
    for fmt in FORMATS[1:]:
        c = contrasts[f'primary/{task}/{metric}/{fmt}_minus_csv']
        if block_ids is None:
            block_ids = c['block_ids']
        assert c['block_ids'] == block_ids, 'block order differs across contrasts'
        columns.append(np.asarray(c['block_differences_pp'], dtype=float))
    matrix = np.column_stack(columns)
    assert matrix.shape == (36, 4)
    return pd.DataFrame(matrix, index=block_ids, columns=FORMATS)


def strata(block_ids):
    # 'core_medical_400_b0' -> 'medical_400'
    return ['_'.join(b.split('_')[1:3]) for b in block_ids]


def test_metric(table):
    m = table.to_numpy()
    n_informative = int((np.ptp(m, axis=1) > 1e-12).sum())
    perm = within_block_permutation(m, dict(rm_F=rm_f_statistic, friedman_chi2=friedman_statistic), seed=SEED)
    classical = dict(rm_anova=rm_anova(m), friedman=friedman_classical(perm['friedman_chi2']['statistic'], 4))
    omnibus = dict(
        permutation_rm_F=dict(statistic=perm['rm_F']['statistic'], critical_value=perm['rm_F']['critical_value'],
                              p_value=perm['rm_F']['p_value']),
        permutation_friedman=dict(statistic=perm['friedman_chi2']['statistic'],
                                  critical_value=perm['friedman_chi2']['critical_value'],
                                  p_value=perm['friedman_chi2']['p_value']),
        classical_rm_anova=classical['rm_anova'], classical_friedman=classical['friedman'],
        permutations=perm['permutations'], tables=len(m), tables_with_any_format_difference=n_informative)
    for key in ('permutation_rm_F', 'permutation_friedman', 'classical_rm_anova', 'classical_friedman'):
        p = omnibus[key]['p_value']
        omnibus[key]['reject_H0'] = None if p is None else bool(p < ALPHA)
    pairs = []
    s = strata(table.index)
    for a, b in combinations(FORMATS, 2):
        diff = (table[b] - table[a]).to_numpy()
        flip = sign_flip_test(diff, seed=SEED)
        t = paired_t(diff)
        pairs.append(dict(comparison=f'{b} minus {a}', mean_difference_pp=float(diff.mean()),
                          bootstrap_95_pp=block_bootstrap_mean(diff, s, seed=SEED),
                          tables_higher=int((diff > 1e-12).sum()), tables_lower=int((diff < -1e-12).sum()),
                          tables_tied=int((np.abs(diff) <= 1e-12).sum()),
                          sign_flip_p=flip['p_value'], sign_flip_method=flip['method'],
                          sign_flip_critical_abs_mean_pp=flip['critical_abs_mean'],
                          t=t['t'], t_df=t['df'], t_p=t['p_value'], t_critical=t['critical_value']))
    for row, adj in zip(pairs, holm([p['sign_flip_p'] for p in pairs])):
        row['sign_flip_holm_p'] = adj
        row['reject_H0'] = bool(adj < ALPHA)
    for row, adj in zip(pairs, holm([p['t_p'] for p in pairs])):
        row['t_holm_p'] = adj
        row['t_reject_H0'] = bool(adj < ALPHA)
    return dict(omnibus=omnibus, pairwise=pairs)


def descriptive(task='attribute'):
    detail = pd.read_csv(NOV / 'primary_task_format_detail.csv')
    nov = detail[detail.task == task].set_index('format').loc[list(FORMATS)]
    nov = nov[['n', 'correct', 'strict_pct', 'present_correct', 'present_n', 'absent_correct', 'absent_n']]
    r4 = json.loads(R4.read_text(encoding='utf-8'))['primary'].get(task)
    if r4 is None:  # Round 4 tested only attribute selection and join
        return nov, None
    r4 = pd.DataFrame({f: dict(requests=v['requests'], strict_correct=v['strict_correct'],
                               present_correct=v['present_correct'], present_n=v['present_n'],
                               absent_correct=v['absent_correct'], absent_n=v['absent_n'])
                       for f, v in r4.items()}).T.loc[list(FORMATS)]
    return nov, r4


def error_bounds(task):
    """Exact one-sided 95% upper bounds on per-request error rates, by format and pooled.

    End-to-end counts API failures as errors; completed-only excludes them. Treats
    requests as independent, so the bounds are optimistic (calls share tables).
    """
    detail = pd.read_csv(NOV / 'primary_task_format_detail.csv')
    completed = pd.read_csv(NOV / 'primary_completed_response_accuracy.csv')
    detail = detail[detail.task == task].set_index('format').loc[list(FORMATS)]
    completed = completed[completed.task == task].set_index('format').loc[list(FORMATS)]
    rows = []
    for f in FORMATS:
        n, ok = int(detail.loc[f, 'n']), int(detail.loc[f, 'correct'])
        cn, cok = int(completed.loc[f, 'completed_requests']), int(completed.loc[f, 'correct'])
        rows.append(dict(format=f, requests=n, errors=n - ok, upper95=clopper_pearson_upper(n - ok, n),
                         completed=cn, completed_errors=cn - cok,
                         completed_upper95=clopper_pearson_upper(cn - cok, cn)))
    n, e = sum(r['requests'] for r in rows), sum(r['errors'] for r in rows)
    cn, ce = sum(r['completed'] for r in rows), sum(r['completed_errors'] for r in rows)
    rows.append(dict(format='all', requests=n, errors=e, upper95=clopper_pearson_upper(e, n),
                     completed=cn, completed_errors=ce, completed_upper95=clopper_pearson_upper(ce, cn)))
    return rows


# ------------------------------------------------------------------- summary markdown
def fp(p):
    if p is None:
        return 'n/a'
    return '<0.0001' if p < 1e-4 else f'{p:.4f}'


def fv(v, digits=2):
    return 'n/a' if v is None else f'{v:.{digits}f}'


def dec(reject):
    return 'n/a' if reject is None else ('**Reject H0**' if reject else 'Fail to reject H0')


def gap_description(nov):
    """E.g. 'CSV lowest, TXT highest', listing ties."""
    pct = nov.strict_pct.round(6)
    low = ' and '.join(f.upper() for f in pct.index[pct == pct.min()])
    high = ' and '.join(f.upper() for f in pct.index[pct == pct.max()])
    return f'{low} lowest, {high} highest'


def bounds_section(rows):
    L = ['## Error-rate bounds', '',
         'With almost no errors, the format tests above cannot reject, so the informative result is how rare errors '
         'are. Exact one-sided 95% Clopper-Pearson upper bounds on the per-request error rate. End-to-end counts '
         'API failures as errors (as the tests above do); completed-only excludes them. These treat requests as '
         'independent, so they are optimistic: calls on the same table are related.', '',
         '| Format | Errors / requests (end-to-end) | 95% upper bound | Errors / completed | 95% upper bound |',
         '| --- | --- | --- | --- | --- |']
    for r in rows:
        L.append(f"| {r['format']} | {r['errors']}/{r['requests']} | {r['upper95']:.2%} | "
                 f"{r['completed_errors']}/{r['completed']} | {r['completed_upper95']:.2%} |")
    return L + ['']


def summary(results, nov, r4, task='attribute', bounds=None):
    info = TASKS[task]
    main = results[MAIN]['omnibus']
    L = [f"# {info['title']}: does format affect accuracy?", '',
         'Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna\'s (gpt-5.6-luna, medium '
         f"reasoning) accuracy on the {info['name']} task: {info['description']}.", '',
         '## Data', '',
         '- **November repeated study, primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x '
         '80/400 rows x 6 tables), each run in all four formats. Each table and format has 12 calls '
         '(original/altered x named/neutral x 3 repeats), 1,728 calls in total.',
         '- **Input:** the published per-table differences in `results/november_replication/analysis.json` '
         f'(`primary/{task}/<metric>/<format>_minus_csv`). No raw responses or API calls.',
         '- **Unit of analysis:** the table. Calls on the same table are averaged first, because they are not '
         'independent.',
         f"- **Only {main['tables_with_any_format_difference']} of 36 tables** show any strict-accuracy difference "
         'between formats; the other tables are tied (almost always 100% in every format).', '',
         f'### Observed accuracy (November, all 1,728 {task} calls)', '',
         '| Format | Strict correct | Strict % | Present values correct | Absent correct |',
         '| --- | --- | --- | --- | --- |']
    for f, r in nov.iterrows():
        L.append(f"| {f} | {int(r.correct)}/{int(r.n)} | {r.strict_pct:.2f}% | "
                 f"{int(r.present_correct)}/{int(r.present_n)} | {int(r.absent_correct)}/{int(r.absent_n)} |")
    context = (info['context'] if r4 is None else
               'Round 4 (Oct 21, 48 requests per format) for context only; it has no per-table data for this task, '
               'so it is not tested: ' + ', '.join(f"{f} {int(r.strict_correct)}/{int(r.requests)}"
                                                    for f, r in r4.iterrows()) + '.')
    L += ['', context, '',
          '## Method', '',
          f'- **Significance level:** alpha = {ALPHA}, two-sided.',
          '- **Main hypothesis:** strict accuracy, omnibus test; present-value and absent-record accuracy are '
          'secondary. This designation was made for this analysis after earlier exploratory looks at the same data, '
          'so it is not a preregistered choice.',
          '- **Omnibus test (main):** within-table permutation test of the repeated-measures F statistic, '
          '100,000 permutations; critical value = 95th percentile of the permutation null. The Friedman statistic '
          'is reported alongside.',
          '- **Classical comparison:** the same repeated-measures ANOVA with its p-value from the F distribution '
          '(F(3, 105), sphericity assumed), and the Friedman chi-square approximation (3 df). These assume '
          'normal residuals and equal variance of differences, which this data (mostly 100%, few nonzero tables) '
          'does not meet, so the permutation results are used for decisions.',
          '- **Pairwise tests:** all 6 pairs. Paired sign-flip permutation test on per-table differences (exact when '
          'at most 20 tables differ), Holm-adjusted within each outcome; this decides. Classical paired t-test '
          '(t(35), Holm-adjusted) shown for comparison. Pairwise results are follow-ups: interpret them only if '
          'the omnibus test rejects.',
          '- **"n/a" critical value** for a permutation test means no possible rearrangement of the data is extreme '
          'enough to reach p < 0.05: too few tables differ, so the test cannot reject whatever their values. '
          'For example, with 4 differing tables the smallest exact two-sided p is 2/2^4 = 0.125.', '']
    for metric, title in METRICS.items():
        o, pairs = results[metric]['omnibus'], results[metric]['pairwise']
        role = 'main' if metric == MAIN else 'secondary'
        L += [f'## {title} ({role})', '',
              'H0: format does not affect this outcome (format labels are exchangeable within each table). '
              'H1: at least one format differs.', '',
              f"Tables with any difference between formats: {o['tables_with_any_format_difference']}/36.", '',
              '### Omnibus tests', '',
              '| Test | Statistic | Critical value (0.05) | p-value | Decision |', '| --- | --- | --- | --- | --- |']
        rm, fr = o['classical_rm_anova'], o['classical_friedman']
        rows = [('Permutation repeated-measures F (decides)', o['permutation_rm_F']['statistic'],
                 o['permutation_rm_F']['critical_value'], o['permutation_rm_F']['p_value'],
                 o['permutation_rm_F']['reject_H0']),
                ('Permutation Friedman chi-square', o['permutation_friedman']['statistic'],
                 o['permutation_friedman']['critical_value'], o['permutation_friedman']['p_value'],
                 o['permutation_friedman']['reject_H0']),
                (f"Classical RM-ANOVA, F({rm['df1']}, {rm['df2']})", rm['F'], rm['critical_value'],
                 rm['p_value'], rm['reject_H0']),
                (f"Classical Friedman, chi-square({fr['df']})", fr['chi2'], fr['critical_value'],
                 fr['p_value'], fr['reject_H0'])]
        for name, stat, crit, p, rej in rows:
            L.append(f'| {name} | {fv(stat)} | {fv(crit)} | {fp(p)} | {dec(rej)} |')
        agree = o['permutation_rm_F']['reject_H0'] == rm['reject_H0']
        L += ['', f"Permutation and classical RM-ANOVA {'agree' if agree else '**disagree**'} on the decision "
              f"(p = {fp(o['permutation_rm_F']['p_value'])} vs {fp(rm['p_value'])}).", '',
              '### Pairwise tests', '',
              'For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).', '',
              '| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | '
              'Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for p in pairs:
            ci = p['bootstrap_95_pp']
            L.append(f"| {p['comparison']} | {p['mean_difference_pp']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | "
                     f"{p['tables_higher']} / {p['tables_lower']} / {p['tables_tied']} | {fp(p['sign_flip_p'])} | "
                     f"{fv(p['sign_flip_critical_abs_mean_pp'], 3)} | {fp(p['sign_flip_holm_p'])} | "
                     f"{dec(p['reject_H0'])} | {fv(p['t'])} | {fv(p['t_critical'])} | {fp(p['t_holm_p'])} | "
                     f"{dec(p['t_reject_H0'])} |")
        L.append('')
    any_reject = (any(results[m]['omnibus']['permutation_rm_F']['reject_H0'] for m in METRICS)
                  or any(p['reject_H0'] for m in METRICS for p in results[m]['pairwise']))
    conclusion = (
        f"**Main test: {dec(main['permutation_rm_F']['reject_H0'])}** (permutation repeated-measures F = "
        f"{fv(main['permutation_rm_F']['statistic'])}, critical value {fv(main['permutation_rm_F']['critical_value'])}, "
        f"p = {fp(main['permutation_rm_F']['p_value'])}; classical F({main['classical_rm_anova']['df1']}, "
        f"{main['classical_rm_anova']['df2']}) p = {fp(main['classical_rm_anova']['p_value'])}). "
        + (f"The data do not show that format affects strict accuracy on the {info['name']} task. "
           if not main['permutation_rm_F']['reject_H0'] else
           f"Format affects strict accuracy on the {info['name']} task in this sample. ")
        + ('No secondary outcome rejects either, and no pairwise comparison is significant. ' if not any_reject else '')
        + f'The observed gap ({gap_description(nov)}) rests on a small number of tables, so the tests have limited '
          'power. Failing to reject means no detectable difference, not that the formats are equivalent.')
    if bounds:
        L += bounds_section(bounds)
        pooled = bounds[-1]
        conclusion += (f" Errors are rare in every format: {pooled['errors']}/{pooled['requests']} requests overall "
                       f"(95% upper bound {pooled['upper95']:.2%} per request), "
                       f"{pooled['completed_errors']}/{pooled['completed']} among completed responses.")
    L += ['## Conclusion', '', conclusion, '',
          '## Caveats', '',
          '- Exploratory: tests chosen after data collection. Earlier exploratory runs on the same data were seen '
          'before this analysis.',
          '- Three source datasets, overlapping source rows across tables, one model alias.',
          info.get('tokens_note',
                   '- Output tokens are not tested here; November output tokens for all three tasks are tested '
                   'in `../november_token_tests/`.'), '',
          '## Files', '',
          *info['files'],
          '- `results/results.json`: every number above; `results/<outcome>_by_table_format.csv`: the 36 x 4 '
          'tables tested (pp relative to CSV).', '']
    return '\n'.join(x for x in L)


def run(task, folder):
    """Run every test for one task and write results/ and SUMMARY.md into `folder`."""
    contrasts = json.loads((NOV / 'analysis.json').read_text(encoding='utf-8'))['contrasts']
    out = folder / 'results'
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for metric in METRICS:
        table = table_matrix(contrasts, metric, task)
        table.round(4).to_csv(out / f'{metric}_by_table_format.csv', index_label='block')
        results[metric] = test_metric(table)
    nov, r4 = descriptive(task)
    bounds = error_bounds(task) if TASKS[task].get('error_bounds') else None
    record = dict(
        status='post-collection exploratory tests; no API calls', task=task, seed=SEED, alpha=ALPHA,
        main_outcome=MAIN, source='results/november_replication/analysis.json', results=results,
        observed_november=nov.reset_index().to_dict('records'),
        round4_descriptive=None if r4 is None else
        r4.reset_index().rename(columns={'index': 'format'}).to_dict('records'))
    if bounds:
        record['error_rate_upper_bounds'] = bounds
    (out / 'results.json').write_text(json.dumps(record, indent=1, default=float) + '\n', encoding='utf-8')
    text = summary(results, nov, r4, task, bounds)
    (folder / 'SUMMARY.md').write_text(text, encoding='utf-8')
    print(text)
    return results


def main():
    run('attribute', HERE)


if __name__ == '__main__':
    main()
