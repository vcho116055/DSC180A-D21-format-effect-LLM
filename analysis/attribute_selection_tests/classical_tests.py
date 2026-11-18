"""Classical (distribution-based) tests, numpy/math only (no scipy).

Repeated-measures ANOVA (F distribution), Friedman (chi-square approximation),
and paired t-tests, with p-values and alpha-level critical values. Used as a
comparison to the permutation tests, which do not assume normality or sphericity.
"""
import math

import numpy as np


# ---------------------------------------------------------------- special functions
def _betacf(a, b, x, iterations=500, eps=1e-14):
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def gammaincc(s, x, iterations=1000, eps=1e-14):
    """Regularized upper incomplete gamma Q(s, x)."""
    if x <= 0:
        return 1.0
    if x < s + 1:  # series for P, then Q = 1 - P
        term = total = 1 / s
        for n in range(1, iterations):
            term *= x / (s + n)
            total += term
            if abs(term) < abs(total) * eps:
                break
        return 1 - total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    tiny = 1e-300  # continued fraction for Q
    b = x + 1 - s
    c, d = 1 / tiny, 1 / b
    h = d
    for i in range(1, iterations):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > tiny else tiny)
        c = b + an / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < eps:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


def f_sf(f, d1, d2):
    return 1.0 if f <= 0 else betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * f))


def chi2_sf(x, df):
    return gammaincc(df / 2, x / 2)


def t_two_sided_p(t, df):
    return betainc(df / 2, 0.5, df / (df + t * t))


def _invert(sf, alpha, hi=1e4):
    """Critical value c with sf(c) = alpha, by bisection (sf decreasing)."""
    lo = 0.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if sf(mid) > alpha else (lo, mid)
    return hi


# --------------------------------------------------------------------------- tests
def rm_anova(matrix, alpha=0.05):
    """Classical one-factor repeated-measures ANOVA (blocks x conditions), sphericity assumed."""
    m = np.asarray(matrix, dtype=float)
    n, k = m.shape
    grand = m.mean()
    ss_cond = n * ((m.mean(axis=0) - grand) ** 2).sum()
    ss_block = k * ((m.mean(axis=1) - grand) ** 2).sum()
    ss_error = ((m - grand) ** 2).sum() - ss_cond - ss_block
    df1, df2 = k - 1, (n - 1) * (k - 1)
    crit = _invert(lambda f: f_sf(f, df1, df2), alpha)
    if ss_error <= 1e-12:
        return dict(F=None, df1=df1, df2=df2, p_value=None, critical_value=crit,
                    note='no within-table variation; F undefined')
    f = (ss_cond / df1) / (ss_error / df2)
    return dict(F=float(f), df1=df1, df2=df2, p_value=f_sf(f, df1, df2), critical_value=crit)


def friedman_classical(statistic, k, alpha=0.05):
    """Chi-square approximation for a Friedman statistic with k conditions."""
    df = k - 1
    return dict(chi2=float(statistic), df=df, p_value=chi2_sf(statistic, df),
                critical_value=_invert(lambda x: chi2_sf(x, df), alpha))


def paired_t(differences, alpha=0.05):
    """Classical two-sided paired t-test of mean difference = 0."""
    d = np.asarray(differences, dtype=float)
    n = d.size
    df = n - 1
    crit = _invert(lambda t: t_two_sided_p(t, df), alpha, hi=1e3)
    sd = d.std(ddof=1)
    if sd <= 1e-12:
        return dict(t=None, df=df, p_value=1.0 if abs(d.mean()) < 1e-12 else 0.0,
                    critical_value=crit, note='no variation in differences')
    t = d.mean() / (sd / math.sqrt(n))
    return dict(t=float(t), df=df, p_value=t_two_sided_p(abs(t), df), critical_value=crit)
