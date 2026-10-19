"""MENU 4: BASELINE KAUSAL GRAFIS (pembanding SOL-DAG), sesuai dokumen Tahap 2.
  B1  DAG pakar + SEM: analisis jalur ML berbobot survei, kecocokan, dekomposisi efek, probit untuk Y
  B2  PC-stable + v-structure + tier + Meek R1-R4 -> CPDAG -> IDA (lokal)
  B3  Bayesian Network berbasis skor (BIC/BDeu/Gauss) + Hill-Climbing ber-tier -> inferensi do
Ketiganya memakai variabel (node teramati DAG pakar), data (kasus lengkap), tier, dan langkah
estimasi yang sama: adjustment set backdoor -> g-komputasi berbobot survei + bootstrap PSU.
Penemuan graf B2/B3 sengaja TIDAK memakai bobot/desain survei (sesuai rumusan baseline)."""
import itertools
import time
import tracemalloc
import warnings
import numpy as np
import pandas as pd
import networkx as nx
import statsmodels.api as sm
from scipy import stats
from scipy.special import gammaln
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C
from causal import build_dag, adjustment, _fit

warnings.filterwarnings("ignore")
P = C.BASELINE


# ================================================================== bersama
def siapkan(df, spec):
    """V = node teramati DAG pakar (urut tier), data = kasus lengkap pada V."""
    G = build_dag(spec)
    V = [v for v in G if v not in spec['laten']]
    tanpa = [v for v in V if v not in C.TIER]
    if tanpa:
        raise KeyError(f"Variabel belum punya tier di config.TIER: {tanpa}")
    V = sorted(V, key=lambda v: (C.TIER[v], v))
    miss = [v for v in V if v not in df]
    if miss:
        raise KeyError(f"Variabel tidak ada di dataset: {miss}")
    d = df.query(spec['filter']) if spec['filter'] else df
    return d.dropna(subset=V).reset_index(drop=True), V, G


def gkomp(d, T, Y, Z):
    """psi_t = sum_i w_i P(Y=1 | T=t, Z_i) / sum_i w_i  (regresi logistik berbobot)."""
    X = d[Z].astype(float)
    X = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
    w = d.bobot.values
    m = _fit(d[Y].values, X.assign(_T=d[T].values), w)
    return [np.average(m.predict(sm.add_constant(X.assign(_T=t), has_constant='add')), weights=w)
            for t in (1, 0)]


def boot(d, fn, B, rng):
    """Bootstrap PSU di dalam strata; fn(data) -> dict."""
    psus = {s: g.psu.unique() for s, g in d.groupby('strata')}
    idx = {k: g.index.values for k, g in d.groupby(['strata', 'psu'])}
    res = []
    for _ in range(B):
        take = np.concatenate([idx[(s, p)] for s, ps in psus.items() for p in rng.choice(ps, len(ps))])
        try:
            res.append(fn(d.loc[take].reset_index(drop=True)))
        except Exception:
            pass
    return pd.DataFrame(res)


def efek(d, T, Y, Z, B, rng):
    def f(x):
        p1, p0 = gkomp(x, T, Y, Z)
        return {'p1': p1, 'p0': p0, 'RD': p1 - p0, 'RR': p1 / p0}
    r = f(d)
    if B:
        bs = boot(d, f, B, rng)
        for k in ('RD', 'RR'):
            r[f'{k}_lo'], r[f'{k}_hi'] = bs[k].quantile(.025), bs[k].quantile(.975)
    return r


def efek_graf(G, d, T, Y, B, rng, laten=()):
    """Langkah estimasi bersama pada satu DAG: Z backdoor -> g-komputasi."""
    Z, ok, med = adjustment(G, T, Y, list(laten))
    if Y not in nx.descendants(G, T):
        m = np.average(d[Y], weights=d.bobot)
        return (dict(p1=m, p0=m, RD=0.0, RR=1.0, RD_lo=0.0, RD_hi=0.0, RR_lo=1.0, RR_hi=1.0), Z, ok,
                "tidak ada jalur berarah T->Y di graf: efek = 0")
    return efek(d, T, Y, Z, B, rng), Z, ok, ""


def banding(arah, takarah, Ge):
    """Selisih struktur terhadap DAG pakar (bukan kebenaran, hanya rujukan)."""
    pakar = set(Ge.edges())
    skp = {frozenset(e) for e in pakar}
    ske = {frozenset(e) for e in arah} | {frozenset(e) for e in takarah}
    tp, fp, fn = len(skp & ske), len(ske - skp), len(skp - ske)
    salah = (sum(1 for a, b in arah if frozenset((a, b)) in skp and (a, b) not in pakar)
             + sum(1 for e in takarah if frozenset(e) in skp))
    return dict(sisi=len(ske), sisi_sama_pakar=tp, sisi_tambahan=fp, sisi_hilang=fn, arah_beda=salah,
                SHD=fp + fn + salah)


def gambar(V, arah, takarah, spec, judul, path):
    """Tata letak per tier (kiri -> kanan). Garis putus-putus = sisi tak berarah."""
    G = nx.DiGraph(); G.add_nodes_from(V)
    pos = {}
    for t in sorted({C.TIER[v] for v in V}):
        vs = [v for v in V if C.TIER[v] == t]
        for k, v in enumerate(vs):
            pos[v] = (t, (len(vs) - 1) / 2 - k)
    col = ['#d62728' if v == spec['T'] else '#2ca02c' if v == spec['Y'] else '#1f77b4' for v in V]
    plt.figure(figsize=(14, 8))
    nx.draw_networkx_nodes(G, pos, node_color=col, node_size=450)
    nx.draw_networkx_labels(G, {k: (x, y - 0.22) for k, (x, y) in pos.items()}, font_size=7)
    nx.draw_networkx_edges(G, pos, edgelist=list(arah), arrowsize=12, edge_color='#666666', node_size=450,
                           connectionstyle='arc3,rad=0.08')
    nx.draw_networkx_edges(G, pos, edgelist=list(takarah), arrows=False, style='dashed', edge_color='#ff7f0e',
                           width=1.6)
    top = max(y for _, y in pos.values()) + 0.8
    for t in sorted({C.TIER[v] for v in V}):
        plt.text(t, top, f"tier {t}\n{C.TIER_NAMA[t]}", ha='center', fontsize=8, color='#555555')
    plt.title(judul + "   (Merah=treatment, Hijau=outcome, oranye putus-putus=tak berarah)", fontsize=10)
    plt.axis('off'); plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def mulai_ukur():
    tracemalloc.start()
    return time.time()


def selesai_ukur(t0):
    """(detik, memori puncak MB) tahap penemuan graf, tanpa bootstrap estimasi."""
    puncak = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    return time.time() - t0, puncak


def info(path, **kv):
    pd.Series(kv, name='nilai').rename_axis('kunci').to_csv(path)


def baris(kode, metode, r, **kw):
    return dict(kode=kode, metode=metode, RD=r['RD'], RD_lo=r.get('RD_lo', np.nan), RD_hi=r.get('RD_hi', np.nan),
                RR=r['RR'], RR_lo=r.get('RR_lo', np.nan), RR_hi=r.get('RR_hi', np.nan), **kw)


# ================================================================== B1 SEM
def wcov(x, V):
    """S_w = sum w (v - v_w)(v - v_w)' / sum w."""
    X = x[V].astype(float).values; w = x.bobot.values
    Xc = X - w @ X / w.sum()
    return (Xc * w[:, None]).T @ Xc / w.sum()


def sem(S, V, Ge, exo_bebas):
    """ML analisis jalur rekursif: B (B[k,j] = beta_kj), Omega, Sigma(theta) = (I-B')^-1 Omega (I-B')^-T.
    Untuk model rekursif dengan galat endogen saling bebas, ML = OLS per persamaan pada S."""
    p = len(V); ix = {v: i for i, v in enumerate(V)}
    B, Om = np.zeros((p, p)), np.zeros((p, p))
    for v in V:
        j = ix[v]; pa = [ix[u] for u in Ge.predecessors(v)]
        if pa:
            b = np.linalg.solve(S[np.ix_(pa, pa)], S[pa, j])
            B[pa, j] = b; Om[j, j] = S[j, j] - S[j, pa] @ b
        else:
            Om[j, j] = S[j, j]
    akar = [ix[v] for v in V if Ge.in_degree(v) == 0]
    if exo_bebas:
        Om[np.ix_(akar, akar)] = S[np.ix_(akar, akar)]
    Ai = np.linalg.inv(np.eye(p) - B.T)
    return B, Om, Ai @ Om @ Ai.T, len(akar)


def kecocokan(S, Sig, n_eff, n_par):
    p = len(S)
    ld = lambda M: np.linalg.slogdet(M)[1]
    F = ld(Sig) + np.trace(S @ np.linalg.inv(Sig)) - ld(S) - p
    chi2, df = (n_eff - 1) * F, p * (p + 1) / 2 - n_par
    chi0, df0 = (n_eff - 1) * (np.log(np.diag(S)).sum() - ld(S)), p * (p - 1) / 2
    sd = np.sqrt(np.diag(S)); R = (S - Sig) / np.outer(sd, sd)
    return dict(chi2=chi2, df=df, p_chi2=stats.chi2.sf(chi2, df) if df > 0 else np.nan,
                RMSEA=np.sqrt(max((chi2 - df) / (df * (n_eff - 1)), 0)) if df > 0 else 0.0,
                CFI=1 - max(chi2 - df, 0) / max(chi0 - df0, chi2 - df, 1e-12),
                SRMR=np.sqrt(np.mean(R[np.tril_indices(p)] ** 2)), n_eff=n_eff)


def fit_graf(d, V, Ge):
    """Kecocokan SEM linear berbobot survei untuk sembarang DAG pada V (dipakai B1 & rangkuman)."""
    S = wcov(d, V)
    _, _, Sig, n_akar = sem(S, V, Ge, P['sem_exo_bebas'])
    n_par = Ge.number_of_edges() + len(V) + (n_akar * (n_akar - 1) // 2 if P['sem_exo_bebas'] else 0)
    f = kecocokan(S, Sig, len(d) / P['deff'], n_par)
    f['BIC_SEM'] = f['chi2'] - f['df'] * np.log(f['n_eff'])     # BIC relatif thd model jenuh
    return f


def b1_inti(x, V, Ge, T, Y):
    """Satu kali estimasi B1 -> dict skalar (dipakai juga di tiap replikasi bootstrap)."""
    ix = {v: i for i, v in enumerate(V)}
    S = wcov(x, V)
    B, _, Sig, _ = sem(S, V, Ge, P['sem_exo_bebas'])
    Tt = np.linalg.inv(np.eye(len(V)) - B) - np.eye(len(V))       # efek total semua pasangan
    r = {f"beta:{a}->{b}": B[ix[a], ix[b]] for a, b in Ge.edges()}
    t, y = ix[T], ix[Y]
    r['total'], r['langsung'] = Tt[t, y], B[t, y]
    r['tak_langsung'] = r['total'] - r['langsung']
    for pth in nx.all_simple_paths(Ge, T, Y):
        r['jalur:' + ' -> '.join(pth)] = np.prod([B[ix[a], ix[b]] for a, b in zip(pth, pth[1:])])
    # probit untuk Y + g-komputasi skala probabilitas; mediator digeser lewat efek total linear T -> M
    pa = list(Ge.predecessors(Y)); w = x.bobot.values
    X = x[pa].astype(float)
    m = sm.GLM(x[Y].values, sm.add_constant(X, has_constant='add'),
               family=sm.families.Binomial(link=sm.families.links.Probit()), var_weights=w).fit()
    de = nx.descendants(Ge, T)

    def psi(tv, ikut_mediator):
        Xt = X.copy()
        for v in pa:
            if v == T:
                Xt[v] = tv
            elif v in de and ikut_mediator:
                Xt[v] = X[v] + Tt[t, ix[v]] * (tv - x[T].values)
        return np.average(m.predict(sm.add_constant(Xt, has_constant='add')), weights=w)
    p1, p0 = psi(1, True), psi(0, True)
    r |= {'probit_p1': p1, 'probit_p0': p0, 'probit_RD': p1 - p0, 'probit_RR': p1 / p0,
          'probit_RD_langsung': psi(1, False) - psi(0, False)}
    r['probit_RD_tak_langsung'] = r['probit_RD'] - r['probit_RD_langsung']
    return r, S, B, Sig


def b1(d, V, G, spec, out, B, rng):
    t0 = time.time(); T, Y = spec['T'], spec['Y']
    Ge = G.subgraph(V).copy()
    tu = mulai_ukur()
    fit = fit_graf(d, V, Ge)
    dp, mem = selesai_ukur(tu)
    r, S, Bm, Sig = b1_inti(d, V, Ge, T, Y)
    bs = boot(d, lambda x: b1_inti(x, V, Ge, T, Y)[0], B, rng) if B else pd.DataFrame()
    ci = lambda k: (bs[k].std(), bs[k].quantile(.025), bs[k].quantile(.975)) if k in bs else (np.nan,) * 3

    sd = np.sqrt(np.diag(S)); ix = {v: i for i, v in enumerate(V)}
    koef = pd.DataFrame([dict(dari=a, ke=b, beta=r[f"beta:{a}->{b}"],
                              beta_std=r[f"beta:{a}->{b}"] * sd[ix[a]] / sd[ix[b]],
                              **dict(zip(('se_boot', 'ci_bawah', 'ci_atas'), ci(f"beta:{a}->{b}"))))
                         for a, b in Ge.edges()])
    koef.to_csv(out / "b1_koefisien.csv", index=False)
    kunci = (['total', 'langsung', 'tak_langsung'] + [k for k in r if k.startswith('jalur:')]
             + ['probit_RD', 'probit_RD_langsung', 'probit_RD_tak_langsung', 'probit_RR'])
    dek = pd.DataFrame([dict(komponen=k.replace('jalur:', 'jalur: '), estimasi=r[k],
                             **dict(zip(('se_boot', 'ci_bawah', 'ci_atas'), ci(k)))) for k in kunci])
    dek.to_csv(out / "b1_dekomposisi.csv", index=False)
    pd.Series(fit).rename_axis('ukuran').rename('nilai').to_csv(out / "b1_kecocokan.csv")

    # langkah estimasi bersama pada DAG pakar (laten diperlakukan sebagai laten)
    rb, Z, ok, cat = efek_graf(G, d, T, Y, B, rng, spec['laten'])
    gambar(V, Ge.edges(), [], spec, f"B1 DAG pakar: {T} -> {Y}", out / "b1_graf.png")
    dt = time.time() - t0
    info(out / "b1_info.csv", n=len(d), sisi=Ge.number_of_edges(), adjustment=', '.join(Z) or '-',
         teridentifikasi=ok, laten=', '.join(spec['laten']) or '-', catatan=cat or '-', detik=round(dt, 1))
    catat = f"|Z|={len(Z)}" + ("" if ok else "; TIDAK teridentifikasi (laten)") + (f"; {cat}" if cat else "")
    rows = [baris('B1', 'B1 DAG pakar: backdoor g-komputasi', rb, sisi=Ge.number_of_edges(), SHD=0,
                  detik=dt, detik_penemuan=dp, memori_MB=mem, catatan=catat),
            baris('B1p', 'B1 SEM probit: efek total (g-komputasi)',
                  dict(RD=r['probit_RD'], RR=r['probit_RR'], RD_lo=ci('probit_RD')[1], RD_hi=ci('probit_RD')[2],
                       RR_lo=ci('probit_RR')[1], RR_hi=ci('probit_RR')[2]),
                  sisi=Ge.number_of_edges(), SHD=0, detik=dt,
                  catatan=f"langsung={r['probit_RD_langsung']:+.4f}, tak langsung={r['probit_RD_tak_langsung']:+.4f}")]
    lines = [f"B1[{spec['T']}->{spec['Y']}] RMSEA={fit['RMSEA']:.3f} CFI={fit['CFI']:.3f} SRMR={fit['SRMR']:.3f}"
             f" chi2={fit['chi2']:.1f} df={fit['df']:.0f} (n_eff={fit['n_eff']:.0f})",
             f"B1 linear: total={r['total']:+.4f} langsung={r['langsung']:+.4f} tak langsung={r['tak_langsung']:+.4f}"
             f" | probit RD={r['probit_RD']:+.4f} | backdoor g-komp RD={rb['RD']:+.4f}"
             f" [{rb.get('RD_lo', np.nan):+.4f},{rb.get('RD_hi', np.nan):+.4f}]"]
    return rows, lines


# ================================================================== B2 PC + tier + IDA
class UjiCI:
    """Uji independensi bersyarat: Fisher z (korelasi parsial) atau G2 (semua variabel diskret)."""

    def __init__(self, d, V, jenis):
        X = d[V].astype(float).values
        self.n, self.jenis, self.jumlah = len(X), jenis, 0
        self.R = np.corrcoef(X, rowvar=False)
        self.kode, self.k = {}, {}
        for i in range(len(V)):
            u, c = np.unique(X[:, i], return_inverse=True)
            if len(u) <= P['maks_kategori']:
                self.kode[i], self.k[i] = c, len(u)

    def p(self, i, j, S):
        self.jumlah += 1
        if self.jenis == "campuran" and all(v in self.kode for v in (i, j, *S)):
            return self.g2(i, j, S)
        idx = [i, j, *S]
        Q = np.linalg.pinv(self.R[np.ix_(idx, idx)])
        r = np.clip(-Q[0, 1] / np.sqrt(Q[0, 0] * Q[1, 1]), -0.999999, 0.999999)
        z = 0.5 * np.sqrt(self.n - len(S) - 3) * np.log((1 + r) / (1 - r))
        return 2 * stats.norm.sf(abs(z))

    def g2(self, i, j, S):
        ki, kj = self.k[i], self.k[j]
        s = np.zeros(self.n, dtype=np.int64)
        for v in S:
            s = s * self.k[v] + self.kode[v]
        s = np.unique(s, return_inverse=True)[1]; ns = s.max() + 1
        O = np.bincount((s * ki + self.kode[i]) * kj + self.kode[j], minlength=ns * ki * kj)
        O = O.reshape(ns, ki, kj).astype(float)
        E = O.sum(2, keepdims=True) * O.sum(1, keepdims=True) / O.sum((1, 2), keepdims=True)
        m = O > 0
        g = 2 * (O[m] * np.log(O[m] / E[m])).sum()
        return stats.chi2.sf(g, max((ki - 1) * (kj - 1) * ns, 1))   # df: hanya strata S yang terisi


def pc_skeleton(ci, p, alpha, maks):
    """PC-stable: ketetanggaan dibekukan di awal setiap level l."""
    A = ~np.eye(p, dtype=bool); sep = {}
    for l in range(maks + 1):
        adj = [set(np.flatnonzero(A[i])) for i in range(p)]
        if all(len(a) - 1 < l for a in adj):
            break
        for i, j in itertools.permutations(range(p), 2):
            if not A[i, j] or len(adj[i] - {j}) < l:
                continue
            for S in itertools.combinations(sorted(adj[i] - {j}), l):
                if ci.p(i, j, S) > alpha:
                    A[i, j] = A[j, i] = False; sep[i, j] = sep[j, i] = set(S)
                    break
    return A, sep


def orientasi(A, sep, tier):
    """A[i,j] & A[j,i] = i - j; A[i,j] & ~A[j,i] = i -> j."""
    A = A.copy(); p = len(A); R = range(p)
    adj = lambda a, b: A[a, b] or A[b, a]
    und = lambda a, b: A[a, b] and A[b, a]
    arah = lambda a, b: A[a, b] and not A[b, a]
    # tahap 2: v-structure (dilewati bila melawan tier atau bertabrakan dengan orientasi sebelumnya)
    for i, j in itertools.combinations(R, 2):
        if adj(i, j):
            continue
        for k in R:
            if (k not in (i, j) and adj(i, k) and adj(j, k) and k not in sep.get((i, j), set())
                    and tier[k] >= max(tier[i], tier[j]) and A[i, k] and A[j, k]):
                A[k, i] = A[k, j] = False
    # tahap 3a: pengetahuan tier
    for i, j in itertools.permutations(R, 2):
        if tier[i] < tier[j] and A[i, j]:
            A[j, i] = False
    # tahap 3b: aturan Meek R1-R4 hingga tidak ada perubahan
    ubah = True
    while ubah:
        ubah = False
        for a, b in itertools.permutations(R, 2):
            if not und(a, b):
                continue
            if (any(arah(c, a) and not adj(c, b) for c in R if c != b)                                   # R1
                    or any(arah(a, c) and arah(c, b) for c in R)                                          # R2
                    or any(und(a, c) and und(a, e) and arah(c, b) and arah(e, b) and not adj(c, e)
                           for c, e in itertools.combinations(R, 2))                                      # R3
                    or any(und(a, e) and arah(e, c) and arah(c, b) and adj(a, c) and not adj(e, b)
                           for e, c in itertools.permutations(R, 2))):                                    # R4
                A[b, a] = False; ubah = True
    return A


def ida_himpunan(A, t):
    """Himpunan induk T yang konsisten dengan CPDAG (tanpa v-structure baru di T)."""
    p = len(A)
    pa = [k for k in range(p) if A[k, t] and not A[t, k]]
    sib = [k for k in range(p) if A[k, t] and A[t, k]]
    adj = lambda a, b: A[a, b] or A[b, a]
    H = [pa + list(S) for r in range(len(sib) + 1) for S in itertools.combinations(sib, r)
         if all(adj(a, b) for a, b in itertools.combinations(S, 2)) and all(adj(s, q) for s in S for q in pa)]
    return pa, sib, H


def b2(d, V, G, spec, out, B, rng):
    t0 = time.time(); T, Y = spec['T'], spec['Y']; ix = {v: i for i, v in enumerate(V)}
    tier = np.array([C.TIER[v] for v in V])
    tu = mulai_ukur()
    ci = UjiCI(d, V, P['uji'])
    A, sep = pc_skeleton(ci, len(V), P['alpha'], P['maks_kondisi'])
    A = orientasi(A, sep, tier)
    dp, mem = selesai_ukur(tu)
    arah = [(V[i], V[j]) for i, j in itertools.permutations(range(len(V)), 2) if A[i, j] and not A[j, i]]
    takarah = [(V[i], V[j]) for i, j in itertools.combinations(range(len(V)), 2) if A[i, j] and A[j, i]]
    pd.DataFrame([dict(dari=a, ke=b, jenis='->') for a, b in arah]
                 + [dict(dari=a, ke=b, jenis='-') for a, b in takarah]).to_csv(out / "b2_cpdag.csv", index=False)

    pa, sib, H = ida_himpunan(A, ix[T])
    ida = []
    for h in H:
        Z = [V[k] for k in h]
        r = (dict(p1=np.nan, p0=np.nan, RD=0.0, RR=1.0, RD_lo=0.0, RD_hi=0.0, RR_lo=1.0, RR_hi=1.0)
             if Y in Z else efek(d, T, Y, Z, B, rng))
        ida.append(dict(himpunan_induk=', '.join(Z) or '(kosong)', n_induk=len(Z), **r))
    ida = pd.DataFrame(ida)
    ida.to_csv(out / "b2_ida.csv", index=False)
    kons = ida.loc[ida.RD.abs().idxmin()]
    gambar(V, arah, takarah, spec, f"B2 PC-stable + tier (alpha={P['alpha']}): CPDAG", out / "b2_graf.png")
    bd = banding(arah, takarah, G.subgraph(V))
    dt = time.time() - t0
    info(out / "b2_info.csv", n=len(d), uji=P['uji'], alpha=P['alpha'], maks_kondisi=P['maks_kondisi'],
         jumlah_uji=ci.jumlah, sisi_berarah=len(arah), sisi_tak_berarah=len(takarah),
         induk_pasti_T=', '.join(V[k] for k in pa) or '-', tetangga_tak_berarah_T=', '.join(V[k] for k in sib) or '-',
         jumlah_himpunan_IDA=len(H), **bd, detik_penemuan=round(dp, 2), memori_MB=round(mem, 2), detik=round(dt, 1))
    rows = [baris('B2', 'B2 PC + tier + IDA: min |RD| (konservatif)', kons, sisi=bd['sisi'], SHD=bd['SHD'],
                  detik=dt, detik_penemuan=dp, memori_MB=mem, catatan=f"{len(H)} himpunan IDA; rentang RD [{ida.RD.min():+.4f}, {ida.RD.max():+.4f}]")]
    lines = [f"B2 uji={ci.jumlah} sisi berarah={len(arah)} tak berarah={len(takarah)} SHD vs pakar={bd['SHD']}"
             f" | IDA {len(H)} himpunan, RD [{ida.RD.min():+.4f},{ida.RD.max():+.4f}], min|RD|={kons.RD:+.4f}"]
    return rows, lines


# ================================================================== B3 BN skor + Hill-Climbing
class Skor:
    """Skor lokal terdekomposisi s(V_j, Pa_j) dengan cache."""

    def __init__(self, d, V, jenis):
        self.jenis, self.n, self.cache = jenis, len(d), {}
        if jenis == "gauss":
            X = d[V].astype(float).values
            self.S = np.cov((X - X.mean(0)) / X.std(0), rowvar=False, ddof=0)
        else:
            self.kode, self.k = [], []
            for v in V:
                x = d[v].astype(float)
                if x.nunique() > P['maks_kategori']:
                    x = pd.qcut(x, P['bin'], labels=False, duplicates='drop')
                c = np.unique(x, return_inverse=True)[1]
                self.kode.append(c); self.k.append(c.max() + 1)

    def lokal(self, j, pa):
        key = (j, frozenset(pa))
        if key not in self.cache:
            self.cache[key] = self._hitung(j, sorted(pa))
        return self.cache[key]

    def _hitung(self, j, pa):
        n = self.n
        if self.jenis == "gauss":
            s2 = self.S[j, j] - (self.S[j, pa] @ np.linalg.solve(self.S[np.ix_(pa, pa)], self.S[pa, j]) if pa else 0)
            return -n / 2 * np.log(2 * np.pi * max(s2, 1e-12)) - n / 2 - (len(pa) + 2) / 2 * np.log(n)
        R = self.k[j]; Q = float(np.prod([self.k[v] for v in pa])) if pa else 1.0
        q = np.zeros(n, dtype=np.int64)
        for v in pa:
            q = q * self.k[v] + self.kode[v]
        q = np.unique(q, return_inverse=True)[1]
        N = np.bincount(q * R + self.kode[j], minlength=(q.max() + 1) * R).reshape(-1, R).astype(float)
        Nq = N.sum(1)
        if self.jenis == "bdeu":
            a = P['ess']
            return ((gammaln(a / Q) - gammaln(a / Q + Nq)).sum()
                    + (gammaln(a / (Q * R) + N) - gammaln(a / (Q * R))).sum())
        xlx = lambda M: np.where(M > 0, M * np.log(np.where(M > 0, M, 1)), 0).sum()
        return xlx(N) - xlx(Nq) - (R - 1) * Q / 2 * np.log(n)


def hill_climb(sk, p, tier, awal, maks, boleh=None):
    """Tambah / hapus / balik sisi dengan kenaikan skor terbesar; asiklik dan patuh tier.
    boleh: himpunan frozenset({i, j}) pasangan yang boleh bertetangga (mis. skeleton); None = semua."""
    Pa = [set() for _ in range(p)]
    for a, b in awal:
        Pa[b].add(a)
    G = nx.DiGraph(); G.add_nodes_from(range(p)); G.add_edges_from((a, b) for b in range(p) for a in Pa[b])
    s = [sk.lokal(j, Pa[j]) for j in range(p)]
    jejak = [dict(langkah=0, operasi='awal', skor=sum(s))]
    while True:
        best, op = 1e-9, None
        for i, j in itertools.permutations(range(p), 2):
            if i in Pa[j]:
                dh = sk.lokal(j, Pa[j] - {i}) - s[j]
                if dh > best:
                    best, op = dh, ('hapus', i, j)
                if tier[j] <= tier[i] and len(Pa[i]) < maks:
                    G.remove_edge(i, j); siklus = nx.has_path(G, i, j); G.add_edge(i, j)
                    if not siklus:
                        db = dh + sk.lokal(i, Pa[i] | {j}) - s[i]
                        if db > best:
                            best, op = db, ('balik', i, j)
            elif (j not in Pa[i] and tier[i] <= tier[j] and len(Pa[j]) < maks
                  and (boleh is None or frozenset((i, j)) in boleh) and not nx.has_path(G, j, i)):
                dt = sk.lokal(j, Pa[j] | {i}) - s[j]
                if dt > best:
                    best, op = dt, ('tambah', i, j)
        if op is None:
            break
        o, i, j = op
        if o in ('hapus', 'balik'):
            Pa[j].discard(i); G.remove_edge(i, j)
        if o == 'tambah':
            Pa[j].add(i); G.add_edge(i, j)
        if o == 'balik':
            Pa[i].add(j); G.add_edge(j, i)
        s[i], s[j] = sk.lokal(i, Pa[i]), sk.lokal(j, Pa[j])
        jejak.append(dict(langkah=len(jejak), operasi=f"{o} {i}->{j}", skor=sum(s)))
    return G, pd.DataFrame(jejak)


def b3(d, V, G, spec, out, B, rng):
    t0 = time.time(); T, Y = spec['T'], spec['Y']; ix = {v: i for i, v in enumerate(V)}
    tier = [C.TIER[v] for v in V]
    Ge = G.subgraph(V)
    tu = mulai_ukur()
    sk = Skor(d, V, P['skor'])
    awal = [(ix[a], ix[b]) for a, b in Ge.edges()] if P['awal'] == "pakar" else []
    Gi, jejak = hill_climb(sk, len(V), tier, awal, P['maks_induk'])
    dp, mem = selesai_ukur(tu)
    Gb = nx.relabel_nodes(Gi, dict(enumerate(V)))
    jejak['operasi'] = jejak.operasi.str.replace(r'(\d+)->(\d+)', lambda m: f"{V[int(m[1])]} -> {V[int(m[2])]}",
                                                 regex=True)
    jejak.to_csv(out / "b3_jejak.csv", index=False)
    pd.DataFrame(list(Gb.edges()), columns=['dari', 'ke']).to_csv(out / "b3_dag.csv", index=False)
    skor_pakar = sum(sk.lokal(ix[v], {ix[u] for u in Ge.predecessors(v)}) for v in V)
    r, Z, ok, cat = efek_graf(Gb, d, T, Y, B, rng)
    gambar(V, Gb.edges(), [], spec, f"B3 BN Hill-Climbing (skor={P['skor']}, awal={P['awal']})", out / "b3_graf.png")
    bd = banding(list(Gb.edges()), [], Ge)
    dt = time.time() - t0
    info(out / "b3_info.csv", n=len(d), skor=P['skor'], awal=P['awal'], maks_induk=P['maks_induk'],
         langkah=len(jejak) - 1, skor_akhir=round(jejak.skor.iloc[-1], 2), skor_DAG_pakar=round(skor_pakar, 2),
         skor_dihitung=len(sk.cache), adjustment=', '.join(Z) or '-', catatan=cat or '-', **bd,
         detik_penemuan=round(dp, 2), memori_MB=round(mem, 2), detik=round(dt, 1))
    rows = [baris('B3', 'B3 BN skor + do (g-komputasi)', r, sisi=bd['sisi'], SHD=bd['SHD'], detik=dt,
                  detik_penemuan=dp, memori_MB=mem,
                  catatan=f"|Z|={len(Z)}; skor {jejak.skor.iloc[-1]:.1f} vs pakar {skor_pakar:.1f}"
                          + (f"; {cat}" if cat else ""))]
    lines = [f"B3 skor={P['skor']} langkah={len(jejak) - 1} sisi={bd['sisi']} SHD vs pakar={bd['SHD']}"
             f" skor akhir={jejak.skor.iloc[-1]:.1f} (pakar {skor_pakar:.1f}) | RD={r['RD']:+.4f}"
             f" [{r.get('RD_lo', np.nan):+.4f},{r.get('RD_hi', np.nan):+.4f}]"]
    return rows, lines


# ================================================================== jalankan
def forest(tab, T, Y, path):
    t = tab.iloc[::-1]
    plt.figure(figsize=(8, 0.6 * len(t) + 1.2))
    y = np.arange(len(t))
    err = np.vstack([t.RD - t.RD_lo, t.RD_hi - t.RD]).clip(min=0)
    plt.errorbar(t.RD, y, xerr=np.nan_to_num(err), fmt='o', color='#1f77b4', capsize=4)
    plt.axvline(0, color='#888888', ls='--', lw=1)
    plt.yticks(y, t.metode, fontsize=8); plt.xlabel(f"Risk difference {T} -> {Y} (CI 95% bootstrap PSU)")
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


KRITERIA = {'BIC_SEM': True, 'CFI': False, 'lebar_CI': True}      # True = makin kecil makin baik
LABEL = {'B1': 'B1 SEM (DAG pakar)', 'B2': 'B2 PC + tier + IDA', 'B3': 'B3 BN berbasis skor'}


def graf_metode(out, kode, V, G):
    """DAG tiap metode. CPDAG B2 diperluas: sisi tak berarah diarahkan mengikuti urutan V tanpa siklus."""
    if kode == 'B1':
        return list(G.subgraph(V).edges())
    f = out / ("b2_cpdag.csv" if kode == 'B2' else "b3_dag.csv")
    if not f.exists():
        return None
    e = pd.read_csv(f)
    if kode == 'B3':
        return list(zip(e.dari, e.ke))
    H = nx.DiGraph(); H.add_nodes_from(V)
    H.add_edges_from(zip(e[e.jenis == '->'].dari, e[e.jenis == '->'].ke))
    for a, b in zip(e[e.jenis == '-'].dari, e[e.jenis == '-'].ke):
        H.add_edge(*((b, a) if nx.has_path(H, b, a) else (a, b)))
    return list(H.edges())


def rangkuman(d, V, G, out):
    """Pilih metode terbaik: peringkat rata-rata BIC-SEM, CFI (graf yang sama dinilai dengan SEM
    berbobot survei yang sama) dan lebar CI 95% RD. Tanpa ground truth: 'terbaik' = paling sesuai
    data dan paling presisi, bukan jaminan paling benar secara kausal."""
    tab = pd.read_csv(out / "perbandingan.csv").set_index('kode')
    rows = []
    for kode, label in LABEL.items():
        E = graf_metode(out, kode, V, G) if kode in tab.index else None
        if E is None:
            continue
        Ge = nx.DiGraph(); Ge.add_nodes_from(V); Ge.add_edges_from(E)
        f, t = fit_graf(d, V, Ge), tab.loc[kode]
        rows.append(dict(kode=kode, metode=label, sisi=len(E), BIC_SEM=f['BIC_SEM'], CFI=f['CFI'],
                         RMSEA=f['RMSEA'], SRMR=f['SRMR'], RD=t.RD, RD_lo=t.RD_lo, RD_hi=t.RD_hi,
                         lebar_CI=t.RD_hi - t.RD_lo, detik_penemuan=t.get('detik_penemuan', np.nan),
                         memori_MB=t.get('memori_MB', np.nan), SHD=t.SHD, catatan=t.catatan))
    r = pd.DataFrame(rows)
    r.loc[r.lebar_CI <= 0, 'lebar_CI'] = np.nan     # efek 0 karena tak ada jalur: bukan presisi
    for k, asc in KRITERIA.items():
        r[f'rank_{k}'] = r[k].rank(ascending=asc, method='min')
    r['peringkat_rata2'] = r.filter(like='rank_').mean(axis=1)
    r['terbaik'] = r.peringkat_rata2 == r.peringkat_rata2.min()
    r.to_csv(out / "rangkuman.csv", index=False)
    b = r[r.terbaik].iloc[0]
    unggul = [k for k in KRITERIA if b[f'rank_{k}'] == 1]
    return [f"TERBAIK: {b.metode} (peringkat rata-rata {b.peringkat_rata2:.2f}; unggul pada "
            f"{', '.join(unggul) or '-'}) RD={b.RD:+.4f} | "
            + " | ".join(f"{x.kode} BIC={x.BIC_SEM:.0f} CFI={x.CFI:.3f} CI={x.lebar_CI:.4f}" for x in r.itertuples())]


def run(df, nama=None, metode=("B1", "B2", "B3"), progress=None):
    rng = np.random.default_rng(C.SEED); lines = []
    fn = {"B1": b1, "B2": b2, "B3": b3}
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = C.OUT / "baseline" / n; out.mkdir(parents=True, exist_ok=True)
        d, V, G = siapkan(df, spec)
        salah = [(a, b) for a, b in G.subgraph(V).edges() if C.TIER[a] > C.TIER[b]]
        lines.append(f"BASE[{n}] {spec['T']}->{spec['Y']} n={len(d)} p={len(V)} boot={P['boot']}"
                     + (f" | PERINGATAN DAG pakar melawan tier: {salah}" if salah else ""))
        rows = []
        for m in metode:
            if progress:
                progress(f"{n}: {m} berjalan...")
            r, l = fn[m](d, V, G, spec, out, P['boot'], rng)
            rows += r; lines += [f"BASE[{n}] {x}" for x in l]
        tab = pd.DataFrame(rows)
        f = out / "perbandingan.csv"
        if f.exists():                          # pertahankan hasil metode yang tidak dijalankan ulang
            lama = pd.read_csv(f)
            tab = pd.concat([lama[~lama.kode.str[:2].isin([m[:2] for m in metode])], tab])
        tab = tab.sort_values('kode').reset_index(drop=True)
        tab.to_csv(f, index=False)
        forest(tab, spec['T'], spec['Y'], out / "perbandingan.png")
        lines += [f"BASE[{n}] {x}" for x in rangkuman(d, V, G, out)]
    return lines


def rangkum_ulang(df):
    """Hitung ulang rangkuman dari hasil yang sudah ada (tanpa menjalankan metode lagi)."""
    lines = []
    for n, spec in C.ANALISIS.items():
        out = C.OUT / "baseline" / n
        if (out / "perbandingan.csv").exists():
            d, V, G = siapkan(df, spec)
            lines += [f"BASE[{n}] {x}" for x in rangkuman(d, V, G, out)]
    return lines
