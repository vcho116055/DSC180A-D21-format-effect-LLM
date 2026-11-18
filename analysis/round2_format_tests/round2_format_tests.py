"""Format (CSV / JSON / XML / TXT) hypothesis tests for the two Round 2 lookup studies.

Combines Round 2 (Oct 21: Titanic, red wine, medical) and its repeat on new
datasets (Oct 25: IBM, avocado, credit card). Both used the same design:
3 datasets x 40/200 rows x 3 sampled tables, each run in 4 formats x
named/neutral x original/altered, so every table appears in every format.

Reads only the published request tables, so all outputs are aggregate and safe
to commit. Post-collection, exploratory; makes no API calls.

1. Accuracy: format differences in strict request correctness. Paired
   (block, cue, version) discordant pairs are counted; with no errors, tests are
   undefined, so exact one-sided 95% upper bounds on error rates are reported.
2. Output tokens: per-table mean output tokens per format (includes reasoning
   tokens). Omnibus within-table permutation test (repeated-measures F and
   Friedman), then all six pairwise paired sign-flip tests with Holm correction,
   each with a table-bootstrap 95% interval. Repeated per study as a check.
3. Input tokens: descriptive ratios to CSV (fixed by serialization; not tested).

Usage (from the repository root):  python -m analysis.round2_format_tests.round2_format_tests
"""
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.round2_format_tests.stat_tests import (
    block_bootstrap_mean, clopper_pearson_upper, friedman_statistic, holm, rm_f_statistic,
    sign_flip_test, within_block_permutation)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ALPHA = 0.05
SOURCES = {'oct21': ROOT / 'results/week4_lookup/scored_requests.csv',
           'oct25': ROOT / 'results/round2_newdata/scored_requests.csv'}
OUT = HERE / 'results'
FORMATS = ('csv', 'json', 'xml', 'txt')
SEED = 20261117


def load():
    frames = []
    for study, path in SOURCES.items():
        frame = pd.read_csv(path)
        frames.append(frame[frame.stage == 'main'].assign(study=study))
    main = pd.concat(frames, ignore_index=True)
    assert len(main) == 576 and main.block.nunique() == 36, 'unexpected Round 2 design'
    assert (main.status == 'completed').all()
    cells = main.groupby(['block', 'format']).size()
    assert (cells == 4).all() and len(cells) == 36 * 4, 'every table must appear 4x in every format'
    return main


def accuracy(main):
    errors = (~main.all_correct.astype(bool))
    by_format = {}
    for fmt in FORMATS:
        sub = main[main.format == fmt]
        e = int(errors[sub.index].sum())
        block_any = sub.groupby('block').all_correct.apply(lambda s: (~s.astype(bool)).any())
        by_format[fmt] = dict(requests=len(sub), errors=e,
                              upper95_error_rate_per_request=clopper_pearson_upper(e, len(sub)),
                              tables=len(block_any), tables_with_error=int(block_any.sum()),
                              upper95_share_of_tables_with_error=clopper_pearson_upper(int(block_any.sum()), len(block_any)))
    wide = main.pivot_table(index=['block', 'cue', 'version'], columns='format',
                            values='all_correct', aggfunc='first').astype(bool)
    discordant = {f'{a}_vs_{b}': dict(only_a_correct=int((wide[a] & ~wide[b]).sum()),
                                     only_b_correct=int((~wide[a] & wide[b]).sum()))
                  for a, b in combinations(FORMATS, 2)}
    total_errors = int(errors.sum())
    return dict(total_requests=len(main), total_errors=total_errors,
                upper95_error_rate_pooled=clopper_pearson_upper(total_errors, len(main)),
                by_format=by_format, discordant_pairs=discordant,
                tests=('McNemar, chi-square, ANOVA and permutation tests are undefined or trivially p = 1 '
                       'when no format produced an error; there are zero discordant pairs.'
                       if total_errors == 0 else 'Errors present: run the output-token style tests on accuracy.'))


def token_tests(main, value='output_tokens', label=''):
    table = main.groupby(['block', 'format'])[value].mean().unstack('format')[list(FORMATS)]
    info = main.groupby('block')[['study', 'dataset', 'n_rows']].first().loc[table.index]
    strata = [f'{d}_{n}' for d, n in zip(info.dataset, info.n_rows)]
    m = table.to_numpy()
    omnibus = within_block_permutation(m, dict(rm_F=rm_f_statistic, friedman_chi2=friedman_statistic),
                                       seed=SEED)
    pairs = []
    for a, b in combinations(FORMATS, 2):
        diff = table[b] - table[a]
        test = sign_flip_test(diff.to_numpy(), seed=SEED)
        pairs.append(dict(comparison=f'{b} minus {a}', mean_difference=float(diff.mean()),
                          bootstrap_95=block_bootstrap_mean(diff.to_numpy(), strata, seed=SEED),
                          tables_b_higher=int((diff > 0).sum()), tables_b_lower=int((diff < 0).sum()),
                          p_value=test['p_value'], method=test['method'],
                          critical_abs_mean_difference=test['critical_abs_mean']))
    for row, adj in zip(pairs, holm([p['p_value'] for p in pairs])):
        row['holm_p_value'] = adj
        row['reject_H0'] = bool(adj < ALPHA)
    for name in ('rm_F', 'friedman_chi2'):
        omnibus[name]['reject_H0'] = bool(omnibus[name]['p_value'] < ALPHA)
    return dict(scope=label or 'combined', tables=len(table),
                format_means=table.mean().to_dict(), omnibus=omnibus, pairwise=pairs), table


def input_ratios(main):
    means = main.groupby(['study', 'dataset', 'format']).input_tokens.mean().unstack('format')[list(FORMATS)]
    ratios = means.div(means['csv'], axis=0).round(3)
    overall = main.groupby('format').input_tokens.mean()[list(FORMATS)]
    return ratios.reset_index(), (overall / overall['csv']).round(3).to_dict()


def fmt_p(p):
    return '<0.0001' if p < 1e-4 else f'{p:.4f}'


def report(acc, tokens, ratios, overall_ratio):
    L = ['# Round 2 format tests (CSV / JSON / XML / TXT)', '',
         'Post-collection exploratory tests on the two Round 2 lookup studies combined: Oct 21 '
         '(Titanic, red wine, medical) and Oct 25 (IBM, avocado, credit card). 576 primary requests, '
         '36 sampled tables; every table was run 4 times in every format (named/neutral x original/altered). '
         'The unit of analysis is the table. No API calls; inputs are the published `scored_requests.csv` files.', '',
         '## 1. Accuracy', '',
         f"Errors: **{acc['total_errors']}/{acc['total_requests']}** primary requests. "
         f"Pooled one-sided 95% upper bound on the per-request error rate: {acc['upper95_error_rate_pooled']:.2%}.", '',
         acc['tests'], '',
         '| format | requests | errors | 95% upper bound, per request | tables with an error | 95% upper bound, share of tables |',
         '| --- | --- | --- | --- | --- | --- |']
    for f, r in acc['by_format'].items():
        L.append(f"| {f} | {r['requests']} | {r['errors']} | {r['upper95_error_rate_per_request']:.2%} | "
                 f"{r['tables_with_error']}/{r['tables']} | {r['upper95_share_of_tables_with_error']:.2%} |")
    L += ['', 'Per-request bounds assume independent requests and are optimistic; the per-table bound uses '
          'the independent unit. These bound how often errors occur; they do not show the formats are equivalent '
          'on harder tasks.', '',
          '## 2. Output tokens', '',
          'Output tokens include hidden reasoning tokens; in the Oct 25 study (where the split is recorded '
          'locally) the visible answer is roughly fixed, so differences mainly reflect how much the model reasoned. '
          'H0: format labels are exchangeable within each table.', '']
    for t in tokens:
        o = t['omnibus']
        means = ', '.join(f'{k} {v:.1f}' for k, v in t['format_means'].items())
        L += [f"### {t['scope']} ({t['tables']} tables)", '',
              f'Mean output tokens: {means}.', '',
              f"Omnibus: repeated-measures F = {o['rm_F']['statistic']:.2f}, permutation p = {fmt_p(o['rm_F']['p_value'])}; "
              f"Friedman chi2 = {o['friedman_chi2']['statistic']:.2f}, permutation p = {fmt_p(o['friedman_chi2']['p_value'])} "
              f"({o['permutations']} within-table permutations).", '',
              '| comparison | mean diff (tokens) | table bootstrap 95% | tables higher / lower | sign-flip p | Holm p |',
              '| --- | --- | --- | --- | --- | --- |']
        for p in t['pairwise']:
            L.append(f"| {p['comparison']} | {p['mean_difference']:.2f} | [{p['bootstrap_95'][0]:.2f}, {p['bootstrap_95'][1]:.2f}] | "
                     f"{p['tables_b_higher']} / {p['tables_b_lower']} | {fmt_p(p['p_value'])} | {fmt_p(p['holm_p_value'])} |")
        L.append('')
    L += ['## 3. Input tokens (descriptive)', '',
          'Input length is fixed by the serialization, so it is described rather than tested. Overall ratio to CSV: ' +
          ', '.join(f'{k} {v:.2f}' for k, v in overall_ratio.items()) + '.', '',
          '| study | dataset | csv | json | xml | txt |', '| --- | --- | --- | --- | --- | --- |']
    for row in ratios.itertuples(index=False):
        L.append(f'| {row.study} | {row.dataset} | {row.csv:.2f} | {row.json:.2f} | {row.xml:.2f} | {row.txt:.2f} |')
    L += ['', '## Caveats', '',
          '- Exploratory, chosen after data collection; not a preregistered analysis.',
          '- The two studies differ in datasets, date and SDK version; permutation is within table, so study-level '
          'differences do not bias the format tests, but per-study results are shown as a consistency check.',
          '- Sampled tables overlap in source rows; one model alias (gpt-5.6-luna, medium reasoning) was tested.', '']
    return '\n'.join(L)


def main():
    data = load()
    acc = accuracy(data)
    combined, table = token_tests(data)
    per_study = [token_tests(data[data.study == s], label=s)[0] for s in SOURCES]
    ratios, overall_ratio = input_ratios(data)
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(status='post-collection exploratory tests; no API calls', seed=SEED,
                  sources=[str(p.relative_to(ROOT)).replace('\\', '/') for p in SOURCES.values()],
                  accuracy=acc, output_tokens=[combined, *per_study],
                  input_token_ratio_to_csv=overall_ratio)
    (OUT / 'results.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    table.round(3).to_csv(OUT / 'output_tokens_by_table_format.csv')
    ratios.to_csv(OUT / 'input_token_ratios.csv', index=False)
    text = report(acc, [combined, *per_study], ratios, overall_ratio)
    (OUT / 'REPORT.md').write_text(text, encoding='utf-8')
    brief = summary(acc, [combined, *per_study], overall_ratio)
    (HERE / 'SUMMARY.md').write_text(brief, encoding='utf-8')
    print(brief)


def decision(reject):
    return '**Reject H0**' if reject else 'Fail to reject H0'


def summary(acc, tokens, overall_ratio):
    combined = tokens[0]
    L = ['# Round 2 format tests: summary of results', '',
         'Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna (gpt-5.6-luna, medium '
         'reasoning) on the Round 2 record-lookup task. Both Round 2 studies are combined: Oct 21 (Titanic, red wine, '
         'medical) and Oct 25 (IBM, avocado, credit card), giving 36 sampled tables and 576 primary requests. Every '
         'table was run 4 times in each format (named/neutral description x original/altered values).', '',
         '## Method', '',
         '- **Unit of analysis:** the sampled table. Requests on the same table are averaged first, because they are '
         'not independent.',
         f'- **Significance level:** alpha = {ALPHA}, two-sided.',
         '- **Omnibus tests** (all four formats at once): within-table permutation test, 100,000 permutations, '
         'using a repeated-measures F statistic and a tie-corrected Friedman chi-square statistic. Critical values are '
         'the 95th percentiles of the permutation null distributions. Reject H0 when p < 0.05 '
         '(equivalently, statistic >= critical value).',
         '- **Pairwise tests** (6 format pairs): paired sign-flip permutation test on the per-table mean difference, '
         '200,000 Monte Carlo sign assignments. The critical value is the smallest |mean difference| that is '
         'significant at 0.05 before adjustment. Decisions use **Holm-adjusted p < 0.05** within each family of 6.',
         '- **Per-study results** repeat the tests on each study alone (18 tables each) as a consistency check.',
         '- **Data:** the published `results/week4_lookup/scored_requests.csv` and '
         '`results/round2_newdata/scored_requests.csv`. No API calls.', '',
         '## Results at a glance', '',
         f"- **Accuracy:** {acc['total_errors']}/{acc['total_requests']} errors. No test can compare formats; "
         'H0 cannot be rejected. Each format\'s per-request error rate is at most '
         f"{acc['by_format']['csv']['upper95_error_rate_per_request']:.2%} (95% upper bound).",
         f"- **Output tokens:** format matters (omnibus p < 0.0001). CSV produces the longest outputs "
         f"({combined['format_means']['csv']:.1f} tokens on average), and JSON, XML and TXT are each significantly "
         'shorter, in both studies separately.',
         '- **Input tokens:** not tested (fixed by serialization). Relative to CSV: ' +
         ', '.join(f'{k} {v:.2f}x' for k, v in overall_ratio.items() if k != 'csv') + '.', '',
         '## Test 1: accuracy by format', '',
         '| Hypothesis | Test | Result | Decision |', '| --- | --- | --- | --- |',
         '| H0: the four formats have equal strict-correct rates. H1: at least one differs. | McNemar / chi-square / '
         'ANOVA / permutation | Not computable: 0 errors, 0 discordant pairs; any test gives p = 1 | '
         'Fail to reject H0 |', '',
         '| Format | Errors / requests | 95% upper bound, per request | Tables with an error | '
         '95% upper bound, share of tables |', '| --- | --- | --- | --- | --- |']
    for f, r in acc['by_format'].items():
        L.append(f"| {f} | {r['errors']}/{r['requests']} | {r['upper95_error_rate_per_request']:.2%} | "
                 f"{r['tables_with_error']}/{r['tables']} | {r['upper95_share_of_tables_with_error']:.2%} |")
    L += ['', 'Failing to reject is not evidence that the formats are equally accurate; it reflects a ceiling. '
          'The per-table bound is the more honest one, because tables are the independent unit.', '',
          '## Test 2: output tokens by format', '',
          'Output tokens include hidden reasoning tokens. The visible answer is roughly fixed in length, so '
          'differences mainly reflect how much the model reasoned before answering.', '',
          '### Omnibus tests', '',
          'H0: format labels are exchangeable within each table (format does not affect output tokens). '
          'H1: at least one format differs.', '',
          '| Scope | Tables | Statistic | Observed | Critical value (0.05) | p-value | Decision |',
          '| --- | --- | --- | --- | --- | --- | --- |']
    for t in tokens:
        for name, label in (('rm_F', 'Repeated-measures F'), ('friedman_chi2', 'Friedman chi-square')):
            o = t['omnibus'][name]
            L.append(f"| {t['scope']} | {t['tables']} | {label} | {o['statistic']:.2f} | "
                     f"{o['critical_value']:.2f} | {fmt_p(o['p_value'])} | {decision(o['reject_H0'])} |")
    L += ['', '### Pairwise tests', '',
          'For each pair, H0: the mean per-table difference in output tokens is 0. H1: it is not 0.', '']
    for t in tokens:
        means = ', '.join(f'{k} {v:.1f}' for k, v in t['format_means'].items())
        L += [f"**{t['scope']}** ({t['tables']} tables; mean output tokens: {means})", '',
              '| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | '
              'p-value | Holm p-value | Decision |',
              '| --- | --- | --- | --- | --- | --- | --- |']
        for p in t['pairwise']:
            L.append(f"| {p['comparison']} | {p['mean_difference']:.2f} | {p['critical_abs_mean_difference']:.2f} | "
                     f"[{p['bootstrap_95'][0]:.2f}, {p['bootstrap_95'][1]:.2f}] | {fmt_p(p['p_value'])} | "
                     f"{fmt_p(p['holm_p_value'])} | {decision(p['reject_H0'])} |")
        L.append('')
    L += ['## Interpretation', '',
          '- **Accuracy:** no format difference can be detected because Luna made no errors on this task. '
          'Harder tasks (Round 4, November study) are needed to compare accuracy.',
          '- **Output tokens:** CSV leads to longer outputs than every other format, in the combined data and in '
          'each study alone. Differences among JSON, XML and TXT are smaller and not consistent across studies. '
          'Since CSV prompts are also the shortest, CSV trades fewer input tokens for more reasoning.',
          '- The reasoning-token explanation is an inference: the reasoning/answer split is recorded only in the '
          'local Oct 25 response log and was not tested here.', '',
          '## Caveats', '',
          '- Exploratory: these tests were chosen after data collection, after seeing that CSV had the highest mean.',
          '- The two studies differ in datasets, date and SDK version. Permutation is within table, so this does '
          'not bias the format tests, but study-level differences are not interpretable.',
          '- Sampled tables overlap in source rows; one model alias was tested.', '',
          '## Files', '',
          '- `round2_format_tests.py`: the analysis. Run from the repository root: '
          '`python -m analysis.round2_format_tests.round2_format_tests`',
          '- `stat_tests.py`: test functions (numpy only).',
          '- `test_stat_tests.py`: unit tests. Run: `python -m unittest analysis.round2_format_tests.test_stat_tests -v`',
          '- `results/`: `REPORT.md` (full report), `results.json` (all numbers), '
          '`output_tokens_by_table_format.csv` (36 x 4 table tested), `input_token_ratios.csv`.', '']
    return '\n'.join(L)


if __name__ == '__main__':
    main()
