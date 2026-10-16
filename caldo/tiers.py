"""Tiers: optimal 1-D clustering (Jenks natural breaks) of rest-of-season value."""
import numpy as np


def jenks(values, k):
    """Exact 1-D k-means by dynamic programming. Returns a tier label (1 = best) per value."""
    order = np.argsort(-values)
    x = values[order]
    n = len(x)
    k = max(1, min(k, n))
    cs, cs2 = np.concatenate([[0], np.cumsum(x)]), np.concatenate([[0], np.cumsum(x ** 2)])

    def sse(i, j):  # cost of x[i:j]
        s, s2, m = cs[j] - cs[i], cs2[j] - cs2[i], j - i
        return s2 - s * s / m

    cost = np.full((k + 1, n + 1), np.inf)
    back = np.zeros((k + 1, n + 1), dtype=int)
    cost[0, 0] = 0
    for c in range(1, k + 1):
        for j in range(c, n + 1):
            best, arg = np.inf, c - 1
            for i in range(c - 1, j):
                v = cost[c - 1, i] + sse(i, j)
                if v < best:
                    best, arg = v, i
            cost[c, j], back[c, j] = best, arg
    labels = np.empty(n, dtype=int)
    j = n
    for c in range(k, 0, -1):
        i = back[c, j]
        labels[i:j] = c
        j = i
    out = np.empty(n, dtype=int)
    out[order] = labels
    return out


def assign_tiers(values, gvf_target=0.96, max_k=12):
    """Smallest number of tiers whose goodness-of-variance-fit reaches the target."""
    values = np.asarray(values, float)
    total = ((values - values.mean()) ** 2).sum()
    if len(values) < 3 or total == 0:
        return np.ones(len(values), dtype=int)
    for k in range(2, max_k + 1):
        lab = jenks(values, k)
        within = sum(((values[lab == t] - values[lab == t].mean()) ** 2).sum() for t in np.unique(lab))
        if 1 - within / total >= gvf_target:
            return lab
    return lab
