"""SOL-DAG v2 — perbaikan S1–S4. Hemat token: setiap fungsi mencetak/mengembalikan ringkasan pendek.
S1 estimasi sadar-query: graf hanya memilih himpunan penyesuaian; efek T->Y SELALU diestimasi (AIPW),
   himpunan efek ala IDA bila orientasi di sekitar T tak pasti. Tidak pernah 'efek = 0 karena tak ada jalur'.
S2 cross-fitting per PSU di dalam strata (K lipatan) menggantikan pemisahan sampel.
S3 satu koreksi saja: uji-t desain per uji (deff lokal otomatis, linearisasi PSU/strata), tanpa penalti n_eff ganda.
   SE efek via fungsi pengaruh + linearisasi desain (tanpa bootstrap -> cepat).
S4 benchmark: DAG acak patuh tier (tidak diturunkan dari DAG pakar), variasi ICC/efek/n, metrik seragam."""
import itertools, time, tracemalloc
import numpy as np, pandas as pd, networkx as nx
from scipy import stats
import statsmodels.api as sm

# ---------------- desain survei ----------------
def design_index(psu, strata):
    """Pra-hitung sekali: kode PSU 0..C-1, strata per PSU, jumlah PSU per strata (hemat waktu per uji)."""
    codes, pidx = np.unique(psu, return_inverse=True)
    p_str = pd.Series(strata).groupby(pidx).first().to_numpy()
    s_codes, sidx = np.unique(p_str, return_inverse=True)
    m = np.bincount(sidx)
    return dict(pidx=pidx, sidx=sidx, m=m, C=len(codes))

def lin_var(z, psu=None, strata=None, idx=None):
    """Varians linearisasi Taylor dari total z (sudah dibagi sum w): sum_h m_h/(m_h-1) sum_c (z_hc - zbar_h)^2."""
    if idx is None: idx = design_index(psu, strata)
    t = np.bincount(idx['pidx'], z, minlength=idx['C'])
    mean = np.bincount(idx['sidx'], t) / idx['m']
    dev2 = np.bincount(idx['sidx'], (t - mean[idx['sidx']]) ** 2)
    ok = idx['m'] > 1
    return float((idx['m'][ok] / (idx['m'][ok] - 1) * dev2[ok]).sum())

def _resid(v, S, w):
    X = np.column_stack([np.ones(len(v))] + [S[:, j] for j in range(S.shape[1])]) if S.size else np.ones((len(v), 1))
    Wx = X * w[:, None]
    b = np.linalg.lstsq(X.T @ Wx, Wx.T @ v, rcond=None)[0]
    return v - X @ b

def ci_test(D, x, y, S, design=True):
    """p-value H0: x ⟂ y | S. design=True: kovarians residual berbobot, SE linearisasi PSU/strata, df desain.
    design=False: uji naif Fisher-z tanpa bobot (pembanding)."""
    Sm = D['X'][:, S] if S else np.empty((D['n'], 0))
    if not design:
        ex, ey = _resid(D['X'][:, x], Sm, np.ones(D['n'])), _resid(D['X'][:, y], Sm, np.ones(D['n']))
        r = np.corrcoef(ex, ey)[0, 1]; z = np.arctanh(np.clip(r, -.9999, .9999)) * np.sqrt(D['n'] - len(S) - 3)
        return 2 * stats.norm.sf(abs(z))
    w = D['w']; ex, ey = _resid(D['X'][:, x], Sm, w), _resid(D['X'][:, y], Sm, w)
    W = w.sum(); th = (w * ex * ey).sum() / W
    se = np.sqrt(lin_var(w * (ex * ey - th) / W, idx=D['idx']))
    return 2 * stats.t.sf(abs(th / se), D['df']) if se > 0 else 1.0

def make_D(X, w, psu, strata):
    """Bungkus data sekali: X (n×p, kolom numerik), bobot, PSU, strata. df desain = #PSU - #strata."""
    idx = design_index(psu, strata)
    return dict(X=np.asarray(X, float), w=np.asarray(w, float), psu=np.asarray(psu), strata=np.asarray(strata),
                n=len(w), idx=idx, df=idx['C'] - len(idx['m']))

# ---------------- penemuan graf (PC-stable + tier) ----------------
def discover(D, tiers, alpha=0.05, max_k=3, design=True):
    p = len(tiers); adj = {i: set(range(p)) - {i} for i in range(p)}; sep = {}
    for k in range(max_k + 1):
        snap = {i: set(a) for i, a in adj.items()}; removed = []
        for i in range(p):
            for j in sorted(snap[i]):
                if j <= i or j not in adj[i]: continue
                for nb in (snap[i] - {j}, snap[j] - {i}):
                    if len(nb) < k: continue
                    hit = next((S for S in itertools.combinations(sorted(nb), k)
                                if ci_test(D, i, j, list(S), design) > alpha), None)
                    if hit is not None:
                        removed.append((i, j)); sep[(i, j)] = sep[(j, i)] = set(hit); break
        for i, j in removed: adj[i].discard(j); adj[j].discard(i)
    G = nx.DiGraph(); G.add_nodes_from(range(p)); U = set()
    for i in range(p):
        for j in adj[i]:
            if tiers[i] < tiers[j]: G.add_edge(i, j)
            elif tiers[i] == tiers[j] and i < j: U.add((i, j))
    for i, k, j in ((i, k, j) for k in range(p) for i in adj[k] for j in adj[k] if i < j and j not in adj[i]):
        for a in (i, j):  # v-structure di dalam tier
            e = (min(a, k), max(a, k))
            if e in U and k not in sep.get((i, j), set()): U.discard(e); G.add_edge(a, k)
    return G, U  # U = sisi tak berarah (di dalam tier)

# ---------------- S1+S2: estimasi sadar-query dengan cross-fitting ----------------
def _logit(y, X, w):
    try:
        return sm.GLM(y, sm.add_constant(X, has_constant='add'), family=sm.families.Binomial(), var_weights=w).fit()
    except Exception:
        return None

def folds(D, K=2, seed=0):
    rng = np.random.default_rng(seed); f = np.zeros(D['n'], int)
    for h in np.unique(D['strata']):
        ps = np.unique(D['psu'][D['strata'] == h]); rng.shuffle(ps)
        for k, c in enumerate(ps): f[D['psu'] == c] = k % K
    return f

def aipw_cf(D, T, Y, Z, f):
    """AIPW berbobot survei, nuisance di-fit di luar lipatan, SE dari fungsi pengaruh + linearisasi desain."""
    X, w = D['X'], D['w']; t, y = X[:, T], X[:, Y]
    mu1, mu0, e = np.zeros(D['n']), np.zeros(D['n']), np.zeros(D['n'])
    Zm = X[:, Z] if Z else np.empty((D['n'], 0))
    for k in np.unique(f):
        tr, te = f != k, f == k
        ps = _logit(t[tr], Zm[tr], w[tr]); om = _logit(y[tr], np.column_stack([Zm[tr], t[tr]]), w[tr])
        if ps is None or om is None: return np.nan, np.nan
        c = lambda A: sm.add_constant(A, has_constant='add')
        e[te] = ps.predict(c(Zm[te])); mu1[te] = om.predict(c(np.column_stack([Zm[te], np.ones(te.sum())])))
        mu0[te] = om.predict(c(np.column_stack([Zm[te], np.zeros(te.sum())])))
    e = np.clip(e, .01, .99); W = w.sum()
    phi = mu1 - mu0 + t * (y - mu1) / e - (1 - t) * (y - mu0) / (1 - e); th = (w * phi).sum() / W
    return th, np.sqrt(lin_var(w * (phi - th) / W, idx=D['idx']))

def query_effect(D, T, Y, tiers, alpha=0.05, K=2, design=True, rule='v2', seed=0):
    """Graf dipelajari di luar lipatan; himpunan induk T yang mungkin (IDA-lokal) -> efek per kandidat."""
    f = folds(D, K, seed); cands = []
    G, U = discover(D, tiers, alpha, design=design)  # graf untuk pelaporan/SHD
    if rule == 'v1' and not nx.has_path(G, T, Y):     # aturan lama (pembanding ablasi)
        return dict(rd=0.0, lo=0.0, hi=0.0, n_set=1, G=G, U=U)
    und = sorted(({a, b} - {T}).pop() for a, b in U if T in (a, b))
    parents = sorted(G.predecessors(T))
    for r in range(len(und) + 1):
        for extra in itertools.combinations(und, r):
            Z = sorted(set(parents) | set(extra) - {Y})
            th, se = aipw_cf(D, T, Y, Z, f)
            if np.isfinite(th): cands.append((th, se))
    th = np.array([c[0] for c in cands]); se = np.array([c[1] for c in cands])
    i = np.argmin(np.abs(th)) if len(th) > 1 else 0   # konservatif ala IDA: |efek| terkecil
    return dict(rd=th[i], lo=th[i] - 1.96 * se[i], hi=th[i] + 1.96 * se[i], n_set=len(th), G=G, U=U,
                rd_set=(th.min(), th.max()))

# ---------------- S4: benchmark semi-sintetik ----------------
def simulate(seed, sizes=(3, 3, 3), n_strata=10, psu_per=10, m=20, icc=0.2, dens=0.35, beta_ty=-0.6):
    rng = np.random.default_rng(seed)
    p = sum(sizes) + 2; tiers = sum(([t] * s for t, s in enumerate(sizes)), []) + [len(sizes), len(sizes) + 1]
    T, Y = p - 2, p - 1; order = list(range(p)); G = nx.DiGraph(); G.add_nodes_from(order)
    for i, j in itertools.combinations(order, 2):
        if rng.random() < dens and (i, j) != (T, Y): G.add_edge(i, j)
    G.add_edge(T, Y)
    B = {e: rng.choice([-1, 1]) * rng.uniform(.3, .8) for e in G.edges}; B[(T, Y)] = beta_ty
    strata = np.repeat(np.arange(n_strata), psu_per * m); psu = np.repeat(np.arange(n_strata * psu_per), m)
    n = len(psu); u_psu = rng.normal(0, 1, (n_strata * psu_per, p))[psu]
    binary = {T, Y} | {i for i in range(p - 2) if rng.random() < .5}
    U01 = rng.uniform(size=(n, p)); E = rng.normal(size=(n, p)); X = np.zeros((n, p))
    def node(j, X):
        lp = sum(B[(i, j)] * X[:, i] for i in G.predecessors(j)) + np.sqrt(icc) * u_psu[:, j]
        return (U01[:, j] < 1 / (1 + np.exp(-(lp - .5)))).astype(float) if j in binary else lp + np.sqrt(1 - icc) * E[:, j]
    for j in order: X[:, j] = node(j, X)
    w = np.exp(rng.normal(0, .5, n_strata * psu_per))[psu]
    Y1, Y0 = X.copy(), X.copy(); Y1[:, T], Y0[:, T] = 1, 0
    true = np.average(node(Y, Y1) - node(Y, Y0), weights=w)
    D = make_D(X, w, psu, strata)
    return D, G, tiers, T, Y, true

def shd(Gt, G, U):
    sk_t = {frozenset(e) for e in Gt.edges}; sk = {frozenset(e) for e in G.edges} | {frozenset(e) for e in U}
    wrong = sum(1 for a, b in G.edges if frozenset((a, b)) in sk_t and not Gt.has_edge(a, b))
    return len(sk_t ^ sk) + wrong

def ci_calibration(D, Gt, reps=20, seed=0):
    """Galat tipe I & daya uji pada pernyataan independensi/dependensi yang BENAR menurut graf acuan."""
    rng = np.random.default_rng(seed); p = D['X'].shape[1]; out = {'naif': [[], []], 'desain': [[], []]}
    for _ in range(reps * 5):
        i, j = rng.choice(p, 2, replace=False); S = sorted(set(Gt.predecessors(i)) - {j})
        indep = nx.is_d_separator(Gt, {i}, {j}, set(S)); key = 0 if indep else 1
        for nm, des in (('naif', False), ('desain', True)):
            if len(out[nm][key]) < reps: out[nm][key].append(ci_test(D, i, j, S, des) < .05)
    return {nm: (np.mean(v[0]), np.mean(v[1])) for nm, v in out.items()}

def benchmark(reps=50, variants=(('v2 desain', True, 'v2'), ('v2 naif', False, 'v2'), ('v1 aturan lama', True, 'v1')),
              **sim):
    rows, cal = [], []
    for r in range(reps):
        D, Gt, tiers, T, Y, true = simulate(r, **sim)
        cal.append(ci_calibration(D, Gt, seed=r))
        for nm, des, rule in variants:
            tracemalloc.start(); t0 = time.time()
            res = query_effect(D, T, Y, tiers, design=des, rule=rule, seed=r)
            sec = time.time() - t0; mem = tracemalloc.get_traced_memory()[1] / 2**20; tracemalloc.stop()
            rows.append(dict(varian=nm, rep=r, shd=shd(Gt, res['G'], res['U']), err=abs(res['rd'] - true),
                             cover=res['lo'] <= true <= res['hi'], nol=res['rd'] == 0, detik=sec, mb=mem))
    df = pd.DataFrame(rows)
    tab = df.groupby('varian').agg(SHD=('shd', 'mean'), RMSE=('err', lambda e: np.sqrt((e**2).mean())),
                                   cakupan=('cover', 'mean'), efek_nol=('nol', 'mean'), detik=('detik', 'mean'),
                                   MB=('mb', 'mean'), SHD_sd=('shd', 'std'))
    t1 = {k: np.mean([c[k][0] for c in cal]) for k in ('naif', 'desain')}
    pw = {k: np.mean([c[k][1] for c in cal]) for k in ('naif', 'desain')}
    return tab.round(4), t1, pw, df

def ringkas(tab, t1, pw, sim):
    """Ringkasan ≤10 baris — tempel ini saja saat berdiskusi."""
    L = [f"BENCH {sim}"]
    for v, r in tab.iterrows():
        L.append(f"{v}: SHD {r.SHD:.1f}±{r.SHD_sd:.1f} RMSE {r.RMSE:.4f} cakupan {r.cakupan:.0%} "
                 f"efek0 {r.efek_nol:.0%} {r.detik:.2f}s {r.MB:.1f}MB")
    L.append(f"CI-test tipe I naif {t1['naif']:.1%} desain {t1['desain']:.1%} | daya naif {pw['naif']:.1%} desain {pw['desain']:.1%}")
    return "\n".join(L)
