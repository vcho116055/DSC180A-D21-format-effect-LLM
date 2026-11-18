"""Reusable block-level test helpers (numpy only, no scipy).

All tests take one value per sampled table (block) and condition, so calls that
share a table are never treated as independent observations.
"""
from itertools import product
import math

import numpy as np


def holm(pvalues):
    """Holm step-down adjusted p-values, returned in input order."""
    p = np.asarray(pvalues, dtype=float)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(np.argsort(p)):
        running = max(running, (len(p) - rank) * p[index])
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def critical_value(null, alpha=0.05):
    """Smallest c with P(null >= c) <= alpha: reject H0 when the observed statistic >= c.

    Returns None when no value of the null distribution is extreme enough (the
    test cannot reach significance at this alpha).
    """
    s = np.sort(np.asarray(null, dtype=float))
    values = np.unique(np.round(s, 9))
    tail = (len(s) - np.searchsorted(np.round(s, 9), values, side='left')) / len(s)
    ok = values[tail <= alpha]
    return float(ok[0]) if ok.size else None


def sign_flip_test(differences, draws=200_000, seed=0, exact_limit=20, alpha=0.05):
    """Two-sided paired sign-flip permutation test of mean difference = 0.

    Exact when there are at most `exact_limit` nonzero differences (zeros are
    invariant under sign flipping); otherwise Monte Carlo with add-one correction.
    The critical value is on |mean difference| (unadjusted, two-sided, level alpha).
    """
    d = np.asarray(differences, dtype=float)
    nonzero = d[np.abs(d) > 1e-12]
    m = int(nonzero.size)
    if m == 0:
        return dict(p_value=1.0, method='all differences zero', nonzero=0, critical_abs_mean=None)
    observed = abs(nonzero.sum())
    if m <= exact_limit:
        signs = np.array(list(product((-1.0, 1.0), repeat=m)))
        null = np.abs(signs @ nonzero)
        p = float(np.mean(null >= observed - 1e-9))
        method = f'exact ({2 ** m} sign assignments)'
    else:
        rng = np.random.default_rng(seed)
        chunks = []
        for start in range(0, draws, 20_000):
            size = min(20_000, draws - start)
            chunks.append(np.abs(rng.choice((-1.0, 1.0), size=(size, m)) @ nonzero))
        null = np.concatenate(chunks)
        p = (int((null >= observed - 1e-9).sum()) + 1) / (draws + 1)
        method = f'Monte Carlo ({draws} draws)'
    crit = critical_value(null, alpha)
    return dict(p_value=p, method=method, nonzero=m,
                critical_abs_mean=None if crit is None else crit / len(d))


def rm_f_statistic(m):
    """Repeated-measures ANOVA F for (..., blocks, conditions) arrays."""
    m = np.asarray(m, dtype=float)
    n, k = m.shape[-2:]
    grand = m.mean(axis=(-2, -1), keepdims=True)
    ss_cond = n * ((m.mean(axis=-2, keepdims=True) - grand) ** 2).sum(axis=(-2, -1))
    ss_block = k * ((m.mean(axis=-1, keepdims=True) - grand) ** 2).sum(axis=(-2, -1))
    ss_error = ((m - grand) ** 2).sum(axis=(-2, -1)) - ss_cond - ss_block
    return (ss_cond / (k - 1)) / (np.maximum(ss_error, 1e-15) / ((n - 1) * (k - 1)))


def friedman_statistic(m):
    """Friedman chi-square with tie correction for (..., blocks, conditions) arrays."""
    m = np.round(np.asarray(m, dtype=float), 9)
    n, k = m.shape[-2:]
    less = (m[..., :, None] > m[..., None, :]).sum(axis=-1)
    equal = (m[..., :, None] == m[..., None, :]).sum(axis=-1)
    ranks = less + (equal + 1) / 2                     # midranks
    tie_term = (equal ** 2 - 1).sum(axis=(-2, -1))     # = sum over tie groups of c^3 - c
    rank_sums = ranks.sum(axis=-2)
    numerator = 12 * ((rank_sums - n * (k + 1) / 2) ** 2).sum(axis=-1)
    denominator = n * k * (k + 1) - tie_term / (k - 1)
    return np.where(denominator > 0, numerator / np.maximum(denominator, 1e-15), 0.0)


def within_block_permutation(matrix, statistics, draws=100_000, seed=0, chunk=10_000, alpha=0.05):
    """Monte Carlo omnibus test: permute condition labels independently within each block.

    Reports the observed statistic, add-one p-value, and the level-alpha critical
    value from the permutation null distribution.
    """
    m = np.asarray(matrix, dtype=float)
    n, k = m.shape
    rng = np.random.default_rng(seed)
    observed = {name: float(f(m)) for name, f in statistics.items()}
    nulls = {name: [] for name in statistics}
    for start in range(0, draws, chunk):
        size = min(chunk, draws - start)
        order = np.argsort(rng.random((size, n, k)), axis=-1)
        permuted = np.take_along_axis(np.broadcast_to(m, (size, n, k)), order, axis=-1)
        for name, f in statistics.items():
            nulls[name].append(np.asarray(f(permuted), dtype=float))
    out = {}
    for name in statistics:
        null = np.concatenate(nulls[name])
        exceed = int((null >= observed[name] - 1e-9).sum())
        out[name] = dict(statistic=observed[name], p_value=(exceed + 1) / (draws + 1),
                         critical_value=critical_value(null, alpha))
    return out | dict(permutations=draws, blocks=int(n), alpha=alpha)


def block_bootstrap_mean(values, strata, draws=10_000, seed=0):
    """Percentile 95% interval for a mean of block values, resampling within strata."""
    v = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    sims = np.zeros(draws)
    for s in sorted(set(strata)):
        idx = [i for i, x in enumerate(strata) if x == s]
        sims += v[idx][rng.integers(0, len(idx), size=(draws, len(idx)))].sum(axis=1)
    sims /= len(v)
    return np.quantile(sims, [0.025, 0.975]).tolist()


def binom_cdf(x, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(x + 1))


def clopper_pearson_upper(errors, n, alpha=0.05):
    """One-sided (1 - alpha) exact upper confidence bound on an error rate."""
    if errors >= n:
        return 1.0
    if errors == 0:
        return 1 - alpha ** (1 / n)
    lo, hi = errors / n, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if binom_cdf(errors, n, mid) > alpha else (lo, mid)
    return hi
