"""SOL v3 — S6–S10, berpusat pada S8 (uji desain per-uji vs pembanding yang adil).
S6 benchmark realistis: desain IDHS asli (bobot/PSU/strata) atau sintetis setara, ICC HETEROGEN per variabel, p besar.
S7 metrik hilir: validitas himpunan penyesuaian di graf acuan, presisi/recall/FDR sisi.
S8 lima uji CI: naif, Kish, deff-global, sandwich-klaster (CR1), desain per-uji (usulan). Kalibrasi per bin deff.
S9 cross-fitting berulang (median + koreksi varians) dan interval gabungan kandidat IDA.
S10 lihat TEORI_S10.md."""
import itertools, time, tracemalloc
import numpy as np, pandas as pd, networkx as nx
from scipy import stats
from sol_v2 import design_index, lin_var, make_D, _resid, folds, aipw_cf

# ======================= S8: lima uji independensi bersyarat =======================
def _wres(D, x, y, S, w):
    Sm = D['X'][:, S] if S else np.empty((D['n'], 0))
    return _resid(D['X'][:, x], Sm, w), _resid(D['X'][:, y], Sm, w)

def _fisher(r, n_eff, k):
    z = np.arctanh(np.clip(r, -.9999, .9999)) * np.sqrt(max(n_eff - k - 3, 1))
    return 2 * stats.norm.sf(abs(z)), z

def t_naif(D, x, y, S):
    ex, ey = _wres(D, x, y, S, np.ones(D['n'])); return _fisher(np.corrcoef(ex, ey)[0, 1], D['n'], len(S))[0]

def t_kish(D, x, y, S):
    """Bobot survei + n efektif Kish (hanya efek bobot, klaster diabaikan)."""
    w = D['w']; ex, ey = _wres(D, x, y, S, w)
    r = (w * ex * ey).sum() / np.sqrt((w * ex**2).sum() * (w * ey**2).sum())
    return _fisher(r, D['n_kish'], len(S))[0]

def t_deff_global(D, x, y, S):
    """Kish lalu dibagi sqrt(deff global) = rata-rata deff univariat semua variabel (gaya v1 SD-Hybrid)."""
    w = D['w']; ex, ey = _wres(D, x, y, S, w)
    r = (w * ex * ey).sum() / np.sqrt((w * ex**2).sum() * (w * ey**2).sum())
    z = _fisher(r, D['n_kish'], len(S))[1] / np.sqrt(D['deff_global'])
    return 2 * stats.norm.sf(abs(z))

def t_sandwich(D, x, y, S):
    """Wald koefisien x pada regresi WLS y ~ 1 + x + S, SE sandwich CR1 per PSU (tanpa strata), df = C-1."""
    w = D['w']; n = D['n']
    X = np.column_stack([np.ones(n), D['X'][:, x]] + [D['X'][:, s] for s in S]); yv = D['X'][:, y]
    Wx = X * w[:, None]; B = np.linalg.inv(X.T @ Wx); b = B @ (Wx.T @ yv); e = yv - X @ b
    sc = X * (w * e)[:, None]; G = np.zeros((D['idx']['C'], X.shape[1]))
    np.add.at(G, D['idx']['pidx'], sc); C = D['idx']['C']; k = X.shape[1]
    V = B @ (G.T @ G) @ B * C / (C - 1) * (n - 1) / (n - k)
    return 2 * stats.t.sf(abs(b[1] / np.sqrt(V[1, 1])), C - 1)

def t_desain(D, x, y, S):
    """USULAN: kovarians residual berbobot, varians linearisasi Taylor dengan strata+PSU, df = #PSU - #strata."""
    w = D['w']; ex, ey = _wres(D, x, y, S, w); W = w.sum(); th = (w * ex * ey).sum() / W
    se = np.sqrt(lin_var(w * (ex * ey - th) / W, idx=D['idx']))
    return 2 * stats.t.sf(abs(th / se), D['df']) if se > 0 else 1.0

TESTS = {'naif': t_naif, 'kish': t_kish, 'deff_global': t_deff_global, 'sandwich_CR1': t_sandwich, 'desain_usulan': t_desain}

def pair_deff(D, x, y, S):
    """Design effect empiris statistik uji (var desain / var SRS) -> untuk binning heterogenitas."""
    w = D['w']; ex, ey = _wres(D, x, y, S, w); W = w.sum(); z = ex * ey; th = (w * z).sum() / W
    v_d = lin_var(w * (z - th) / W, idx=D['idx']); v_s = np.average((z - th) ** 2, weights=w) / D['n']
    return v_d / v_s if v_s > 0 else np.nan

def prep(D):
    """Tambahkan n Kish dan deff global (rata-rata deff univariat) ke D; dipanggil sekali."""
    w = D['w']; D['n_kish'] = w.sum() ** 2 / (w ** 2).sum(); W = w.sum(); dg = []
    for j in range(D['X'].shape[1]):
        v = D['X'][:, j]; m = np.average(v, weights=w); vs = np.average((v - m) ** 2, weights=w) / D['n']
        if vs > 0: dg.append(lin_var(w * (v - m) / W, idx=D['idx']) / vs)
    D['deff_global'] = float(np.mean(dg)); return D

# ======================= S6: simulasi realistis, ICC heterogen =======================
def design_idhs(path=None, n_strata=67, psu_per=29, m=9, seed=0):
    """Desain nyata dari CSV (kolom bobot, psu/psu_v021, strata/strata_v023) atau sintetis setara IDHS 2017."""
    if path:
        d = pd.read_csv(path, usecols=lambda c: c in ('bobot', 'psu', 'strata', 'psu_v021', 'strata_v023'))
        d = d.rename(columns={'psu_v021': 'psu', 'strata_v023': 'strata'}).dropna()
        return d.bobot.to_numpy(float), d.psu.to_numpy(), d.strata.to_numpy()
    rng = np.random.default_rng(seed); psu = np.repeat(np.arange(n_strata * psu_per), m)
    strata = psu // psu_per; w = np.exp(rng.normal(0, .5, n_strata * psu_per))[psu]
    return w, psu, strata

def simulate_v3(seed, design, p=15, n_tiers=4, dens=0.25, icc=(0.1, 0.8), beta_ty=-0.3, bin_frac=.5):
    """icc=(a,b): ICC tiap variabel ~ U(a,b) (heterogen); icc=float: homogen. T & Y biner di dua tier terakhir."""
    rng = np.random.default_rng(seed); w, psu, strata = design; n = len(w)
    k = p - 2; tiers = sorted(rng.integers(0, n_tiers, k).tolist()) + [n_tiers, n_tiers + 1]; T, Y = p - 2, p - 1
    G = nx.DiGraph(); G.add_nodes_from(range(p))
    for i, j in itertools.combinations(range(p), 2):
        if rng.random() < dens and (i, j) != (T, Y): G.add_edge(i, j)
    G.add_edge(T, Y); B = {e: rng.choice([-1, 1]) * rng.uniform(.2, .6) for e in G.edges}; B[(T, Y)] = beta_ty
    rho = rng.uniform(*icc, p) if isinstance(icc, tuple) else np.full(p, icc)
    _, pidx = np.unique(psu, return_inverse=True); U = rng.normal(size=(pidx.max() + 1, p))[pidx]
    binary = {T, Y} | {i for i in range(k) if rng.random() < bin_frac}
    E, U01 = rng.normal(size=(n, p)), rng.uniform(size=(n, p))
    def node(j, X):
        lp = sum(B[(i, j)] * X[:, i] for i in G.predecessors(j))
        if j in binary:
            return (U01[:, j] < 1 / (1 + np.exp(-(lp - .5 + np.sqrt(rho[j] / (1 - rho[j])) * 1.8 * U[:, j])))).astype(float)
        return lp + np.sqrt(rho[j]) * U[:, j] + np.sqrt(1 - rho[j]) * E[:, j]
    X = np.zeros((n, p))
    for j in range(p): X[:, j] = node(j, X)
    X1, X0 = X.copy(), X.copy(); X1[:, T], X0[:, T] = 1, 0
    true = np.average(node(Y, X1) - node(Y, X0), weights=w)
    return prep(make_D(X, w, psu, strata)), G, tiers, T, Y, true, rho

# ======================= S8 inti: kalibrasi per bin deff =======================
def calibration(D, G, n_stmt=60, max_k=3, seed=0):
    """Separuh pernyataan H0 dijamin benar via Markov lokal (i ⟂ non-keturunan | induk i), separuh acak (umumnya H1)."""
    rng = np.random.default_rng(seed); p = D['X'].shape[1]; rows = []; tries = 0
    while len(rows) < n_stmt and tries < 50 * n_stmt:
        tries += 1
        if len(rows) % 2 == 0:
            i = int(rng.integers(p)); pa = set(G.predecessors(i))
            cand = [v for v in range(p) if v != i and v not in pa and v not in nx.descendants(G, i)]
            if not cand or len(pa) > 5: continue
            j = int(rng.choice(cand)); S = sorted(pa)
        else:
            i, j = (int(v) for v in rng.choice(p, 2, replace=False)); pool = [v for v in range(p) if v not in (i, j)]
            S = sorted(int(v) for v in rng.choice(pool, rng.integers(0, max_k + 1), replace=False))
        ind = nx.is_d_separator(G, {i}, {j}, set(S))
        r = dict(indep=ind, deff=pair_deff(D, i, j, S), k=len(S))
        for nm, f in TESTS.items(): r[nm] = f(D, i, j, S) < .05
        rows.append(r)
    return rows

# ======================= S7 + S9: penemuan, validitas, efek =======================
def discover_v3(D, tiers, test, alpha=.05, max_k=2):
    p = len(tiers); adj = {i: set(range(p)) - {i} for i in range(p)}; sep = {}; ntest = 0
    for k in range(max_k + 1):
        snap = {i: set(a) for i, a in adj.items()}; rem = []
        for i in range(p):
            for j in sorted(snap[i]):
                if j <= i or j not in adj[i]: continue
                for nb in (snap[i] - {j}, snap[j] - {i}):
                    hit = None
                    for S in itertools.combinations(sorted(nb), k):
                        ntest += 1
                        if test(D, i, j, list(S)) > alpha: hit = S; break
                    if hit is not None: rem.append((i, j)); sep[(i, j)] = sep[(j, i)] = set(hit); break
        for i, j in rem: adj[i].discard(j); adj[j].discard(i)
    Gh = nx.DiGraph(); Gh.add_nodes_from(range(p)); Un = set()
    for i in range(p):
        for j in adj[i]:
            if tiers[i] < tiers[j]: Gh.add_edge(i, j)
            elif tiers[i] == tiers[j] and i < j: Un.add((i, j))
    for kk in range(p):
        for i, j in itertools.combinations(sorted(adj[kk]), 2):
            if j in adj[i] or kk in sep.get((i, j), set()): continue
            for a in (i, j):
                e = (min(a, kk), max(a, kk))
                if e in Un: Un.discard(e); Gh.add_edge(a, kk)
    return Gh, Un, ntest

def cand_sets(Gh, Un, T, Y):
    und = sorted(({a, b} - {T}).pop() for a, b in Un if T in (a, b)); par = set(Gh.predecessors(T))
    return [sorted((par | set(c)) - {Y}) for r in range(len(und) + 1) for c in itertools.combinations(und, r)]

def valid_adjust(G, T, Y, Z):
    """S7: Z sah sebagai himpunan backdoor di graf ACUAN?"""
    if set(Z) & nx.descendants(G, T): return False
    Gb = G.copy(); Gb.remove_edges_from(list(G.out_edges(T)))
    return nx.is_d_separator(Gb, {T}, {Y}, set(Z))

def effect_s9(D, T, Y, sets, R=5, K=2, seed=0):
    """S9: cross-fitting berulang R kali; median + varians terkoreksi; interval gabungan kandidat."""
    res = []
    for Z in sets:
        th, se = [], []
        for r in range(R):
            t_, s_ = aipw_cf(D, T, Y, Z, folds(D, K, seed * 100 + r))
            if np.isfinite(t_): th.append(t_); se.append(s_)
        if not th: continue
        th, se = np.array(th), np.array(se); m = np.median(th); s = np.sqrt(np.median(se**2 + (th - m) ** 2))
        res.append((m, m - 1.96 * s, m + 1.96 * s))
    if not res: return np.nan, np.nan, np.nan, np.nan, np.nan
    main = res[0] if len(res) == 1 else min(res, key=lambda r: abs(r[0]))
    return main[0], main[1], main[2], min(r[1] for r in res), max(r[2] for r in res)

def edge_metrics(G, Gh, Un):
    t = {frozenset(e) for e in G.edges}; h = {frozenset(e) for e in Gh.edges} | {frozenset(e) for e in Un}
    tp = len(t & h); fp = len(h - t); fn = len(t - h)
    wrong = sum(1 for a, b in Gh.edges if frozenset((a, b)) in t and not G.has_edge(a, b))
    return dict(SHD=fp + fn + wrong, presisi=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1), FDR=fp / max(tp + fp, 1))

def downstream(D, G, tiers, T, Y, true, tests=None, R=5, seed=0, max_k=2):
    out = []
    for nm in (tests or TESTS):
        tracemalloc.start(); t0 = time.time()
        Gh, Un, nt = discover_v3(D, tiers, TESTS[nm], max_k=max_k); sec = time.time() - t0
        mem = tracemalloc.get_traced_memory()[1] / 2**20; tracemalloc.stop()
        sets = cand_sets(Gh, Un, T, Y); rd, lo, hi, ulo, uhi = effect_s9(D, T, Y, sets, R=R, seed=seed)
        out.append(dict(uji=nm, **edge_metrics(G, Gh, Un), adj_valid=float(np.mean([valid_adjust(G, T, Y, Z) for Z in sets])),
                        err=abs(rd - true), cover=lo <= true <= hi, cover_union=ulo <= true <= uhi,
                        detik=sec, MB=mem, n_uji=nt))
    return out
