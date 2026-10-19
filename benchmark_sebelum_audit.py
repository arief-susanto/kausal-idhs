"""MENU BENCHMARK SEMI-SINTETIK: menguji H1-H5 dengan graf benar yang diketahui, desain klaster IDHS dipertahankan.
Skenario A (variabel teramati)
  graf benar  = DAG pakar yang diperturbasi (sebagian panah dihapus/ditambah, patuh tier); B1 tetap memakai DAG pakar
                asli sehingga menggambarkan pakar yang keliru sebagian
  SCM         = tiap node dicocokkan pada data IDHS terhadap induknya di graf benar (logistik / linear berbobot)
                + efek acak PSU (ICC dari ANOVA residual) -> bobot, PSU, strata, dan ukuran klaster asli dipakai ulang
  metode      = B1, B2, B3, N1, N2, SOL-DAG (tanpa lapis MLC karena tidak ada indikator) + 3 ablasi SOL
Skenario B (konstruk laten)
  node benar  = node MLC v2 pada data nyata (konstruk reflektif, komposit, variabel teramati); graf benar = DAG pakar
                dipetakan ke tingkat konstruk lalu diperturbasi; koefisien dari regresi pada Sigma_V nyata
  data        = indikator dibangkitkan dari konstruknya (muatan nyata; komposit = indeks indikatornya), biner lewat ambang
  metode      = SOL-DAG, SOL tanpa MLC, N3, N3 tanpa konstruk, B2 dan B3 pada indikator mentah
Efek benar  = selisih risiko kontrafaktual do(T=1) - do(T=0) dengan noise bersama pada populasi desain berulang.
Metrik      = SHD, SID, |galat RD|, cakupan CI 95%, waktu dan memori penemuan, stabilitas antar-replikasi,
              galat tipe I dan daya uji pada pernyataan independensi yang benar."""
import itertools
import json
import os
import time
import numpy as np
import pandas as pd
import networkx as nx
from scipy import stats, special
import statsmodels.api as sm
import config_old as C
import baseline as BL
import novelty as N
import sol_dag as S

P = C.BENCH
KTX = {}           # konteks bersama di proses pekerja (diisi _init)


def folder(nama):
    o = C.OUT / "benchmark" / nama
    o.mkdir(parents=True, exist_ok=True)
    return o


# ================================================================== graf benar
def perturbasi(Ge, nodes, tier, T, Y, frac, rng):
    """Hapus frac panah DAG pakar (kecuali T->Y), tambah panah acak patuh tier sebanyak yang dihapus."""
    E = [e for e in Ge.edges() if e != (T, Y) and e[0] in nodes and e[1] in nodes]
    k = int(round(frac * len(E)))
    hapus = {E[i] for i in rng.permutation(len(E))[:k]}
    G = nx.DiGraph(); G.add_nodes_from(nodes)
    G.add_edges_from(e for e in E if e not in hapus); G.add_edge(T, Y)
    kand = [(a, b) for a, b in itertools.permutations(nodes, 2)
            if tier[a] <= tier[b] and not G.has_edge(a, b) and not G.has_edge(b, a) and a != Y]
    tambah = []
    for i in rng.permutation(len(kand)):
        if len(tambah) >= k:
            break
        a, b = kand[i]
        if not nx.has_path(G, b, a):
            G.add_edge(a, b); tambah.append((a, b))
    return G, sorted(hapus), tambah


# ================================================================== metrik graf
def adjustment_sah(G, x, y, Z):
    """Kriteria adjustment umum (Shpitser/Perkovic): Z sah untuk efek x -> y di DAG G."""
    Z = set(Z) - {x}
    if y in Z:
        return False
    de_x = nx.descendants(G, x)
    dsep = getattr(nx, "is_d_separator", None) or nx.d_separated
    if y not in de_x:
        return dsep(G, {x}, {y}, Z)
    cn = {w for w in de_x if w == y or y in nx.descendants(G, w)}           # node pada jalur kausal (tanpa x)
    forb = set().union(*[nx.descendants(G, w) | {w} for w in cn])
    if Z & forb:
        return False
    Gp = G.copy(); Gp.remove_edges_from([(x, c) for c in list(G.successors(x)) if c in cn])
    return dsep(Gp, {x}, {y}, Z)


def sid(Gt, Ge):
    """Structural Intervention Distance (Peters & Buehlmann, 2015): pasangan (i, j) yang distribusi intervensinya
    salah bila memakai Pa_Ge(i) sebagai adjustment set di graf benar Gt."""
    salah = 0
    for i in Gt:
        pa = set(Ge.predecessors(i)) if i in Ge else set()
        de = nx.descendants(Gt, i)
        for j in Gt:
            if j == i:
                continue
            ok = (j not in de) if j in pa else adjustment_sah(Gt, i, j, pa)
            salah += not ok
    return salah


def shd(Gt, arah, takarah=()):
    return BL.banding(list(arah), list(takarah), Gt)['SHD']


def kolaps(G, peta):
    """Petakan graf node mentah ke node benar (indikator -> konstruknya); sisi di dalam satu kelompok dibuang."""
    H = nx.DiGraph(); H.add_nodes_from(set(peta.values()))
    H.add_edges_from({(peta[a], peta[b]) for a, b in G.edges() if a in peta and b in peta and peta[a] != peta[b]})
    return H


def dag_dari_cpdag(A, nama):
    """Perluasan CPDAG/PDAG -> DAG yang dijamin asiklik: panah berarah dulu (yang membentuk siklus dilewati),
    lalu sisi tak berarah diarahkan tanpa membentuk siklus."""
    p = len(nama); G = nx.DiGraph(); G.add_nodes_from(nama)
    for i, j in itertools.permutations(range(p), 2):
        if A[i, j] and not A[j, i] and not nx.has_path(G, nama[j], nama[i]):
            G.add_edge(nama[i], nama[j])
    for i, j in itertools.combinations(range(p), 2):
        if A[i, j] and A[j, i]:
            G.add_edge(*((nama[j], nama[i]) if nx.has_path(G, nama[j], nama[i]) else (nama[i], nama[j])))
    return G


def tepi(G):
    return ";".join(sorted(f"{a}>{b}" for a, b in G.edges()))


# ================================================================== skenario A: SCM dari IDHS
def _anova(r, pc):
    nc = np.bincount(pc); k, n = len(nc), len(r)
    mc = np.bincount(pc, weights=r) / nc
    msb = (nc * (mc - r.mean()) ** 2).sum() / (k - 1); msw = ((r - mc[pc]) ** 2).sum() / (n - k)
    n0 = (n - (nc ** 2).sum() / n) / (k - 1)
    return max((msb - msw) / n0, 0.0), msw


def fit_scm(d, G):
    pc = d.groupby(['strata', 'psu']).ngroup().values; w = d.bobot.values
    par = {}
    for v in nx.topological_sort(G):
        pa = list(G.predecessors(v)); y = d[v].astype(float).values
        X = sm.add_constant(d[pa].astype(float).values, has_constant='add') if pa else np.ones((len(d), 1))
        if set(np.unique(y)) <= {0.0, 1.0}:
            m = sm.GLM(y, X, family=sm.families.Binomial(), var_weights=w).fit()
            sb, sw = _anova(y - m.predict(X), pc); icc = min(sb / (sb + sw), 0.5) if sb + sw > 0 else 0.0
            par[v] = dict(pa=pa, beta=np.asarray(m.params), biner=True, sb=np.sqrt(icc / (1 - icc) * np.pi ** 2 / 3))
        else:
            m = sm.WLS(y, X, weights=w).fit(); sb, sw = _anova(y - m.predict(X), pc)
            par[v] = dict(pa=pa, beta=np.asarray(m.params), biner=False, sb=np.sqrt(sb), sw=np.sqrt(sw))
    return par


def noise_A(par, n, npsu, rng):
    return {v: (rng.standard_normal(npsu), rng.random(n) if p['biner'] else rng.standard_normal(n)) for v, p in par.items()}


def bangkit_A(par, pc, nz, do=None, prob=None):
    X, pr_out = {}, None
    for v, p in par.items():
        if do and v in do:
            X[v] = np.full(len(pc), float(do[v])); continue
        eta = p['beta'][0] + sum(p['beta'][k + 1] * X[q] for k, q in enumerate(p['pa']))
        u, e = nz[v]
        if p['biner']:
            pr = special.expit(eta + p['sb'] * u[pc])
            if v == prob:
                pr_out = pr
            X[v] = (e < pr).astype(float)
        else:
            X[v] = eta + p['sb'] * u[pc] + p['sw'] * e
    return X, pr_out


def rd_benar_A(par, d, T, Y, K, rng):
    pc0 = d.groupby(['strata', 'psu']).ngroup().values; npsu = pc0.max() + 1
    pc = np.concatenate([pc0 + k * npsu for k in range(K)]); w = np.tile(d.bobot.values, K)
    nz = noise_A(par, len(pc), npsu * K, rng)
    p1 = bangkit_A(par, pc, nz, {T: 1}, Y)[1]; p0 = bangkit_A(par, pc, nz, {T: 0}, Y)[1]
    return float(np.average(p1 - p0, weights=w)), float(np.average(p1, weights=w)), float(np.average(p0, weights=w))


# ================================================================== skenario B: SCM konstruk laten
def siapkan_B(df, spec, rng):
    d_m, obs, cols = N.data_mlc(spec, df)
    m = N.bangun_mlc(d_m, obs)
    Vm, tier = m['Vm'], dict(zip(m['Vm'], m['tier']))
    peta = {c: c for c in Vm}
    for k in m['refl']:
        peta.update({m['cols'][i]: k for i in m['grup'][k]})
    for k, (ii, w, _) in m['komposit'].items():
        peta.update({m['cols'][i]: k for i in ii})
    peta.update({a: b for a, b in C.MLC_DIGANTI.items() if b in Vm})
    Ge = BL.build_dag(spec)
    Gk = nx.DiGraph(); Gk.add_nodes_from(Vm)
    for a, b in Ge.edges():
        if a in peta and b in peta and peta[a] != peta[b] and tier[peta[a]] <= tier[peta[b]] \
                and not nx.has_path(Gk, peta[b], peta[a]):
            Gk.add_edge(peta[a], peta[b])
    T, Y = spec['T'], spec['Y']
    Gt, hapus, tambah = perturbasi(Gk, Vm, tier, T, Y, P['perturbasi'], rng)
    S_ = m['S']; ix = {v: i for i, v in enumerate(Vm)}
    u_real = pd.concat([d_m, m['skor']], axis=1)
    pc = d_m.groupby(['strata', 'psu']).ngroup().values
    par = {}
    for v in nx.topological_sort(Gt):
        pa = list(Gt.predecessors(v)); j = ix[v]; q = [ix[a] for a in pa]
        b = np.linalg.solve(S_[np.ix_(q, q)], S_[q, j]) if q else np.zeros(0)
        res = max(1 - (S_[j, q] @ b if q else 0), 0.05)
        x = u_real[v].astype(float).values; x = (x - x.mean()) / (x.std() or 1)
        sb, sw = _anova(x, pc); icc = min(sb / (sb + sw), 0.5) if sb + sw > 0 else 0.0
        jenis = "reflektif" if v in m['refl'] else "komposit" if v in m['komposit'] else \
            ("biner" if set(np.unique(d_m[v])) <= {0.0, 1.0} else "kontinu")
        info = dict(pa=pa, beta=b, res=res, icc=icc, jenis=jenis)
        if jenis == "biner":
            info['pi'] = float(np.average(d_m[v], weights=d_m.bobot)); info['kappa'] = stats.norm.ppf(1 - info['pi'])
        if jenis == "reflektif":
            info['ind'] = [(m['cols'][i], float(m['lam'][v][0][t]), bool(m['biner'][i]),
                            float(d_m[m['cols'][i]].mean())) for t, i in enumerate(m['grup'][v])]
        if jenis == "komposit":
            ii, w, _ = m['komposit'][v]
            val, vec = np.linalg.eigh(m['R'][np.ix_(ii, ii)])
            a_ = np.clip(np.sqrt(val[-1]) * np.abs(vec[:, -1]) * np.sign(w), -0.95, 0.95)
            info['ind'] = [(m['cols'][i], float(a_[t]), bool(m['biner'][i]), float(d_m[m['cols'][i]].mean()))
                           for t, i in enumerate(ii)]
            info['w'] = w
        par[v] = info
    tier_raw = {c: (C.TIER[c] if c in C.TIER else tier[peta[c]]) for c in cols}
    return dict(d=d_m, obs=obs, cols=cols, Vm=Vm, tier=tier, Gt=Gt, par=par, peta=peta, tier_raw=tier_raw,
                hapus=hapus, tambah=tambah, m_real=m)


def _baku(x):
    s = x.std()
    return (x - x.mean()) / (s if s > 0 else 1)


def bangkit_B(par, pc, npsu, rng, nz=None, do=None, prob=None):
    """-> (kolom indikator + teramati, nilai node, prob Y). nz: dict noise yang diisi/dipakai ulang (noise bersama
    untuk kontrafaktual); rng hanya dipakai bila noise belum ada."""
    n = len(pc)
    nz = {} if nz is None else nz

    def get(k, size):
        if k not in nz:
            nz[k] = rng.standard_normal(size)
        return nz[k]
    val, kol, pr_out = {}, {}, None
    for v, p in par.items():
        if do and v in do:
            val[v] = np.full(n, float(do[v])); kol[v] = val[v]
            val[v + "@"] = (val[v] - p['pi']) / np.sqrt(p['pi'] * (1 - p['pi'])); continue
        mu = sum(p['beta'][k] * val[q + "@"] for k, q in enumerate(p['pa'])) if p['pa'] else np.zeros(n)
        s = np.sqrt(p['res'])
        up, ee = get(v + ":u", npsu)[pc], get(v + ":e", n)
        z = mu + s * (np.sqrt(p['icc']) * up + np.sqrt(1 - p['icc']) * ee)
        if p['jenis'] == "biner":
            x = (z > p['kappa']).astype(float); val[v] = x; kol[v] = x
            val[v + "@"] = (x - p['pi']) / np.sqrt(p['pi'] * (1 - p['pi']))
            if v == prob:
                pr_out = stats.norm.cdf((mu + s * np.sqrt(p['icc']) * up - p['kappa']) / (s * np.sqrt(1 - p['icc'])))
        elif p['jenis'] == "kontinu":
            val[v] = z; kol[v] = z; val[v + "@"] = z
        else:
            xs = []
            for c, lam, bin_, pi in p['ind']:
                xi = lam * z + np.sqrt(max(1 - lam ** 2, 0.01)) * get(f"{v}:{c}", n)
                xo = (xi > stats.norm.ppf(1 - pi)).astype(float) if bin_ else xi
                kol[c] = xo; xs.append(_baku(xo))
            if p['jenis'] == "reflektif":
                val[v] = z; val[v + "@"] = z
            else:
                c_ = _baku(np.column_stack(xs) @ p['w']); val[v] = c_; val[v + "@"] = c_
    return kol, val, pr_out


def rd_benar_B(par, d, T, Y, K, rng):
    pc0 = d.groupby(['strata', 'psu']).ngroup().values; npsu = pc0.max() + 1
    pc = np.concatenate([pc0 + k * npsu for k in range(K)]); w = np.tile(d.bobot.values, K)
    nz = {}
    bangkit_B(par, pc, npsu * K, rng, nz)                                  # rekam noise sekali
    p1 = bangkit_B(par, pc, npsu * K, None, nz, {T: 1}, Y)[2]
    p0 = bangkit_B(par, pc, npsu * K, None, nz, {T: 0}, Y)[2]
    return float(np.average(p1 - p0, weights=w)), float(np.average(p1, weights=w)), float(np.average(p0, weights=w))


# ================================================================== metode per replikasi
def _ukur(fn):
    t0 = BL.mulai_ukur(); hasil = fn(); dt, mem = BL.selesai_ukur(t0)
    return hasil, dt, mem


def _efek(G, d, T, Y, B, rng):
    r, _, _, _ = BL.efek_graf(G, d, T, Y, B, rng)
    return r['RD'], r.get('RD_lo', np.nan), r.get('RD_hi', np.nan)


def metode_A(dat, k, rng):
    """Semua metode skenario A pada satu data semi-sintetik. -> list baris."""
    V, T, Y, Gt, Ge, B = k['V'], k['T'], k['Y'], k['Gt'], k['Ge'], P['boot']
    tier = [C.TIER[v] for v in V]; ix = {v: i for i, v in enumerate(V)}
    baris = []

    def catat(nama, G, rd, dt, mem, takarah=(), langkah=np.nan, Gd=None):
        Gd = G if Gd is None else Gd                                  # Gd = perluasan DAG asiklik untuk SID
        baris.append(dict(metode=nama, SHD=shd(Gt, G.edges(), takarah), SID=sid(Gt, Gd), sisi=G.number_of_edges()
                          + len(takarah), RD_hat=rd[0], RD_lo=rd[1], RD_hi=rd[2], detik=dt, memori=mem,
                          langkah=langkah, tepi=tepi(Gd)))

    # B1: DAG pakar asli (tanpa penemuan)
    G1 = Ge.copy(); catat("B1 DAG pakar", G1, _efek(G1, dat, T, Y, B, rng), np.nan, np.nan)
    # B2
    def f2():
        ci = BL.UjiCI(dat, V, "campuran"); A, sep = BL.pc_skeleton(ci, len(V), C.BASELINE['alpha'], C.BASELINE['maks_kondisi'])
        return BL.orientasi(A, sep, np.array(tier))
    A, dt, mem = _ukur(f2)
    arah = [(V[i], V[j]) for i, j in itertools.permutations(range(len(V)), 2) if A[i, j] and not A[j, i]]
    und = [(V[i], V[j]) for i, j in itertools.combinations(range(len(V)), 2) if A[i, j] and A[j, i]]
    G2 = nx.DiGraph(); G2.add_nodes_from(V); G2.add_edges_from(arah)
    pa, sib, H = BL.ida_himpunan(A, ix[T])
    rds = [(0.0 if Y in [V[q] for q in h] else BL.efek(dat, T, Y, [V[q] for q in h], 0, rng)['RD'], h) for h in H]
    rd, h = min(rds, key=lambda z: abs(z[0])) if rds else (0.0, [])
    ci_ = BL.efek(dat, T, Y, [V[q] for q in h], B, rng) if (B and rds and Y not in [V[q] for q in h]) else {}
    catat("B2 PC + tier + IDA", G2, (rd, ci_.get('RD_lo', np.nan), ci_.get('RD_hi', np.nan)), dt, mem, und,
          Gd=dag_dari_cpdag(A, V))
    # B3
    (G3, jej), dt, mem = _ukur(lambda: BL.hill_climb(BL.Skor(dat, V, C.BASELINE['skor']), len(V), tier, [],
                                                      C.BASELINE['maks_induk']))
    G3 = nx.relabel_nodes(G3, dict(enumerate(V)))
    catat("B3 BN skor", G3, _efek(G3, dat, T, Y, B, rng), dt, mem, langkah=len(jej) - 1)
    # N1
    def f_n1():
        ds = N.Desain(dat)
        ci = N.UjiDesain(dat, V, C.NOVELTY['sd_uji'], ds, C.NOVELTY['sd_rs_orde'])
        A, _ = BL.pc_skeleton(ci, len(V), C.NOVELTY['sd_alpha'], C.NOVELTY['sd_maks_kondisi'])
        skel = {frozenset((i, j)) for i, j in itertools.combinations(range(len(V)), 2) if A[i, j]}
        db, nk, _ = N.deff_umum(dat, V, ds)
        sk = N.SkorW(dat, V, C.NOVELTY['sd_skor'], True, nk / db, C.NOVELTY['sd_skala'])
        return BL.hill_climb(sk, len(V), tier, [], C.NOVELTY['sd_maks_induk'], boleh=skel)
    (Gn1, jej), dt, mem = _ukur(f_n1)
    Gn1 = nx.relabel_nodes(Gn1, dict(enumerate(V)))
    catat("N1 SD-Hybrid", Gn1, _efek(Gn1, dat, T, Y, B, rng), dt, mem, langkah=len(jej) - 1)
    # N2
    def f_n2():
        n_eff = None
        if C.NOVELTY['to_berbobot']:
            db, nk, _ = N.deff_umum(dat, V, N.Desain(dat)); n_eff = nk / db
        sk = N.SkorW(dat, V, C.NOVELTY['to_skor'], C.NOVELTY['to_berbobot'], n_eff,
                     C.NOVELTY['sd_skala'] if C.NOVELTY['to_berbobot'] else 'n')
        return N.TODAG(sk, C.NOVELTY['to_maks_induk']).cari(V, tier, C.NOVELTY['to_eksak_maks'])
    (Gn2, _, _, jej), dt, mem = _ukur(f_n2)
    Gn2 = nx.relabel_nodes(Gn2, dict(enumerate(V)))
    catat("N2 TO-DAG", Gn2, _efek(Gn2, dat, T, Y, B, rng), dt, mem, langkah=len(jej))
    # SOL (tanpa lapis MLC di skenario A) + ablasi
    mA = S.bagi_psu(dat, rng); cache = {}
    for nama, o in [("SOL-DAG", dict(mlc=False, koreksi=True, tier=True, split=True)),
                    ("SOL tanpa koreksi desain", dict(mlc=False, koreksi=False, tier=True, split=True)),
                    ("SOL tanpa tier", dict(mlc=False, koreksi=True, tier=False, split=True)),
                    ("SOL tanpa pemisahan sampel", dict(mlc=False, koreksi=True, tier=True, split=False))]:
        h = S.jalankan(k['spec'], o, None, None, dat, V, B, rng, cache, mA)
        catat(nama, h['G'], (h['RD'], h['RD_lo'], h['RD_hi']), h['detik_penemuan'], h['memori_MB'], langkah=h['langkah'])
    return baris


def uji_pernyataan(dat, k):
    """H5: tolak H0 pada pernyataan independensi benar (galat tipe I) dan dependensi benar (daya uji)."""
    V = k['V']; ix = {v: i for i, v in enumerate(V)}
    naif, kor = BL.UjiCI(dat, V, "campuran"), N.UjiDesain(dat, V, "desain", None, C.NOVELTY['sd_rs_orde'])
    a = P['alpha_uji']; out = []
    for jenis, (x, y, Sx) in k['pernyataan']:
        Si = tuple(ix[s] for s in Sx)
        out.append(dict(jenis=jenis, naif=naif.p(ix[x], ix[y], Si) < a, terkoreksi=kor.p(ix[x], ix[y], Si) < a))
    return out


def pilih_pernyataan(Gt, V, rng, m):
    """Pernyataan benar dari graf benar: independensi j ⟂ i | Pa(j) (i bukan keturunan j, tak bertetangga) dan
    dependensi pasangan bertetangga (S = ∅)."""
    dsep = getattr(nx, "is_d_separator", None) or nx.d_separated
    ind = []
    for i, j in itertools.permutations(V, 2):
        if Gt.has_edge(i, j) or Gt.has_edge(j, i) or i in nx.descendants(Gt, j):
            continue
        S_ = set(Gt.predecessors(j)) - {i}
        if len(S_) <= 3 and dsep(Gt, {i}, {j}, S_):
            ind.append(("independen", (i, j, tuple(sorted(S_)))))
    dep = [("dependen", (a, b, ())) for a, b in Gt.edges()]
    pil = lambda L: [L[q] for q in rng.permutation(len(L))[:m]]
    return pil(ind) + pil(dep)


def metode_B(dat, k, rng):
    Vm, T, Y, Gt, B = k['Vm'], k['T'], k['Y'], k['Gt'], P['boot']
    cols, obs, peta = k['cols'], k['obs'], k['peta']
    baris = []

    def catat(nama, G, rd, dt, mem, langkah=np.nan):
        Gc = kolaps(G, {**peta, **{v: v for v in Vm}})
        Gc.add_nodes_from(Vm)
        baris.append(dict(metode=nama, SHD=shd(Gt, Gc.edges()),
                          SID=sid(Gt, Gc) if nx.is_directed_acyclic_graph(Gc) else np.nan, sisi=Gc.number_of_edges(),
                          RD_hat=rd[0], RD_lo=rd[1], RD_hi=rd[2], detik=dt, memori=mem, langkah=langkah, tepi=tepi(Gc)))

    tier_raw = [k['tier_raw'][c] for c in cols]
    t0 = BL.mulai_ukur(); R, biner = N.korelasi_laten(dat, cols); d_kor, m_kor = BL.selesai_ukur(t0)
    # SOL penuh dan tanpa MLC (pembagian PSU yang sama)
    mA = S.bagi_psu(dat, rng); cache = {}
    h = S.jalankan(k['spec'], S.VARIAN["SOL-DAG"], dat, obs, None, None, B, rng, cache, mA)
    catat("SOL-DAG", h['G'], (h['RD'], h['RD_lo'], h['RD_hi']), h['detik_penemuan'], h['memori_MB'], h['langkah'])
    h = S.jalankan(k['spec'], S.VARIAN["SOL tanpa MLC"], None, None, dat, cols, B, rng, cache, mA, tier_v=tier_raw)
    catat("SOL tanpa MLC", h['G'], (h['RD'], h['RD_lo'], h['RD_hi']), h['detik_penemuan'], h['memori_MB'], h['langkah'])
    # N3 dan ablasinya (penemuan pada Sigma, estimasi g-komputasi)
    def f_n3():
        m = N.bangun_mlc(dat, obs, R, biner)
        G, _ = N.temukan(m['S'], len(dat), m['Vm'], m['tier'])
        return m, nx.relabel_nodes(G, dict(enumerate(m['Vm'])))
    (m, G), dt, mem = _ukur(f_n3)
    u = pd.concat([dat, m['skor']], axis=1)
    catat("N3 MLC-DAG", G, _efek(G, u, T, Y, B, rng), dt + d_kor, max(mem, m_kor))
    (G, _), dt, mem = _ukur(lambda: N.temukan(R, len(dat), cols, tier_raw))
    G = nx.relabel_nodes(G, dict(enumerate(cols)))
    catat("N3 tanpa konstruk", G, _efek(G, dat, T, Y, B, rng), dt + d_kor, max(mem, m_kor))
    # B2 dan B3 pada indikator mentah
    def f2():
        ci = BL.UjiCI(dat, cols, "campuran"); A, sep = BL.pc_skeleton(ci, len(cols), C.BASELINE['alpha'],
                                                                     C.BASELINE['maks_kondisi'])
        return BL.orientasi(A, sep, np.array(tier_raw))
    A, dt, mem = _ukur(f2)
    G = dag_dari_cpdag(A, cols)
    catat("B2 indikator mentah", G, _efek(G, dat, T, Y, B, rng), dt, mem)
    (G, jej), dt, mem = _ukur(lambda: BL.hill_climb(BL.Skor(dat, cols, C.BASELINE['skor']), len(cols), tier_raw, [],
                                                     C.BASELINE['maks_induk']))
    G = nx.relabel_nodes(G, dict(enumerate(cols)))
    catat("B3 indikator mentah", G, _efek(G, dat, T, Y, B, rng), dt, mem, len(jej) - 1)
    return baris


# ================================================================== pekerja
def _init(konteks):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    KTX.update(konteks)


def satu(tugas):
    sken, r = tugas
    k = KTX[sken]; rng = np.random.default_rng([C.SEED, r, ord(sken)])
    t0 = time.time()
    if sken == "A":
        nz = noise_A(k['par'], len(k['pc']), k['npsu'], rng)
        X, _ = bangkit_A(k['par'], k['pc'], nz)
        dat = k['desain'].assign(**X)
        baris = metode_A(dat, k, rng)
        uji = [dict(**u, rep=r) for u in uji_pernyataan(dat, k)]
    else:
        kol, _, _ = bangkit_B(k['par'], k['pc'], k['npsu'], rng)
        dat = k['desain'].assign(**kol)
        baris = metode_B(dat, k, rng)
        uji = []
    for b in baris:
        b.update(skenario=sken, rep=r, RD_benar=k['rd'], detik_rep=time.time() - t0)
    return baris, uji


def siapkan(df, nama):
    """Konteks bersama kedua skenario (dihitung sekali di proses utama)."""
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    rng = np.random.default_rng([C.SEED, 7])
    N.MLC_DATA[0] = df
    kt, meta = {}, {}
    if "A" in P['skenario']:
        d, V, G0 = BL.siapkan(df, spec)
        tier = {v: C.TIER[v] for v in V}
        Ge = G0.subgraph(V).copy()
        Gt, hapus, tambah = perturbasi(Ge, V, tier, T, Y, P['perturbasi'], rng)
        par = fit_scm(d, Gt)
        rd, p1, p0 = rd_benar_A(par, d, T, Y, P['n_populasi'], rng)
        pc = d.groupby(['strata', 'psu']).ngroup().values
        kt["A"] = dict(spec=spec, V=V, T=T, Y=Y, Gt=Gt, Ge=Ge, par=par, rd=rd, pc=pc, npsu=pc.max() + 1,
                       desain=d[['bobot', 'strata', 'psu', 'klaster']].reset_index(drop=True),
                       pernyataan=pilih_pernyataan(Gt, V, rng, P['n_pernyataan']))
        meta["A"] = dict(node=len(V), sisi_benar=Gt.number_of_edges(), sisi_pakar=Ge.number_of_edges(),
                         dihapus=len(hapus), ditambah=len(tambah), SHD_pakar_vs_benar=shd(Gt, Ge.edges()),
                         RD_benar=rd, p1=p1, p0=p0)
        pd.DataFrame(list(Gt.edges()), columns=['dari', 'ke']).to_csv(folder(nama) / "graf_benar_A.csv", index=False)
        BL.gambar(V, Gt.edges(), [], spec, "Graf benar skenario A (DAG pakar diperturbasi)",
                  folder(nama) / "graf_benar_A.png")
    if "B" in P['skenario']:
        b = siapkan_B(df, spec, rng)
        pcB = b['d'].groupby(['strata', 'psu']).ngroup().values
        rdB, p1, p0 = rd_benar_B(b['par'], b['d'], T, Y, P['n_populasi'], rng)
        kt["B"] = dict(spec=spec, T=T, Y=Y, Vm=b['Vm'], Gt=b['Gt'], par=b['par'], peta=b['peta'], cols=b['cols'],
                       obs=b['obs'], tier_raw=b['tier_raw'], rd=rdB, pc=pcB, npsu=pcB.max() + 1,
                       desain=b['d'][['bobot', 'strata', 'psu', 'klaster']].reset_index(drop=True))
        meta["B"] = dict(node=len(b['Vm']), node_indikator=len(b['cols']), sisi_benar=b['Gt'].number_of_edges(),
                         dihapus=len(b['hapus']), ditambah=len(b['tambah']), RD_benar=rdB, p1=p1, p0=p0,
                         reflektif=b['m_real']['refl'], komposit=list(b['m_real']['komposit']),
                         dipecah=b['m_real']['pecah'])
        pd.DataFrame(list(b['Gt'].edges()), columns=['dari', 'ke']).to_csv(folder(nama) / "graf_benar_B.csv", index=False)
        BL.gambar(b['Vm'], b['Gt'].edges(), [], spec, "Graf benar skenario B (tingkat konstruk)",
                  folder(nama) / "graf_benar_B.png")
    return kt, meta


def run(df, nama="sanitasi_diare", rep=None, pekerja=None, progress=None):
    """Jalankan benchmark paralel; hasil ditulis bertahap ke hasil/benchmark/<nama>/."""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    for k, f in (("rep", int), ("pekerja", int), ("perturbasi", float), ("boot", int)):   # dari menu aplikasi
        if os.environ.get(f"BENCH_{k.upper()}"):
            P[k] = f(os.environ[f"BENCH_{k.upper()}"])
    rep = rep or P['rep']; pekerja = pekerja or P['pekerja']
    out = folder(nama)
    (out / "pid.txt").write_text(str(os.getpid()))
    for f in ("per_rep.csv", "uji_pernyataan.csv"):
        (out / f).unlink(missing_ok=True)
    t0 = time.time()
    kt, meta = siapkan(df, nama)
    meta.update(analisis=nama, rep=rep, pekerja=pekerja, konfigurasi=dict(P), mulai=time.strftime("%Y-%m-%d %H:%M"))
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    tugas = [(s, r) for s in kt for r in range(rep)]
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    selesai, galat = 0, []
    with ProcessPoolExecutor(max_workers=pekerja, initializer=_init, initargs=(kt,)) as ex:
        fut = {ex.submit(satu, t): t for t in tugas}
        for f in as_completed(fut):
            try:
                baris, uji = f.result()
                pd.DataFrame(baris).to_csv(out / "per_rep.csv", mode="a", index=False,
                                           header=not (out / "per_rep.csv").exists())
                if uji:
                    pd.DataFrame(uji).assign(skenario=fut[f][0]).to_csv(
                        out / "uji_pernyataan.csv", mode="a", index=False, header=not (out / "uji_pernyataan.csv").exists())
            except Exception as e:                                      # replikasi gagal dicatat, tidak menghentikan
                galat.append(f"{fut[f]}: {e!r}")
            selesai += 1
            (out / "progres.json").write_text(json.dumps(dict(selesai=selesai, total=len(tugas), galat=galat[-5:],
                                                              detik=time.time() - t0)), encoding="utf-8")
            if progress:
                progress(selesai, len(tugas))
    ringkas(nama)
    meta.update(selesai=time.strftime("%Y-%m-%d %H:%M"), detik=time.time() - t0, gagal=len(galat))
    (out / "pid.txt").unlink(missing_ok=True)                       # tanda "sedang berjalan" dihapus
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return [f"BENCH[{nama}] {len(tugas)} tugas ({rep} replikasi × {len(kt)} skenario), gagal={len(galat)}, "
            f"{(time.time() - t0) / 60:.1f} menit"] + baca_hipotesis(nama)


# ================================================================== ringkasan dan uji hipotesis
def _wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n; d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return c - h, c + h


def _stabil(g):
    """SHD antar-replikasi berurutan (graf yang lebih stabil -> SHD kecil)."""
    g = g.sort_values('rep'); E = [set(t.split(";")) - {""} for t in g.tepi]
    return pd.Series([len(a ^ b) for a, b in zip(E, E[1:])], index=g.rep.values[1:])


def ringkas(nama):
    out = folder(nama)
    f = out / "per_rep.csv"
    if not f.exists():
        return
    d = pd.read_csv(f)
    d['galat'] = d.RD_hat - d.RD_benar; d['abs_galat'] = d.galat.abs()
    d['cakup'] = (d.RD_lo <= d.RD_benar) & (d.RD_benar <= d.RD_hi)
    rows = []
    for (s, m), g in d.groupby(['skenario', 'metode'], sort=False):
        st = _stabil(g)
        lo, hi = _wilson(int(g.cakup.sum()), int(g.RD_lo.notna().sum()))
        rows.append(dict(skenario=s, metode=m, rep=len(g), SHD=g.SHD.mean(), SID=g.SID.mean(),
                         RMSE=np.sqrt((g.galat ** 2).mean()), bias=g.galat.mean(), sd_RD=g.RD_hat.std(),
                         efek_nol=(g.RD_hat == 0).mean(), cakupan=g.cakup.mean() if g.RD_lo.notna().any() else np.nan,
                         cakupan_lo=lo, cakupan_hi=hi, detik=g.detik.mean(), memori=g.memori.mean(),
                         stabilitas_SHD=st.mean() if len(st) else np.nan, langkah=g.langkah.mean(), sisi=g.sisi.mean()))
    pd.DataFrame(rows).to_csv(out / "ringkasan.csv", index=False)
    hipotesis(d, out)


PEMBANDING = {
    "A": dict(sol="SOL-DAG", baseline=["B1 DAG pakar", "B2 PC + tier + IDA", "B3 BN skor", "N1 SD-Hybrid", "N2 TO-DAG"],
              ablasi=["SOL tanpa koreksi desain", "SOL tanpa tier", "SOL tanpa pemisahan sampel"]),
    "B": dict(sol="SOL-DAG", baseline=["B2 indikator mentah", "B3 indikator mentah", "N3 MLC-DAG", "N3 tanpa konstruk"],
              ablasi=["SOL tanpa MLC"]),
}
HIPOTESIS = {"H1": ("Akurasi", ["SHD", "SID", "abs_galat"]), "H2": ("Kecepatan", ["detik"]),
             "H3": ("Memori", ["memori"]), "H4": ("Konvergensi & stabilitas", ["stabilitas"])}


def _wilcoxon(x, y):
    """Uji satu sisi x < y berpasangan; -> (median selisih, p)."""
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    if len(x) < 5 or np.allclose(x, y):
        return (float(np.median(x - y)) if len(x) else np.nan), 1.0
    try:
        return float(np.median(x - y)), float(stats.wilcoxon(x, y, alternative="less", zero_method="zsplit").pvalue)
    except ValueError:
        return float(np.median(x - y)), 1.0


def _holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m); run_ = 0
    for r, i in enumerate(o):
        run_ = max(run_, (m - r) * p[i]); adj[i] = min(run_, 1.0)
    return adj


def hipotesis(d, out):
    rows = []
    for s, cfg in PEMBANDING.items():
        ds = d[d.skenario == s]
        if ds.empty:
            continue
        sol = ds[ds.metode == cfg['sol']].set_index('rep')
        st_sol = _stabil(ds[ds.metode == cfg['sol']])
        for h, (judul, metrik) in HIPOTESIS.items():
            for jenis in ("baseline", "ablasi"):
                for lawan in cfg[jenis]:
                    lw = ds[ds.metode == lawan].set_index('rep')
                    if lw.empty or sol.empty:
                        continue
                    if h in ("H2", "H3", "H4") and lawan == "B1 DAG pakar":
                        continue                                       # B1 tidak menemukan graf
                    for mt in metrik:
                        if mt == "stabilitas":
                            st_l = _stabil(ds[ds.metode == lawan]); ix = st_sol.index.intersection(st_l.index)
                            x, y = st_sol[ix].values.astype(float), st_l[ix].values.astype(float)
                        else:
                            kol = {"detik": "detik", "memori": "memori"}.get(mt, mt)
                            ix = sol.index.intersection(lw.index)
                            x, y = sol.loc[ix, kol].values.astype(float), lw.loc[ix, kol].values.astype(float)
                        med, p = _wilcoxon(x, y)
                        rows.append(dict(skenario=s, hipotesis=h, aspek=judul, pembanding=lawan, jenis=jenis, metrik=mt,
                                         SOL=np.nanmean(x), lawan=np.nanmean(y), median_selisih=med, p=p, n=int(len(x))))
    hp = pd.DataFrame(rows)
    if len(hp):
        hp['p_holm'] = np.nan
        for h, g in hp.groupby('hipotesis'):
            hp.loc[g.index, 'p_holm'] = _holm(g.p.values)
        hp['keputusan'] = np.where((hp.p_holm < 0.05) & (hp.median_selisih <= 0), "SOL lebih baik",
                                   np.where(hp.SOL > hp.lawan, "SOL tidak lebih baik", "tidak berbeda bermakna"))
    # H5: validitas koreksi desain
    h5 = []
    fu = out / "uji_pernyataan.csv"
    if fu.exists():
        u = pd.read_csv(fu)
        for jenis, g in u.groupby('jenis'):
            for kol in ("naif", "terkoreksi"):
                k_, n_ = int(g[kol].sum()), len(g); lo, hi = _wilson(k_, n_)
                h5.append(dict(ukuran="galat tipe I" if jenis == "independen" else "daya uji", uji=kol,
                               nilai=k_ / n_, ci_lo=lo, ci_hi=hi, n=n_, target=P['alpha_uji'] if jenis == "independen" else np.nan))
    for s, cfg in PEMBANDING.items():
        for m in [cfg['sol']] + [x for x in cfg['ablasi'] if "koreksi" in x] + cfg['baseline']:
            g = d[(d.skenario == s) & (d.metode == m) & d.RD_lo.notna()]
            if len(g):
                k_ = int(((g.RD_lo <= g.RD_benar) & (g.RD_benar <= g.RD_hi)).sum()); lo, hi = _wilson(k_, len(g))
                h5.append(dict(ukuran=f"cakupan CI 95% (skenario {s})", uji=m, nilai=k_ / len(g), ci_lo=lo, ci_hi=hi,
                               n=len(g), target=0.95))
    h5 = pd.DataFrame(h5)
    if len(h5):
        h5['sesuai_target'] = (h5.ci_lo <= h5.target) & (h5.target <= h5.ci_hi)
    hp.to_csv(out / "hipotesis.csv", index=False)
    h5.to_csv(out / "hipotesis_H5.csv", index=False)
    # putusan ringkas per hipotesis
    put = []
    for h, (judul, _) in HIPOTESIS.items():
        g = hp[(hp.hipotesis == h) & (hp.jenis == "baseline")] if len(hp) else pd.DataFrame()
        if g.empty:
            continue
        menang = (g.keputusan == "SOL lebih baik").mean()
        put.append(dict(hipotesis=h, aspek=judul, perbandingan=len(g), SOL_lebih_baik=int((g.keputusan == "SOL lebih baik").sum()),
                        putusan="didukung" if menang == 1 else "didukung sebagian" if menang > 0 else "tidak didukung"))
    if len(h5):
        t1 = h5[(h5.ukuran == "galat tipe I")].set_index('uji')
        cak = h5[h5.ukuran.str.startswith("cakupan") & (h5.uji == "SOL-DAG")]
        ok1 = bool(len(t1) == 2 and t1.loc['terkoreksi', 'sesuai_target'] and t1.loc['naif', 'ci_lo'] > P['alpha_uji'])
        ok2 = bool(len(cak) and cak.sesuai_target.all())
        put.append(dict(hipotesis="H5", aspek="Validitas koreksi desain", perbandingan=2,
                        SOL_lebih_baik=int(ok1) + int(ok2),
                        putusan="didukung" if ok1 and ok2 else "didukung sebagian" if ok1 or ok2 else "tidak didukung"))
    pd.DataFrame(put).to_csv(out / "putusan.csv", index=False)


def baca_hipotesis(nama):
    f = folder(nama) / "putusan.csv"
    if not f.exists():
        return []
    return [f"BENCH[{nama}] {r.hipotesis} {r.aspek}: {r.putusan} ({r.SOL_lebih_baik}/{r.perbandingan})"
            for r in pd.read_csv(f).itertuples()]


# ================================================================== evaluasi benchmark v2 (pra-registrasi)
V2_DIR = C.ROOT / "v2"


def _baca_ringkasan_v2():
    """Galat tipe I dan daya uji per sel dari RINGKASAN_v2.txt (satu-satunya tempat sol_v2 menyimpannya)."""
    import re
    f = V2_DIR / "RINGKASAN_v2.txt"
    if not f.exists():
        return {}
    kal = {}
    for blok in f.read_text(encoding="utf-8").split("\n\n"):
        m = re.search(r"'icc': ([\d.]+), 'beta_ty': ([-\d.]+)", blok)
        c = re.search(r"tipe I naif ([\d.]+)% desain ([\d.]+)% \| daya naif ([\d.]+)% desain ([\d.]+)%", blok)
        if m and c:
            kal[(float(m[1]), float(m[2]))] = dict(t1_naif=float(c[1]) / 100, t1_desain=float(c[2]) / 100,
                                                   daya_naif=float(c[3]) / 100, daya_desain=float(c[4]) / 100)
    return kal


def evaluasi_v2():
    """-> (tabel sel, tabel hipotesis) menurut kriteria PRAREGISTRASI_v2.md. n pernyataan per sel diasumsikan
    20 × replikasi (ci_calibration mengisi hingga 20 pernyataan per jenis per replikasi)."""
    sel = []
    for f in sorted(V2_DIR.glob("hasil_*_*.csv")):
        icc, beta = map(float, f.stem.split("_")[1:3])
        d = pd.read_csv(f)
        for v, g in d.groupby("varian"):
            sel.append(dict(icc=icc, beta_ty=beta, varian=v, rep=len(g), SHD=g.shd.mean(),
                            RMSE=np.sqrt((g.err ** 2).mean()), cakupan=g.cover.mean(), efek_nol=g.nol.mean(),
                            detik=g.detik.mean(), MB=g.mb.mean()))
    sel = pd.DataFrame(sel)
    if sel.empty:
        return sel, pd.DataFrame()
    kal = _baca_ringkasan_v2(); reps = int(sel.rep.max())
    for k, v in (("t1_naif", "t1_naif"), ("t1_desain", "t1_desain"), ("daya_naif", "daya_naif"), ("daya_desain", "daya_desain")):
        sel[k] = [kal.get((r.icc, r.beta_ty), {}).get(v, np.nan) for r in sel.itertuples()]
    hp = []
    # H1v2: efek nol 0% dan cakupan >= 85% di semua sel efek != 0 (varian v2 desain); gagal bila < 80% di salah satu
    s = sel[(sel.varian == "v2 desain") & (sel.beta_ty != 0)]
    ok = bool(len(s) and (s.efek_nol == 0).all() and (s.cakupan >= .85).all()); gagal = bool((s.cakupan < .80).any())
    hp.append(dict(kode="H1v2", hipotesis="Estimasi sadar-query memulihkan efek",
                   hasil="; ".join(f"ICC {r.icc} β {r.beta_ty}: cakupan {r.cakupan:.1%}, efek nol {r.efek_nol:.1%}"
                                   for r in s.itertuples()),
                   putusan="diterima" if ok else "gagal" if gagal else "tidak tegas (80–85%)"))
    # H2v2: RMSE v2 < v1 pada beta -0,15 (Wilcoxon satu sisi berpasangan per replikasi, Holm antar-ICC)
    pv, teks, lebih_kecil = [], [], []
    for f in sorted(V2_DIR.glob("hasil_*_-0.15.csv")):
        d = pd.read_csv(f); icc = float(f.stem.split("_")[1])
        a = d[d.varian == "v2 desain"].set_index("rep").err; b = d[d.varian == "v1 aturan lama"].set_index("rep").err
        ix = a.index.intersection(b.index)
        med, p = _wilcoxon(a[ix].values, b[ix].values)          # |galat| per replikasi, berpasangan
        r2, r1 = np.sqrt((a[ix] ** 2).mean()), np.sqrt((b[ix] ** 2).mean())
        pv.append(p); lebih_kecil.append(r2 < r1)
        teks.append(f"ICC {icc}: RMSE v2 {r2:.4f} vs v1 {r1:.4f} ({'lebih kecil' if r2 < r1 else 'TIDAK lebih kecil'})")
    if pv:
        ph = _holm(pv)
        hp.append(dict(kode="H2v2", hipotesis="v2 lebih akurat daripada aturan v1 pada efek kecil",
                       hasil="; ".join(f"{t} (p Holm {q:.2g})" for t, q in zip(teks, ph)),
                       putusan="diterima" if ((ph < .05) & np.array(lebih_kecil)).all() else "gagal"))
        # kriteria pra-registrasi: RMSE v2 < v1 DAN Wilcoxon satu sisi (Holm) p < 0,05 di setiap sel beta -0,15
    # H3v2-H6v2 pada ICC 0,4 (digabung antar-sel ICC 0,4; per sel ditampilkan di tabel sel)
    k4 = [v for (icc, b), v in kal.items() if icc == 0.4]
    if k4:
        n = 20 * reps * len(k4)
        t1d = np.mean([v['t1_desain'] for v in k4]); t1n = np.mean([v['t1_naif'] for v in k4])
        lo, hi = _wilson(round(t1d * n), n)
        hp.append(dict(kode="H3v2", hipotesis="Uji desain terkalibrasi (ICC 0,4)",
                       hasil=f"galat tipe I desain {t1d:.1%} (Wilson {lo:.1%}–{hi:.1%}, n≈{n})",
                       putusan="diterima" if (.025 <= t1d <= .075 and hi <= .09) else "gagal"))
        hp.append(dict(kode="H4v2", hipotesis="Uji naif tidak terkalibrasi (ICC 0,4)",
                       hasil=f"galat tipe I naif {t1n:.1%}", putusan="diterima" if t1n > .10 else "gagal"))
    if kal:
        dd = np.mean([v['daya_desain'] for v in kal.values()]); dn = np.mean([v['daya_naif'] for v in kal.values()])
        hp.append(dict(kode="H5v2", hipotesis="Kehilangan daya uji terbatas",
                       hasil=f"daya desain {dd:.1%} vs naif {dn:.1%} (selisih {100 * (dd - dn):+.1f} pp, semua sel)",
                       putusan="diterima" if dd >= dn - .05 else "gagal"))
    s4 = sel[sel.icc == 0.4].pivot_table(index="beta_ty", columns="varian", values="SHD")
    if {"v2 desain", "v2 naif"} <= set(s4.columns):
        sd = sel[(sel.icc == 0.4) & (sel.varian == "v2 desain")].SHD.mean()
        sn = sel[(sel.icc == 0.4) & (sel.varian == "v2 naif")].SHD.mean()
        hp.append(dict(kode="H6v2", hipotesis="Akurasi struktur tidak lebih buruk (ICC 0,4)",
                       hasil=f"SHD desain {sd:.2f} vs naif {sn:.2f} (selisih {sd - sn:+.2f})",
                       putusan="diterima" if sd <= sn + 1 else "gagal"))
    return sel, pd.DataFrame(hp)


# ================================================================== evaluasi v3 (pra-registrasi S6-S10)
V3_DIR = C.ROOT / "v3"
TAFSIR_V3 = ("Tafsiran bagian ambigu: H8a, H8b, H8d pada skenario heterogen (inti S8); H8c gabungan kedua skenario; "
             "H7a heterogen seperti tertulis; H7b dan H9 memakai skenario heterogen sebagai utama (homogen dilaporkan); "
             "H9 pada uji desain_usulan, p = 15.")


def evaluasi_v3():
    """-> (tabel kalibrasi S8, tabel hilir, tabel hipotesis) menurut PRAREGISTRASI_v3.md."""
    f8, f15 = V3_DIR / "hasil_S8.csv", V3_DIR / "hasil_downstream_p15.csv"
    kal, hil, hp = pd.DataFrame(), pd.DataFrame(), []
    if f8.exists():
        s8 = pd.read_csv(f8); uji = ["naif", "kish", "deff_global", "sandwich_CR1", "desain_usulan"]
        rows = []
        for sc, g in s8.groupby("skenario"):
            h0, h1 = g[g.indep], g[~g.indep]
            for t in uji:
                k_ = int(h0[t].sum()); lo, hi = _wilson(k_, len(h0))
                rows.append(dict(skenario=sc, uji=t, tipeI=k_ / len(h0), wilson_lo=lo, wilson_hi=hi, n_H0=len(h0),
                                 daya=h1[t].mean(), n_H1=len(h1)))
        kal = pd.DataFrame(rows); k = kal.set_index(["skenario", "uji"])
        he = "heterogen"
        t1 = k.loc[(he, "desain_usulan"), "tipeI"]
        hp.append(dict(kode="H8a", hipotesis="Uji desain terkalibrasi pada deff heterogen",
                       hasil=f"galat tipe I {t1:.1%} (Wilson {k.loc[(he, 'desain_usulan'), 'wilson_lo']:.1%}–"
                             f"{k.loc[(he, 'desain_usulan'), 'wilson_hi']:.1%})",
                       putusan="diterima" if .025 <= t1 <= .075 else "gagal"))
        n_, ki, dg = (k.loc[(he, u), "tipeI"] for u in ("naif", "kish", "deff_global"))
        hp.append(dict(kode="H8b", hipotesis="Pembanding lazim salah kalibrasi",
                       hasil=f"naif {n_:.1%}, Kish {ki:.1%} (> 10%?); deff-global {dg:.1%} (< 2,5%?)",
                       putusan="diterima" if (n_ > .10 and ki > .10 and dg < .025) else "gagal"))
        h0 = s8[s8.indep]; same = (h0.sandwich_CR1 == h0.desain_usulan).mean()
        per = "; ".join(f"{sc} {(g.sandwich_CR1 == g.desain_usulan).mean():.1%}" for sc, g in h0.groupby("skenario"))
        hp.append(dict(kode="H8c", hipotesis="Uji desain setara sandwich CR1",
                       hasil=f"kesepakatan keputusan pada H0 {same:.1%} ({per})",
                       putusan="diterima → klaim 'uji baru' DICABUT" if same >= .99 else "gagal (uji berbeda dari CR1)"))
        dd = k.loc[(he, "desain_usulan"), "daya"] - k.loc[(he, "deff_global"), "daya"]
        hp.append(dict(kode="H8d", hipotesis="Daya uji desain > deff-global",
                       hasil=f"daya desain {k.loc[(he, 'desain_usulan'), 'daya']:.1%} vs deff-global "
                             f"{k.loc[(he, 'deff_global'), 'daya']:.1%} (selisih {100 * dd:+.1f} pp)",
                       putusan="diterima" if dd >= .05 else "gagal"))
    if f15.exists():
        ds = pd.read_csv(f15)
        hil = ds.groupby(["skenario", "uji"]).agg(SHD=("SHD", "mean"), presisi=("presisi", "mean"),
                                                  recall=("recall", "mean"), FDR=("FDR", "mean"),
                                                  adj_valid=("adj_valid", "mean"),
                                                  RMSE=("err", lambda e: np.sqrt((e ** 2).mean())),
                                                  cakupan=("cover", "mean"), cakupan_gabungan=("cover_union", "mean"),
                                                  detik=("detik", "mean"), MB=("MB", "mean")).reset_index()
        pv = lambda sc, m, a, b, alt: _wilcoxon_alt(ds, sc, m, a, b, alt)
        he = ds[ds.skenario == "heterogen"]
        pa = [pv("heterogen", "adj_valid", "desain_usulan", l, "greater") for l in ("naif", "kish")]
        ph = _holm([p for _, p in pa])
        mv = lambda sc, u, m: ds[(ds.skenario == sc) & (ds.uji == u)][m].mean()
        hp.append(dict(kode="H7a", hipotesis="Validitas himpunan penyesuaian desain ≥ naif dan Kish (heterogen)",
                       hasil=f"desain {mv('heterogen', 'desain_usulan', 'adj_valid'):.1%} vs naif "
                             f"{mv('heterogen', 'naif', 'adj_valid'):.1%} (p Holm {ph[0]:.2g}), Kish "
                             f"{mv('heterogen', 'kish', 'adj_valid'):.1%} (p Holm {ph[1]:.2g})",
                       putusan="diterima" if (ph < .05).all() else "gagal"))
        pb = [pv(sc, "FDR", "desain_usulan", "naif", "less") for sc in ("heterogen", "homogen")]
        phb = _holm([p for _, p in pb])
        hp.append(dict(kode="H7b", hipotesis="FDR sisi desain < naif",
                       hasil="; ".join(f"{sc}: {mv(sc, 'desain_usulan', 'FDR'):.3f} vs {mv(sc, 'naif', 'FDR'):.3f} "
                                       f"(p Holm {q:.2g})" for sc, q in zip(("heterogen", "homogen"), phb)),
                       putusan="diterima" if phb[0] < .05 else "gagal"))
        cu = {sc: (mv(sc, "desain_usulan", "cover_union"), mv(sc, "desain_usulan", "cover")) for sc in ("heterogen", "homogen")}
        hp.append(dict(kode="H9", hipotesis="Cakupan CI (uji desain, p = 15)",
                       hasil="; ".join(f"{sc}: gabungan {g:.1%}, utama {u:.1%}" for sc, (g, u) in cu.items()),
                       putusan="diterima" if (cu["heterogen"][0] >= .94 and cu["heterogen"][1] >= .92) else "gagal"))
    return kal, hil, pd.DataFrame(hp)


def _wilcoxon_alt(ds, sc, metrik, a, b, alt):
    """Wilcoxon berpasangan per replikasi a vs b; alt 'greater' (a > b) atau 'less' (a < b). -> (median, p)."""
    g = ds[ds.skenario == sc]
    x = g[g.uji == a].set_index("rep")[metrik]; y = g[g.uji == b].set_index("rep")[metrik]
    ix = x.index.intersection(y.index); x, y = x[ix].values.astype(float), y[ix].values.astype(float)
    if len(x) < 5 or np.allclose(x, y):
        return float(np.median(x - y)) if len(x) else np.nan, 1.0
    try:
        return float(np.median(x - y)), float(stats.wilcoxon(x, y, alternative=alt, zero_method="zsplit").pvalue)
    except ValueError:
        return float(np.median(x - y)), 1.0
