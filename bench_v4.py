"""BENCHMARK v4 (Fase 2): apakah pemilihan confounder lewat penemuan graf sadar-desain menghasilkan himpunan
penyesuaian yang valid, dan kapan koreksi desain justru merugikan?

Rencana analisis: RENCANA_ANALISIS_v4.md (dikunci dengan tag git rencana-v4 SEBELUM file ini dijalankan penuh).

DGP (per replikasi, graf benar acak dan patuh tier)
  node    : X1..X(p-2) di tier 0-2, T sendirian di tier 3, Y di tier 4; sebagian X biner, sisanya kontinu
  laten   : sebagian X (BENCH_V4['laten_frac']) TIDAK diberikan ke metode -> M-bias / confounding sisa mungkin
  confounder: >= 2 X dipaksa menjadi induk T dan Y; kekuatannya 'lemah' atau 'kuat' (faktor grid)
  desain  : sintetis setara IDHS (strata x PSU x unit), efek acak PSU per variabel (ICC homogen atau heterogen)
  efek benar: RD kondisional sampel = rata-rata berbobot Phi(do T=1) - Phi(do T=0) (eksak, tanpa galat Monte Carlo)
Metode (semua memakai estimator yang SAMA: AIPW cross-fitting per PSU, SE linearisasi desain). Model logistik
  memakai causal._fit dan trimming propensity = kuantil C.TRIM, sama dengan menu Inferensi Kausal (causal.estimate).
  M0 semua X teramati          M1 induk T di DAG pakar (graf benar diperturbasi)
  M2 PC naif + tier            M3 PC + uji desain (Rao-Scott / t-desain = setara sandwich CR1)
  M4 M3 dengan alpha longgar untuk pasangan yang melibatkan T atau Y (alpha_T; utama = BENCH_V4['alpha_T_utama'])
  M5 induk T dari M3 gabung induk T dari M1
  M6 disjunctive cause: induk T atau induk Y (selain T) dari graf M3
Jalankan:  python -u bench_v4.py [--rep N] [--pekerja K] [--ulang]
Keluaran:  hasil/benchmark_v4/per_rep.csv, ringkasan.csv, hipotesis.csv, meta.json (bisa dilanjutkan bila terputus)."""
import argparse
import zlib
import itertools
import json
import os
import time
import warnings
import numpy as np
import pandas as pd
import networkx as nx
import statsmodels.api as sm
from scipy import stats
import config as C
import baseline as BL
import causal as K
import novelty as N

warnings.filterwarnings("ignore")
P = C.BENCH_V4
OUT = C.OUT / "benchmark_v4"


# ================================================================== desain sintetis
def buat_desain(rng):
    h, m, k = P['desain']
    strata = np.repeat(np.arange(h), m * k); psu = np.repeat(np.arange(h * m), k)
    bobot = np.repeat(rng.lognormal(0, 0.4, h * m), k) * rng.uniform(0.8, 1.25, h * m * k)
    return pd.DataFrame({'strata': strata, 'psu': psu, 'bobot': bobot / bobot.mean()})


# ================================================================== graf benar acak
def buat_dag(p, kuat, beta_ty, rng):
    """-> dict graf benar: G (semua node), urutan, tier, koefisien, jenis, prevalensi, node teramati."""
    m = p - 2
    X = [f"X{i + 1}" for i in range(m)]
    tx = np.sort(rng.integers(0, 3, m))
    tier = {**dict(zip(X, tx.tolist())), 'T': 3, 'Y': 4}
    urut = X + ['T', 'Y']
    G = nx.DiGraph(); G.add_nodes_from(urut); b = {}
    q = min(1.0, 2.0 / max(m - 1, 1))                                  # rerata ~1-2 induk antar-X
    for i, j in itertools.combinations(range(m), 2):
        if rng.random() < q:
            G.add_edge(X[i], X[j]); b[X[i], X[j]] = rng.uniform(0.2, 0.5) * rng.choice([-1, 1])
    conf = list(rng.choice(X, size=min(3, m), replace=False))          # confounder paksa
    rentang = (0.3, 0.5) if kuat == "kuat" else (0.05, 0.15)
    for x in X:
        for tgt in ('T', 'Y'):
            if x in conf:
                G.add_edge(x, tgt); b[x, tgt] = rng.uniform(*rentang) * rng.choice([-1, 1])
            elif rng.random() < 0.25:                                    # instrumen (->T) / prediktor (->Y)
                G.add_edge(x, tgt); b[x, tgt] = rng.uniform(0.2, 0.5) * rng.choice([-1, 1])
    G.add_edge('T', 'Y'); b['T', 'Y'] = beta_ty
    jenis = {x: ("biner" if rng.random() < 0.5 else "kontinu") for x in X} | {'T': 'biner', 'Y': 'biner'}
    pi = {v: rng.uniform(0.2, 0.6) for v in X} | {'T': rng.uniform(0.5, 0.75), 'Y': 0.15}
    nlat = int(round(P['laten_frac'] * m))
    laten = list(rng.choice([x for x in X if x not in conf], size=min(nlat, m - len(conf)), replace=False))
    obs = [x for x in X if x not in laten]
    return dict(G=G, urut=urut, tier=tier, b=b, jenis=jenis, pi=pi, obs=obs, laten=laten, X=X)


def adjustment_sah(G, x, y, Z):
    """Kriteria adjustment umum (Shpitser/Perkovic), salinan benchmark.py."""
    Z = set(Z) - {x}
    if y in Z:
        return False
    de_x = nx.descendants(G, x)
    dsep = getattr(nx, "is_d_separator", None) or nx.d_separated
    if y not in de_x:
        return dsep(G, {x}, {y}, Z)
    cn = {w for w in de_x if w == y or y in nx.descendants(G, w)}
    forb = set().union(*[nx.descendants(G, w) | {w} for w in cn])
    if Z & forb:
        return False
    Gp = G.copy(); Gp.remove_edges_from([(x, c) for c in list(G.successors(x)) if c in cn])
    return dsep(Gp, {x}, {y}, Z)


def dag_teridentifikasi(p, kuat, beta_ty, rng, coba=50):
    """Tolak graf yang efeknya tidak teridentifikasi dari node teramati (himpunan oracle tidak sah)."""
    for _ in range(coba):
        g = buat_dag(p, kuat, beta_ty, rng)
        anc = (nx.ancestors(g['G'], 'T') | nx.ancestors(g['G'], 'Y')) - {'T', 'Y'}
        oracle = [v for v in g['obs'] if v in anc]
        if adjustment_sah(g['G'], 'T', 'Y', oracle):
            g['oracle'] = oracle
            return g
    raise RuntimeError("gagal membangkitkan graf yang teridentifikasi")


# ================================================================== bangkitkan data
def bangkit(g, ds, icc, rng):
    """-> (DataFrame node teramati + T + Y, RD benar kondisional sampel)."""
    n, pc = len(ds.pc), ds.pc
    val, inp, simpan = {}, {}, {}
    for v in g['urut']:
        pa = list(g['G'].predecessors(v))
        mu = sum(g['b'][a, v] * inp[a] for a in pa) if pa else np.zeros(n)
        r = icc[v]
        s = np.sqrt(max(1 - np.var(mu), 0.2))
        u = rng.standard_normal(ds.npsu)[pc]; e = rng.standard_normal(n)
        z = mu + s * (np.sqrt(r) * u + np.sqrt(1 - r) * e)
        if g['jenis'][v] == "biner":
            kappa = stats.norm.ppf(1 - g['pi'][v])
            val[v] = (z > kappa).astype(float); inp[v] = val[v] - g['pi'][v]
        else:
            val[v] = z; inp[v] = z
        if v == 'Y':
            simpan = dict(mu_tanpa_T=mu - g['b']['T', 'Y'] * inp['T'], s=s, r=r, u=u, kappa=kappa)
    k = simpan
    pr = lambda t: stats.norm.cdf((k['mu_tanpa_T'] + g['b']['T', 'Y'] * (t - g['pi']['T']) + k['s'] * np.sqrt(k['r']) * k['u']
                                   - k['kappa']) / (k['s'] * np.sqrt(1 - k['r'])))
    return pd.DataFrame({v: val[v] for v in g['obs'] + ['T', 'Y']}), pr(1.0), pr(0.0)


# ================================================================== estimator bersama: AIPW cross-fit per PSU
def _logit(y, X, w, Xb):
    """Logistik berbobot dengan causal._fit (IRLS, maxiter 50) -> prediksi pada Xb. X, Xb TANPA konstanta."""
    try:
        m = K._fit(y, X, w)
        return np.asarray(m.predict(sm.add_constant(Xb, has_constant='add')))
    except Exception:                                                   # mis. separasi sempurna
        return np.full(len(Xb), np.average(y, weights=w))


def aipw(d, Z, ds, w, K, rng):
    """RD, SE desain, CI 95% (t, df desain). Lipatan = PSU diacak di dalam strata."""
    t, y = d['T'].values, d['Y'].values
    Zm = d[Z].values if Z else np.zeros((len(d), 0))
    if Z:
        Zm = (Zm - Zm.mean(0)) / np.where(Zm.std(0) > 0, Zm.std(0), 1)
    lip_psu = np.empty(ds.npsu, dtype=int)
    for h in range(len(ds.nh)):
        ix = np.flatnonzero(ds.h == h); lip_psu[ix] = rng.permutation(len(ix)) % K
    lip = lip_psu[ds.pc]
    m1, m0, e = np.zeros(len(d)), np.zeros(len(d)), np.zeros(len(d))
    for k in range(K):
        tr, te = lip != k, lip == k
        e[te] = _logit(t[tr], Zm[tr], w[tr], Zm[te])
        Xo = np.column_stack([Zm, t])
        m1[te] = _logit(y[tr], Xo[tr], w[tr], np.column_stack([Zm[te], np.ones(te.sum())]))
        m0[te] = _logit(y[tr], Xo[tr], w[tr], np.column_stack([Zm[te], np.zeros(te.sum())]))
    e = np.clip(e, *np.quantile(e, C.TRIM))      # trimming kuantil, sama dengan causal.estimate
    psi = m1 - m0 + t * (y - m1) / e - (1 - t) * (y - m0) / (1 - e)
    rd = float(np.average(psi, weights=w))
    se = float(np.sqrt(ds.var_total(w * (psi - rd) / w.sum())[0]))
    q = stats.t.ppf(0.975, ds.df)
    return rd, se, rd - q * se, rd + q * se


# ================================================================== penemuan graf
class Memo:
    """Cache p-value agar M3 dan M4 berbagi uji yang sama."""
    def __init__(self, ci):
        self.ci, self.c, self.jumlah = ci, {}, 0

    def p(self, i, j, S):
        k = (min(i, j), max(i, j), tuple(sorted(S)))
        if k not in self.c:
            self.c[k] = self.ci.p(i, j, S); self.jumlah += 1
        return self.c[k]


class Longgar:
    """p-value pasangan yang melibatkan node khusus (T, Y) diskalakan agar ditolak pada alpha_T, bukan alpha."""
    def __init__(self, ci, khusus, alpha, alpha_T):
        self.ci, self.khusus, self.f = ci, set(khusus), alpha / alpha_T

    def p(self, i, j, S):
        p = self.ci.p(i, j, S)
        return p * self.f if (i in self.khusus or j in self.khusus) else p


def pc_induk(ci, V, tier):
    """PC-stable + tier + Meek (fungsi baseline) -> (induk T, induk Y selain T, skeleton)."""
    A, sep = BL.pc_skeleton(ci, len(V), P['alpha'], P['maks_kondisi'])
    skel = {frozenset((V[i], V[j])) for i, j in itertools.combinations(range(len(V)), 2) if A[i, j]}
    A = BL.orientasi(A, sep, np.array(tier))
    it, iy = V.index('T'), V.index('Y')
    paT = [V[k] for k in range(len(V)) if A[k, it] and k != iy]       # tier: tetangga T di tier lebih awal
    paY = [V[k] for k in range(len(V)) if A[k, iy] and k != it]
    return paT, paY, skel


def perturbasi(G, nodes, tier, frac, rng):
    """DAG pakar: hapus frac panah (kecuali T->Y), tambah panah acak patuh tier sebanyak yang dihapus."""
    E = [e for e in G.edges() if e != ('T', 'Y') and e[0] in nodes and e[1] in nodes]
    k = int(round(frac * len(E))); hapus = {E[i] for i in rng.permutation(len(E))[:k]}
    H = nx.DiGraph(); H.add_nodes_from(nodes); H.add_edges_from(e for e in E if e not in hapus); H.add_edge('T', 'Y')
    kand = [(a, b) for a, b in itertools.permutations(nodes, 2)
            if tier[a] <= tier[b] and a != 'Y' and not H.has_edge(a, b) and not H.has_edge(b, a)]
    tambah = 0
    for i in rng.permutation(len(kand)):
        if tambah >= k:
            break
        a, b = kand[i]
        if not nx.has_path(H, b, a):
            H.add_edge(a, b); tambah += 1
    return H


# ================================================================== satu replikasi
def sel_list():
    return [dict(icc=i, beta_ty=b, kuat=k, p=p) for i in P['icc'] for b in P['beta_ty']
            for k in P['kuat_confounder'] for p in P['p']]


def sel_id(s):
    return f"icc={s['icc']}|beta={s['beta_ty']}|{s['kuat']}|p={s['p']}"


def satu(tugas):
    s, r = tugas
    rng = np.random.default_rng([C.SEED, r, zlib.crc32(sel_id(s).encode())])   # crc32: stabil antar-proses (hash() acak per proses)
    ds_df = buat_desain(np.random.default_rng([C.SEED, 99]))           # desain tetap untuk semua replikasi
    ds = N.Desain(ds_df); w = ds_df.bobot.values
    g = dag_teridentifikasi(s['p'], s['kuat'], s['beta_ty'], rng)
    icc = {v: (rng.uniform(0.1, 0.8) if s['icc'] == "heterogen" else float(s['icc'])) for v in g['urut']}
    dat, p1, p0 = bangkit(g, ds, icc, rng)
    rd_benar = float(np.average(p1 - p0, weights=w))
    d = pd.concat([ds_df, dat], axis=1)
    V = g['obs'] + ['T', 'Y']; tier = [g['tier'][v] for v in V]
    benar_skel = {frozenset(e) for e in g['G'].subgraph(V).edges()}
    baris, Zs, info = [], {}, {}

    def temukan(nama, ci):
        t0 = time.time(); paT, paY, skel = pc_induk(ci, V, tier)
        fp = len(skel - benar_skel)
        info[nama] = dict(detik_penemuan=time.time() - t0, FDR=fp / max(len(skel), 1),
                          recall=len(skel & benar_skel) / max(len(benar_skel), 1))
        return paT, paY

    Zs['M0'] = list(g['obs'])
    Gp = perturbasi(g['G'].subgraph(V).copy(), V, g['tier'], 0.30, rng)
    Zs['M1'] = [v for v in Gp.predecessors('T')]
    Zs['M2'], _ = temukan('M2', BL.UjiCI(d, V, "campuran"))
    des = Memo(N.UjiDesain(d, V, "desain", ds, C.NOVELTY['sd_rs_orde']))
    paT3, paY3 = temukan('M3', des)
    Zs['M3'] = paT3
    khusus = [V.index('T'), V.index('Y')]
    for a in P['alpha_T']:
        nm = f"M4(aT={a})"
        Zs[nm], _ = temukan(nm, Longgar(des, khusus, P['alpha'], a))
    Zs['M5'] = sorted(set(paT3) | set(Zs['M1']))
    Zs['M6'] = sorted(set(paT3) | set(paY3))
    for nama, Z in Zs.items():
        t0 = time.time()
        rd, se, lo, hi = aipw(d, Z, ds, w, P['K'], rng)
        baris.append(dict(sel=sel_id(s), **s, rep=r, metode=nama, n_Z=len(Z), Z=";".join(Z),
                          valid=bool(adjustment_sah(g['G'], 'T', 'Y', Z)), RD_benar=rd_benar, RD_hat=rd, se=se,
                          RD_lo=lo, RD_hi=hi, cakup=bool(lo <= rd_benar <= hi), detik_estimasi=time.time() - t0,
                          n_obs=len(g['obs']), n_laten=len(g['laten']), **info.get(nama, {})))
    return baris


# ================================================================== ringkasan dan hipotesis
def _wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n; dd = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / dd; h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / dd
    return c - h, c + h


def _wil(x, y, alt):
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    if len(x) < 5 or np.allclose(x, y):
        return 1.0
    try:
        return float(stats.wilcoxon(x, y, alternative=alt, zero_method="zsplit").pvalue)
    except ValueError:
        return 1.0


def ringkas():
    f = OUT / "per_rep.csv"
    if not f.exists():
        return pd.DataFrame(), pd.DataFrame()
    d = pd.read_csv(f)
    d['galat'] = d.RD_hat - d.RD_benar
    g = d.groupby(['sel', 'icc', 'beta_ty', 'kuat', 'p', 'metode'], sort=False)
    rk = g.agg(rep=('rep', 'count'), valid=('valid', 'mean'), bias=('galat', 'mean'),
               RMSE=('galat', lambda e: np.sqrt((e ** 2).mean())), cakupan=('cakup', 'mean'),
               lebar_CI=('RD_hi', 'mean'), n_Z=('n_Z', 'mean'), FDR=('FDR', 'mean'), recall=('recall', 'mean'),
               detik_penemuan=('detik_penemuan', 'mean')).reset_index()
    rk['lebar_CI'] = g.apply(lambda x: (x.RD_hi - x.RD_lo).mean()).values
    rk.to_csv(OUT / "ringkasan.csv", index=False)
    # hipotesis (rencana v4): pada ICC heterogen, digabung atas faktor lain
    he = d[d.icc.astype(str) == "heterogen"]
    utama = f"M4(aT={P['alpha_T_utama']})"
    kandidat = [utama, "M5", "M6"]
    vr = he.groupby('metode').valid.mean()
    terbaik = max(kandidat, key=lambda m: vr.get(m, -1))
    hp = []
    k_, n_ = int(he[he.metode == terbaik].valid.sum()), int((he.metode == terbaik).sum()); lo, hi = _wilson(k_, n_)
    ok10 = vr.get(terbaik, 0) >= .90 and vr.get(terbaik, 0) >= vr.get("M2", 1)
    hp.append(dict(kode="H10", hipotesis="Validitas penyesuaian metode terbaik (M4 utama/M5/M6) >= 90% dan >= M2",
                   hasil=f"{terbaik} {vr.get(terbaik, np.nan):.1%} (Wilson {lo:.1%}-{hi:.1%}) vs M2 {vr.get('M2', np.nan):.1%},"
                         f" M0 {vr.get('M0', np.nan):.1%}", putusan="diterima" if ok10 else "ditolak"))
    def pv(a, b, kol, alt):
        """Wilcoxon berpasangan per (sel, rep); pasangan yang salah satunya hilang dibuang."""
        x = he[he.metode == a].set_index(['sel', 'rep'])[kol]; y = he[he.metode == b].set_index(['sel', 'rep'])[kol]
        ix = x.index.intersection(y.index)
        return _wil(x[ix].values.astype(float), y[ix].values.astype(float), alt)
    f4, f2 = he[he.metode == utama].FDR.mean(), he[he.metode == "M2"].FDR.mean(); p11 = pv(utama, "M2", "FDR", "less")
    hp.append(dict(kode="H11", hipotesis=f"FDR sisi {utama} <= M2 (naif)", hasil=f"{f4:.3f} vs {f2:.3f} (Wilcoxon p {p11:.2g})",
                   putusan="diterima" if (f4 <= f2 and p11 < .05) else "ditolak"))
    he = he.assign(absg=he.galat.abs())
    rm = he.groupby('metode').galat.apply(lambda e: np.sqrt((e ** 2).mean()))
    p12 = pv(terbaik, "M0", "absg", "less")
    hp.append(dict(kode="H12", hipotesis="RMSE metode terbaik <= M0 (semua kovariat pra-treatment)",
                   hasil=f"{terbaik} {rm.get(terbaik, np.nan):.4f} vs M0 {rm.get('M0', np.nan):.4f} (Wilcoxon |galat| p {p12:.2g})",
                   putusan="diterima" if rm.get(terbaik, 9) <= rm.get('M0', 0) else "ditolak"))
    cv = he[he.metode == terbaik].cakup.mean()
    hp.append(dict(kode="H13", hipotesis="Cakupan CI 95% metode terbaik >= 92%", hasil=f"{terbaik} {cv:.1%}",
                   putusan="diterima" if cv >= .92 else "ditolak"))
    skenario = "A (metode usulan memperbaiki tarik-menarik)" if ok10 else "B (studi peringatan)"
    hp.append(dict(kode="Gerbang 2", hipotesis="Bingkai naskah", hasil=f"terbaik = {terbaik}", putusan=skenario))
    hp = pd.DataFrame(hp); hp.to_csv(OUT / "hipotesis.csv", index=False)
    return rk, hp


# ================================================================== jalankan
def main():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", type=int, default=P['rep']); ap.add_argument("--pekerja", type=int, default=P['pekerja'])
    ap.add_argument("--ulang", action="store_true", help="hapus hasil lama dan mulai dari nol")
    ap.add_argument("--ringkas", action="store_true", help="hanya hitung ulang ringkasan dan hipotesis")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "per_rep.csv"
    if a.ringkas:
        rk, hp = ringkas(); print(hp.to_string(index=False)); return
    if a.ulang:
        f.unlink(missing_ok=True)
    sudah = set()
    if f.exists():                                                    # lanjutkan run yang terputus
        lama = pd.read_csv(f, usecols=['sel', 'rep']); sudah = set(zip(lama.sel, lama.rep))
    tugas = [(s, r) for s in sel_list() for r in range(a.rep) if (sel_id(s), r) not in sudah]
    meta = dict(mulai=time.strftime("%Y-%m-%d %H:%M"), rep=a.rep, pekerja=a.pekerja, sel=len(sel_list()),
                tugas_baru=len(tugas), sudah=len(sudah), konfigurasi=P)
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    print(f"{len(tugas)} tugas baru ({len(sudah)} sudah ada), {a.pekerja} pekerja", flush=True)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    t0, selesai, galat = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.pekerja) as ex:
        fut = {ex.submit(satu, t): t for t in tugas}
        for fu in as_completed(fut):
            try:
                pd.DataFrame(fu.result()).to_csv(f, mode="a", index=False, header=not f.exists())
            except Exception as e:
                galat.append(f"{sel_id(fut[fu][0])} rep {fut[fu][1]}: {e!r}")
            selesai += 1
            if selesai % 10 == 0 or selesai == len(tugas):
                el = time.time() - t0
                print(f"{selesai}/{len(tugas)} selesai, {el / 60:.1f} menit, sisa ~{el / selesai * (len(tugas) - selesai) / 60:.0f} menit,"
                      f" gagal {len(galat)}", flush=True)
    if galat:
        (OUT / "gagal.txt").write_text("\n".join(galat), encoding="utf-8")
    rk, hp = ringkas()
    print(hp.to_string(index=False))


if __name__ == "__main__":
    main()
