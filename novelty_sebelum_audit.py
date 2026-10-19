"""MENU N1-N3: KANDIDAT KEBARUAN (dokumen Tahap 3). Semuanya hipotesis desain yang belum teruji;
perbandingan pada data nyata IDHS bukan bukti keunggulan (perlu evaluasi semi-sintetik).
  N1 SD-Hybrid : uji Rao-Scott / t-desain + skor pseudo-likelihood berbobot (penalti log n_eff)
                 -> skeleton PC terkoreksi -> Hill-Climbing di dalam skeleton, patuh tier
  N2 TO-DAG    : pencarian urutan di dalam tier + grow-shrink + cache skor
  N3 MLC-DAG   : korelasi tetrakorik berbobot -> model satu-faktor + purifikasi tetrad
                 -> kovarians konstruk terkoreksi galat ukur -> penemuan struktur pada Sigma_V
Langkah estimasi efek sama dengan baseline: adjustment set backdoor -> g-komputasi berbobot -> bootstrap PSU."""
import itertools
import math
import time
import warnings
import numpy as np
import pandas as pd
import networkx as nx
from scipy import stats, optimize
from scipy.special import gammaln
import config_old as C
import baseline as BL

warnings.filterwarnings("ignore")
P = C.NOVELTY
METODE = {
    "sd_hybrid": dict(kode="N1", nama="SD-Hybrid", judul="Survey-Design-Consistent Hybrid Discovery",
                      kriteria={'BIC_SEM': True, 'CFI': False, 'lebar_CI': True}),
    "to_dag": dict(kode="N2", nama="TO-DAG", judul="Tier-Ordered DAG Search",
                   kriteria={'detik_penemuan': True, 'memori_MB': True, 'BIC_SEM': True}),
    "mlc_dag": dict(kode="N3", nama="MLC-DAG", judul="Multidimensional Latent-Construct DAG",
                    kriteria={'detik_penemuan': True, 'memori_MB': True, 'lebar_CI': True}),
}


def folder(metode, nama):
    out = C.OUT / "novelty" / metode / nama
    out.mkdir(parents=True, exist_ok=True)
    return out


# ================================================================== desain survei
class Desain:
    """Struktur PSU-dalam-strata untuk varians linearisasi Taylor: Var = sum_h n_h/(n_h-1) sum_c (u_hc - u_h)^2."""

    def __init__(self, d):
        self.pc = d.groupby(['strata', 'psu']).ngroup().values
        self.npsu = self.pc.max() + 1
        ps = pd.DataFrame({'pc': self.pc, 'h': d.strata.values}).drop_duplicates('pc').sort_values('pc')
        self.h = pd.factorize(ps.h)[0]
        self.nh = np.bincount(self.h)
        self.fak = np.where(self.nh > 1, self.nh / np.maximum(self.nh - 1, 1), 0.0)[self.h]
        self.df = int(self.npsu - len(self.nh))                 # df desain = #PSU - #strata

    def var_total(self, Z, idx=None):
        """Varians desain dari total sum_k z_k untuk tiap kolom Z (Z sudah berisi w_k * psi_k / W)."""
        Z = np.atleast_2d(Z.T).T
        pc = self.pc if idx is None else self.pc[idx]
        T = np.column_stack([np.bincount(pc, weights=Z[:, k], minlength=self.npsu) for k in range(Z.shape[1])])
        M = np.column_stack([np.bincount(self.h, weights=T[:, k], minlength=len(self.nh))
                             for k in range(Z.shape[1])]) / self.nh[:, None]
        return (self.fak[:, None] * (T - M[self.h]) ** 2).sum(0)


def deff_umum(d, V, ds):
    """delta_bar = rerata design effect (klaster) rerata berbobot atas V; n_Kish = (sum w)^2 / sum w^2."""
    w = d.bobot.values; W = w.sum()
    n_kish = W ** 2 / (w ** 2).sum()
    X = d[V].astype(float).values
    m = w @ X / W
    var_des = ds.var_total(w[:, None] * (X - m) / W)
    var_w = (w[:, None] * (X - m) ** 2).sum(0) / W / n_kish
    dv = var_des / np.where(var_w > 0, var_w, np.nan)
    return float(np.nanmean(dv)), float(n_kish), pd.Series(dv, index=V)


class UjiDesain:
    """Uji independensi bersyarat konsisten desain (antarmuka sama dengan baseline.UjiCI).
    Kategorik: Rao-Scott orde 1 atau 2 dari eigenvalue matriks design effect D = V_SRS^-1 V_desain.
    Kontinu/campuran: t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU)."""

    def __init__(self, d, V, jenis="desain", ds=None, orde=2):
        X = d[V].astype(float).values
        self.X, self.n, self.jenis, self.orde, self.jumlah = X, len(X), jenis, orde, 0
        self.w = d.bobot.values / d.bobot.values.mean()
        self.ds = ds or Desain(d)
        self.kode, self.k = {}, {}
        for i in range(len(V)):
            u, c = np.unique(X[:, i], return_inverse=True)
            if len(u) <= C.BASELINE['maks_kategori']:
                self.kode[i], self.k[i] = c, len(u)

    def p(self, i, j, S):
        self.jumlah += 1
        if self.jenis == "desain" and all(v in self.kode for v in (i, j, *S)):
            return self.rao_scott(i, j, S)
        return self.t_desain(i, j, S)

    def t_desain(self, i, j, S):
        """Korelasi parsial berbobot; SE dari fungsi pengaruh psi = ab - r(a^2+b^2)/2 dilinearisasi per PSU."""
        w, X = self.w, self.X
        Yij = X[:, [i, j]]
        if S:
            A = np.column_stack([np.ones(self.n), X[:, list(S)]]); sw = np.sqrt(w)[:, None]
            E = Yij - A @ np.linalg.lstsq(A * sw, Yij * sw, rcond=None)[0]
        else:
            E = Yij - w @ Yij / w.sum()
        sd = np.sqrt((w[:, None] * E ** 2).sum(0) / w.sum())
        if np.any(sd == 0):
            return 1.0
        a, b = E[:, 0] / sd[0], E[:, 1] / sd[1]
        r = (w * a * b).sum() / w.sum()
        psi = a * b - r * (a ** 2 + b ** 2) / 2
        se = np.sqrt(self.ds.var_total(w * psi / w.sum())[0])
        return 1.0 if se == 0 else 2 * stats.t.sf(abs(r / se), self.ds.df)

    def _if_kontras(self, idx, ci, cj, ra, rb, w):
        """Fungsi pengaruh kontras interaksi z_ab = p_ab - p_a p_b (a, b tanpa level terakhir) pada satu domain."""
        W = w.sum()
        la, lb = np.flatnonzero(ra), np.flatnonzero(rb)
        pab = np.array([[np.sum(w * ((ci == a) & (cj == b))) for b in lb] for a in la]) / W
        pa, pb = pab.sum(1), pab.sum(0)
        kol = []
        for x, a in enumerate(la[:-1]):
            for y, b in enumerate(lb[:-1]):
                ia, ib = (ci == a).astype(float), (cj == b).astype(float)
                kol.append(w * ((ia * ib - pab[x, y]) - pb[y] * (ia - pa[x]) - pa[x] * (ib - pb[y])) / W)
        return np.column_stack(kol), pab, pa, pb

    def rao_scott(self, i, j, S, orde=None):
        """X2_w = sum_s n_s sum_ab (p_ab|s - p_a|s p_b|s)^2 / (p_a|s p_b|s); delta_k = eigenvalue D.
        Orde 1: X2_w / delta_bar ~ chi2_df. Orde 2: X2_w / (delta_bar (1 + a^2)) ~ chi2_{df/(1+a^2)},
        a^2 = koefisien variasi kuadrat eigenvalue."""
        orde = orde or self.orde
        ki, kj, w = self.k[i], self.k[j], self.w
        s = np.zeros(self.n, dtype=np.int64)
        for v in S:
            s = s * self.k[v] + self.kode[v]
        s = np.unique(s, return_inverse=True)[1]
        x2, blok_des, blok_srs = 0.0, [], []
        for c in range(s.max() + 1):
            idx = np.flatnonzero(s == c)
            if len(idx) < 20:
                continue
            ci, cj = self.kode[i][idx], self.kode[j][idx]
            ra = np.bincount(ci, minlength=ki) > 0; rb = np.bincount(cj, minlength=kj) > 0
            if ra.sum() < 2 or rb.sum() < 2:
                continue
            Zw, pab, pa, pb = self._if_kontras(idx, ci, cj, ra, rb, w[idx])
            E = np.outer(pa, pb)
            x2 += len(idx) * ((pab - E) ** 2 / np.maximum(E, 1e-12)).sum()
            Zs, *_ = self._if_kontras(idx, ci, cj, ra, rb, np.ones(len(idx)))
            full = np.zeros((self.n, Zw.shape[1])); full[idx] = Zw
            blok_des.append(full)
            blok_srs.append((Zs.T @ Zs) * len(idx) / max(len(idx) - 1, 1))
        if not blok_des:
            return 1.0
        Zd = np.hstack(blok_des)
        T = np.column_stack([np.bincount(self.ds.pc, weights=Zd[:, k], minlength=self.ds.npsu)
                             for k in range(Zd.shape[1])])
        M = np.column_stack([np.bincount(self.ds.h, weights=T[:, k], minlength=len(self.ds.nh))
                             for k in range(T.shape[1])]) / self.ds.nh[:, None]
        Dv = T - M[self.ds.h]
        V_des = (self.ds.fak[:, None] * Dv).T @ Dv
        V_srs = np.zeros_like(V_des); o = 0
        for b in blok_srs:
            V_srs[o:o + len(b), o:o + len(b)] = b; o += len(b)
        delta = np.real(np.linalg.eigvals(np.linalg.pinv(V_srs) @ V_des))
        delta = np.clip(delta, 1e-6, None); df = len(delta)
        dbar = max(delta.mean(), 0.05)
        if orde == 1:
            return stats.chi2.sf(x2 / dbar, df)
        a2 = ((delta - dbar) ** 2).sum() / (df * dbar ** 2)
        return stats.chi2.sf(x2 / (dbar * (1 + a2)), df / (1 + a2))


class SkorW(BL.Skor):
    """Skor struktur konsisten desain: pseudo-log-likelihood berbobot dengan penalti (k_j/2) log n_eff.
    skala='n_eff' (disarankan): likelihood juga diskalakan ke n_eff sehingga fit dan penalti berada pada skala
    sampel efektif yang sama (setara BIC desain); skala='n': likelihood dinormalisasi ke n seperti rumusan awal.
    berbobot=False & n_eff=n -> identik dengan skor baseline B3."""

    def __init__(self, d, V, jenis, berbobot=True, n_eff=None, skala="n_eff"):
        super().__init__(d, V, "bic" if jenis == "gauss" else jenis)   # kode diskret dari baseline
        self.jenis, self.skala = jenis, skala
        self.n_pen = n_eff or len(d)
        self.n_lik = self.n_pen if skala == "n_eff" else len(d)
        w = d.bobot.values.astype(float) if berbobot else np.ones(len(d))
        self.w = w * self.n_lik / w.sum()
        if jenis == "gauss":
            X = d[V].astype(float).values
            m = self.w @ X / self.n_lik; sd = np.sqrt(self.w @ (X - m) ** 2 / self.n_lik)
            Z = (X - m) / np.where(sd > 0, sd, 1)
            self.S = (Z * self.w[:, None]).T @ Z / self.n_lik

    def _hitung(self, j, pa):
        n, lp = self.n_lik, np.log(self.n_pen)
        if self.jenis == "gauss":
            s2 = self.S[j, j] - (self.S[j, pa] @ np.linalg.solve(self.S[np.ix_(pa, pa)], self.S[pa, j]) if pa else 0)
            return -n / 2 * np.log(2 * np.pi * max(s2, 1e-12)) - n / 2 - (len(pa) + 2) / 2 * lp
        R = self.k[j]; Q = float(np.prod([self.k[v] for v in pa])) if pa else 1.0
        q = np.zeros(self.n, dtype=np.int64)
        for v in pa:
            q = q * self.k[v] + self.kode[v]
        q = np.unique(q, return_inverse=True)[1]
        N = np.bincount(q * R + self.kode[j], weights=self.w, minlength=(q.max() + 1) * R).reshape(-1, R)
        Nq = N.sum(1)
        if self.jenis == "bdeu":
            a = C.BASELINE['ess']
            return ((gammaln(a / Q) - gammaln(a / Q + Nq)).sum()
                    + (gammaln(a / (Q * R) + N) - gammaln(a / (Q * R))).sum())
        xlx = lambda M: np.where(M > 0, M * np.log(np.where(M > 0, M, 1)), 0).sum()
        return xlx(N) - xlx(Nq) - (R - 1) * Q / 2 * lp


class SkorKov(BL.Skor):
    """Skor Gauss dari matriks kovarians saja (statistik cukup), untuk MLC-DAG."""

    def __init__(self, S, n):
        self.jenis, self.S, self.n, self.cache = "gauss", S, n, {}


class UjiKov:
    """Fisher z dari matriks korelasi saja (statistik cukup)."""

    def __init__(self, R, n):
        self.R, self.n, self.jumlah = R, n, 0

    def p(self, i, j, S):
        self.jumlah += 1
        idx = [i, j, *S]
        Q = np.linalg.pinv(self.R[np.ix_(idx, idx)])
        r = np.clip(-Q[0, 1] / np.sqrt(Q[0, 0] * Q[1, 1]), -0.999999, 0.999999)
        return 2 * stats.norm.sf(abs(0.5 * np.sqrt(self.n - len(S) - 3) * np.log((1 + r) / (1 - r))))


# ================================================================== bersama
def banding_baseline(nama, metode, baris_n, d, V, out):
    """Gabungkan baris novelty dengan B1-B3 (hasil/baseline/<nama>/rangkuman.csv), lalu peringkat
    dengan kriteria yang dijanjikan kandidat. B1 tidak menemukan graf -> dikecualikan dari kriteria waktu/memori."""
    f = C.OUT / "baseline" / nama / "rangkuman.csv"
    base = pd.read_csv(f) if f.exists() else pd.DataFrame(columns=['kode', 'metode', 'RD', 'RD_lo', 'RD_hi'])
    base = base.drop(columns=[c for c in base if c.startswith('rank_')] + ['peringkat_rata2', 'terbaik'],
                     errors='ignore')
    rows = []
    for b in baris_n:
        if d is not None and b.get('edges') is not None:
            Ge = nx.DiGraph(); Ge.add_nodes_from(V); Ge.add_edges_from(b['edges'])
            ft = BL.fit_graf(d, V, Ge)
            b = {**b, 'BIC_SEM': ft['BIC_SEM'], 'CFI': ft['CFI'], 'RMSEA': ft['RMSEA']}
        rows.append({k: v for k, v in b.items() if k != 'edges'})
    tab = pd.concat([base, pd.DataFrame(rows)], ignore_index=True)
    tab['lebar_CI'] = (tab.RD_hi - tab.RD_lo).where(lambda x: x > 0)
    krit = METODE[metode]['kriteria']
    tab = peringkat(tab, krit)
    tab.to_csv(out / "banding.csv", index=False)
    sp = C.ANALISIS[nama]
    BL.forest(tab.assign(RD_lo=tab.RD_lo.fillna(tab.RD), RD_hi=tab.RD_hi.fillna(tab.RD)), sp['T'], sp['Y'],
              out / "banding.png")
    b = tab[tab.terbaik].iloc[0]
    return (f"banding: terbaik={b.metode} (peringkat {b.peringkat_rata2:.2f}) | "
            + " | ".join(f"{r.kode} " + " ".join(f"{k}={getattr(r, k):.3g}" for k in krit) for r in tab.itertuples()))


def peringkat(tab, krit):
    """Peringkat per kriteria; nilai kosong (mis. tanpa CI karena efek 0) = peringkat terbawah.
    Bila kriteria memuat waktu/memori, B1 (tanpa penemuan graf) tidak ikut diperingkat."""
    tab = tab.drop(columns=[c for c in tab if c.startswith('rank_')] + ['peringkat_rata2', 'terbaik'], errors='ignore')
    ikut = ~((tab.kode == 'B1') & any(k in ('detik_penemuan', 'memori_MB') for k in krit))
    for k, asc in krit.items():
        if k not in tab:
            tab[k] = np.nan
        tab[f'rank_{k}'] = tab.loc[ikut, k].rank(ascending=asc, method='min', na_option='bottom')
    tab['peringkat_rata2'] = tab.filter(like='rank_').mean(axis=1).where(ikut)
    tab['terbaik'] = tab.peringkat_rata2 == tab.peringkat_rata2.min()
    return tab


def rangking_ulang():
    """Hitung ulang peringkat semua banding.csv yang ada (tanpa menjalankan metode lagi)."""
    for m, M in METODE.items():
        for f in (C.OUT / "novelty" / m).glob("*/banding.csv"):
            peringkat(pd.read_csv(f), M['kriteria']).to_csv(f, index=False)


def baris_n(kode, metode, r, edges, **kw):
    return dict(kode=kode, metode=metode, RD=r['RD'], RD_lo=r.get('RD_lo', np.nan), RD_hi=r.get('RD_hi', np.nan),
                edges=edges, sisi=len(edges), **kw)


def simpan_dag(out, pre, Gb, V, spec, judul, Ge):
    pd.DataFrame(list(Gb.edges()), columns=['dari', 'ke']).to_csv(out / f"{pre}_dag.csv", index=False)
    BL.gambar(V, Gb.edges(), [], spec, judul, out / f"{pre}_graf.png")
    return BL.banding(list(Gb.edges()), [], Ge) if Ge is not None else {}


# ================================================================== N1 SD-Hybrid
def sd_hybrid(d, V, G, spec, out, B, rng):
    T, Y = spec['T'], spec['Y']; t_all = time.time()
    tier = [C.TIER[v] for v in V]
    tu = BL.mulai_ukur()
    ds = Desain(d)
    ci = UjiDesain(d, V, P['sd_uji'], ds, P['sd_rs_orde'])
    A, sep = BL.pc_skeleton(ci, len(V), P['sd_alpha'], P['sd_maks_kondisi'])
    skel = {frozenset((i, j)) for i, j in itertools.combinations(range(len(V)), 2) if A[i, j]}
    dbar, n_kish, dv = deff_umum(d, V, ds)
    n_eff = n_kish / dbar
    sk = SkorW(d, V, P['sd_skor'], True, n_eff, P['sd_skala'])
    Gi, jejak = BL.hill_climb(sk, len(V), tier, [], P['sd_maks_induk'], boleh=skel)
    dp, mem = BL.selesai_ukur(tu)
    Gb = nx.relabel_nodes(Gi, dict(enumerate(V)))
    jejak['operasi'] = jejak.operasi.str.replace(r'(\d+)->(\d+)', lambda m: f"{V[int(m[1])]} -> {V[int(m[2])]}",
                                                 regex=True)
    jejak.to_csv(out / "sd_jejak.csv", index=False)
    pd.DataFrame([(V[min(p)], V[max(p)]) for p in skel], columns=['a', 'b']).to_csv(out / "sd_skeleton.csv",
                                                                                     index=False)
    dv.rename('deff').rename_axis('variabel').to_csv(out / "sd_deff.csv")
    bd = simpan_dag(out, "sd", Gb, V, spec, f"N1 SD-Hybrid (α={P['sd_alpha']}, skor s_w {P['sd_skor']})",
                    G.subgraph(V))
    r, Z, ok, cat = BL.efek_graf(Gb, d, T, Y, B, rng)
    f2 = C.OUT / "baseline" / spec_nama(spec) / "b2_info.csv"
    naif = pd.read_csv(f2, index_col=0).nilai if f2.exists() else None
    BL.info(out / "sd_info.csv", n=len(d), uji=P['sd_uji'], alpha=P['sd_alpha'], jumlah_uji=ci.jumlah,
            sisi_skeleton=len(skel), sisi_skeleton_B2_naif=(int(naif['sisi']) if naif is not None else '-'),
            delta_bar=round(dbar, 3), n_Kish=round(n_kish, 1), n_eff=round(n_eff, 1), df_desain=ds.df,
            rao_scott_orde=P['sd_rs_orde'], skala_skor=P['sd_skala'], skor=P['sd_skor'], langkah=len(jejak) - 1, skor_akhir=round(jejak.skor.iloc[-1], 2),
            adjustment=', '.join(Z) or '-', catatan=cat or '-', **bd,
            detik_penemuan=round(dp, 2), memori_MB=round(mem, 2), detik=round(time.time() - t_all, 1))
    rows = [baris_n('N1', 'N1 SD-Hybrid', r, list(Gb.edges()), SHD=bd['SHD'], detik_penemuan=dp,
                    memori_MB=mem, catatan=f"skeleton {len(skel)} sisi; n_eff={n_eff:.0f}" + (f"; {cat}" if cat else ""))]
    lines = [f"N1 SD-Hybrid uji={ci.jumlah} skeleton={len(skel)} (B2 naif "
             f"{naif['sisi'] if naif is not None else '-'}) delta_bar={dbar:.2f} n_eff={n_eff:.0f} sisi={bd['sisi']}"
             f" SHD={bd['SHD']} RD={r['RD']:+.4f} [{r.get('RD_lo', np.nan):+.4f},{r.get('RD_hi', np.nan):+.4f}]"]
    return rows, lines


def spec_nama(spec):
    return next(n for n, s in C.ANALISIS.items() if s is spec)


def simulasi_uji(d, rep, icc, efek=(0.0, 0.05, 0.10), alpha=0.05, rng=None):
    """Galat tipe I (efek = 0) dan daya uji (efek > 0) dengan desain IDHS nyata (bobot, PSU, strata).
    Tiap variabel laten = sqrt(icc)*u_PSU + sqrt(1-icc)*e; Y_laten = r*X_laten + sqrt(1-r^2)*Y_laten0, lalu
    didikotomkan/dibagi tiga. Membandingkan uji naif (B2) dengan Rao-Scott orde 1, orde 2, dan t-desain (N1)."""
    rng = rng or np.random.default_rng(C.SEED)
    base = d[['bobot', 'strata', 'psu']].reset_index(drop=True)
    ds = Desain(base)
    kasus = [("biner 2×2, S=∅", 'xb', 'yb', ()), ("3×3 (df 4), S=∅", 'x3', 'y3', ()),
             ("biner 2×2, S={z}", 'xb', 'yb', ('zb',)), ("kontinu, S=∅", 'xc', 'yc', ()),
             ("kontinu, S={z}", 'xc', 'yc', ('zc',))]
    hasil, pnull = [], {}
    efek = tuple(sorted(set((0.0,) + tuple(efek))))               # efek 0 selalu ada untuk kalibrasi ukuran
    for r in efek:
        tolak = np.zeros((len(kasus), 3)); pv = [[] for _ in kasus]
        for _ in range(rep):
            lat = {v: np.sqrt(icc) * rng.standard_normal(ds.npsu)[ds.pc] + np.sqrt(1 - icc) * rng.standard_normal(len(base))
                   for v in ('x', 'y', 'z')}
            lat['y'] = r * lat['x'] + np.sqrt(1 - r ** 2) * lat['y']
            g = {}
            for v, l in lat.items():
                g[v + 'c'] = l; g[v + 'b'] = (l > 0).astype(float); g[v + '3'] = np.digitize(l, [-0.43, 0.43]).astype(float)
            x = base.assign(**g); cols = list(g); ix = {c: k for k, c in enumerate(cols)}
            naif, kor = BL.UjiCI(x, cols, "campuran"), UjiDesain(x, cols, "desain", ds)
            for k, (_, a, b, S) in enumerate(kasus):
                Si = tuple(ix[s] for s in S); ia, ib = ix[a], ix[b]
                pn = naif.p(ia, ib, Si); pv[k].append(pn)
                tolak[k, 0] += pn < alpha
                if a.endswith('c'):
                    pt = kor.t_desain(ia, ib, Si); tolak[k, 1] += pt < alpha; tolak[k, 2] += pt < alpha
                else:
                    tolak[k, 1] += kor.rao_scott(ia, ib, Si, orde=1) < alpha
                    tolak[k, 2] += kor.rao_scott(ia, ib, Si, orde=2) < alpha
        for k, ks in enumerate(kasus):
            if r == 0:
                pnull[k] = np.quantile(pv[k], alpha)                 # ambang naif agar ukurannya = alpha
            hasil.append({'uji': ks[0], 'efek': r, 'jenis': 'galat tipe I' if r == 0 else 'daya uji',
                          'naif (B2)': tolak[k, 0] / rep,
                          'naif disesuaikan ukuran': np.mean(np.array(pv[k]) < pnull[k]),
                          'terkoreksi orde 1': tolak[k, 1] / rep,
                          'terkoreksi orde 2': tolak[k, 2] / rep, 'nominal': alpha})
    return pd.DataFrame(hasil)


def simulasi_tipe1(d, rep, icc, alpha=0.05, rng=None):
    """Kompatibilitas: galat tipe I saja, kolom 'terkoreksi desain (N1)' = orde yang dipakai N1."""
    s = simulasi_uji(d, rep, icc, (0.0,), alpha, rng)
    kol = 'terkoreksi orde 2' if P.get('sd_rs_orde', 2) == 2 else 'terkoreksi orde 1'
    return s.rename(columns={kol: 'terkoreksi desain (N1)'})[['uji', 'naif (B2)', 'terkoreksi desain (N1)', 'nominal']]


# ================================================================== N2 TO-DAG
def robinson(p):
    a = [1]
    for m in range(1, p + 1):
        a.append(sum((-1) ** (k + 1) * math.comb(m, k) * 2 ** (k * (m - k)) * a[m - k] for k in range(1, m + 1)))
    return a[p]


class TODAG:
    """F(pi) = sum_j s(V_j, Pa*_pi(j)); Pa* lewat grow-shrink atas pendahulu. Karena pendahulu node tier t =
    semua tier < t + pendahulu di dalam tier t, F terurai per tier -> tiap tier dioptimalkan terpisah."""

    def __init__(self, sk, m, boleh=None):
        self.sk, self.m, self.boleh, self.gs_cache = sk, m, boleh, {}

    def gs(self, j, cand):
        key = (j, frozenset(cand))
        if key in self.gs_cache:
            return self.gs_cache[key]
        cand = {c for c in cand if self.boleh is None or frozenset((c, j)) in self.boleh}
        S, cur = set(), self.sk.lokal(j, set())
        while len(S) < self.m:                                   # grow
            best, bv = None, cur
            for c in cand - S:
                v = self.sk.lokal(j, S | {c})
                if v > bv + 1e-9:
                    best, bv = c, v
            if best is None:
                break
            S.add(best); cur = bv
        while S:                                                  # shrink
            best, bv = None, cur
            for c in S:
                v = self.sk.lokal(j, S - {c})
                if v >= bv - 1e-9:
                    best, bv = c, v
            if best is None:
                break
            S.discard(best); cur = bv
        self.gs_cache[key] = (cur, frozenset(S))
        return self.gs_cache[key]

    def F_tier(self, urutan, dasar):
        return sum(self.gs(j, dasar | set(urutan[:k]))[0] for k, j in enumerate(urutan))

    def eksak(self, U, dasar):
        """DP subset (Silander-Myllymaki) atas urutan di dalam tier: optimum untuk semua |U|! urutan."""
        g = {frozenset(): (0.0, ())}
        for ukuran in range(1, len(U) + 1):
            for A in itertools.combinations(U, ukuran):
                A = frozenset(A)
                g[A] = max(((g[A - {j}][0] + self.gs(j, dasar | (A - {j}))[0], g[A - {j}][1] + (j,)) for j in A),
                           key=lambda z: z[0])
        return list(g[frozenset(U)][1]), g[frozenset(U)][0]

    def lokal(self, U, dasar, jejak, t):
        """Pindahkan satu variabel ke posisi lain di dalam tier; terima perubahan terbaik yang menaikkan F."""
        urut = sorted(U); F = self.F_tier(urut, dasar)
        while True:
            best, bv = None, F
            for a in range(len(urut)):
                sisa = urut[:a] + urut[a + 1:]
                for b in range(len(urut)):
                    if b != a:
                        baru = sisa[:b] + [urut[a]] + sisa[b:]
                        v = self.F_tier(baru, dasar)
                        if v > bv + 1e-9:
                            best, bv = baru, v
            if best is None:
                return urut, F
            urut, F = best, bv
            jejak.append(dict(tier=t, mode='pindah', F_tier=F))

    def cari(self, V, tier, eksak_maks):
        urutan, jejak, dasar, total = [], [], set(), 0.0
        for t in sorted(set(tier)):
            U = [j for j in range(len(V)) if tier[j] == t]
            jejak.append(dict(tier=t, mode='awal', F_tier=self.F_tier(sorted(U), dasar)))
            if len(U) <= eksak_maks:
                urut, F = self.eksak(U, dasar); jejak.append(dict(tier=t, mode='eksak', F_tier=F))
            else:
                urut, F = self.lokal(U, dasar, jejak, t)
            urutan += urut; total += F; dasar |= set(U)
        G = nx.DiGraph(); G.add_nodes_from(range(len(V)))
        for k, j in enumerate(urutan):
            G.add_edges_from((i, j) for i in self.gs(j, set(urutan[:k]))[1])
        return G, urutan, total, pd.DataFrame(jejak)


def to_dag(d, V, G, spec, out, B, rng):
    T, Y = spec['T'], spec['Y']; t_all = time.time(); ix = {v: i for i, v in enumerate(V)}
    tier = [C.TIER[v] for v in V]
    tu = BL.mulai_ukur()
    n_eff = None
    if P['to_berbobot']:
        ds = Desain(d); dbar, n_kish, _ = deff_umum(d, V, ds); n_eff = n_kish / dbar
    sk = SkorW(d, V, P['to_skor'], P['to_berbobot'], n_eff, P['sd_skala'] if P['to_berbobot'] else 'n')
    to = TODAG(sk, P['to_maks_induk'])
    Gi, urutan, F, jejak = to.cari(V, tier, P['to_eksak_maks'])
    dp, mem = BL.selesai_ukur(tu)
    Gb = nx.relabel_nodes(Gi, dict(enumerate(V)))
    ukuran = pd.Series(tier).value_counts().sort_index()
    ruang = math.prod(math.factorial(k) for k in ukuran)
    jejak['tier_nama'] = [C.TIER_NAMA[t] for t in jejak.tier]
    jejak.to_csv(out / "to_jejak.csv", index=False)
    pd.DataFrame({'posisi': range(1, len(V) + 1), 'variabel': [V[j] for j in urutan],
                  'tier': [tier[j] for j in urutan]}).to_csv(out / "to_urutan.csv", index=False)
    # skor graf lain pada fungsi skor yang sama (adil)
    skor_graf = lambda E: sum(sk.lokal(ix[v], {ix[a] for a, b in E if b == v}) for v in V)
    f3 = C.OUT / "baseline" / spec_nama(spec) / "b3_dag.csv"
    s_b3 = skor_graf(list(pd.read_csv(f3).itertuples(index=False, name=None))) if f3.exists() else np.nan
    bd = simpan_dag(out, "to", Gb, V, spec, f"N2 TO-DAG (skor {P['to_skor']}"
                    + (", berbobot" if P['to_berbobot'] else "") + ")", G.subgraph(V))
    r, Z, ok, cat = BL.efek_graf(Gb, d, T, Y, B, rng)
    BL.info(out / "to_info.csv", n=len(d), skor=P['to_skor'], berbobot=P['to_berbobot'],
            n_penalti=round(n_eff or len(d), 1), maks_induk=P['to_maks_induk'],
            ukuran_tier=' · '.join(f"{C.TIER_NAMA[t]}={k}" for t, k in ukuran.items()),
            ruang_urutan_tier=f"{ruang:,}".replace(",", "."), ruang_urutan_tanpa_tier=f"{math.factorial(len(V)):.3e}",
            ruang_DAG=f"{robinson(len(V)):.3e}", ruang_setelah_dekomposisi=int(sum(math.factorial(k) for k in ukuran)),
            skor_lokal_dihitung=len(sk.cache), grow_shrink_dihitung=len(to.gs_cache),
            skor_TO_DAG=round(F, 2), skor_B3_pada_skor_sama=round(s_b3, 2), skor_pakar_pada_skor_sama=round(
                skor_graf(list(G.subgraph(V).edges())), 2),
            adjustment=', '.join(Z) or '-', catatan=cat or '-', **bd,
            detik_penemuan=round(dp, 2), memori_MB=round(mem, 2), detik=round(time.time() - t_all, 1))
    rows = [baris_n('N2', 'N2 TO-DAG', r, list(Gb.edges()), SHD=bd['SHD'], detik_penemuan=dp, memori_MB=mem,
                    catatan=f"{len(sk.cache)} skor lokal; F={F:.1f} vs B3 {s_b3:.1f}" + (f"; {cat}" if cat else ""))]
    lines = [f"N2 TO-DAG ruang urutan={ruang:,} (tanpa tier {math.factorial(len(V)):.2e}) skor lokal={len(sk.cache)}"
             f" F={F:.1f} (B3 {s_b3:.1f}) sisi={bd['sisi']} SHD={bd['SHD']} detik={dp:.2f} memori={mem:.1f}MB"
             f" RD={r['RD']:+.4f}"]
    return rows, lines


# ================================================================== N3 MLC-DAG
def _wpearson(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    c = np.average((x - mx) * (y - my), weights=w)
    return c / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))


def tetrakorik(x, y, w):
    """rho = argmax sum_i w_i log P_rho(x_i, y_i) pada tabel 2x2 berbobot."""
    p = np.array([[np.sum(w * ((x == a) & (y == b))) for b in (0, 1)] for a in (0, 1)]) / w.sum()
    ta, tb = stats.norm.ppf(p[0].sum()), stats.norm.ppf(p[:, 0].sum())
    Fa, Fb = stats.norm.cdf(ta), stats.norm.cdf(tb)

    def nll(r):
        P00 = stats.multivariate_normal.cdf([ta, tb], cov=[[1, r], [r, 1]])
        Pm = np.array([[P00, Fa - P00], [Fb - P00, 1 - Fa - Fb + P00]]).clip(1e-12)
        return -(p * np.log(Pm)).sum()
    return optimize.minimize_scalar(nll, bounds=(-0.995, 0.995), method='bounded', options={'xatol': 1e-4}).x


def korelasi_laten(d, cols):
    """Matriks korelasi respons laten berbobot: tetrakorik (biner-biner), biserial (biner-kontinu),
    Pearson berbobot (lainnya; ordinal diperlakukan kontinu)."""
    X = d[cols].astype(float).values; w = d.bobot.values
    biner = [set(np.unique(X[:, k])) <= {0.0, 1.0} for k in range(len(cols))]
    R = np.eye(len(cols))
    for a, b in itertools.combinations(range(len(cols)), 2):
        x, y = X[:, a], X[:, b]
        if biner[a] and biner[b]:
            r = tetrakorik(x, y, w)
        elif biner[a] or biner[b]:
            bi, ko = (x, y) if biner[a] else (y, x)
            pp = np.average(bi, weights=w)
            r = np.clip(_wpearson(bi, ko, w) * np.sqrt(pp * (1 - pp)) / stats.norm.pdf(stats.norm.ppf(pp)), -.99, .99)
        else:
            r = _wpearson(x, y, w)
        R[a, b] = R[b, a] = r
    return R, biner


def satu_faktor(Rd):
    """Principal axis factoring satu faktor: lambda, Theta = 1 - lambda^2."""
    h = np.clip(1 - 1 / np.diag(np.linalg.pinv(Rd)), 0.05, 0.95)
    for _ in range(200):
        M = Rd.copy(); np.fill_diagonal(M, h)
        val, vec = np.linalg.eigh(M)
        lam = vec[:, -1] * np.sqrt(max(val[-1], 1e-6))
        lam = np.clip(lam * (np.sign(lam.sum()) or 1), -0.995, 0.995)        # cegah kasus Heywood (Theta < 0)
        hn = np.clip(lam ** 2, 0.01, 0.995)
        if np.abs(hn - h).max() < 1e-6:
            break
        h = hn
    return lam, 1 - lam ** 2


def ukur(R, grup):
    """grup: {konstruk: [indeks]} -> lambda, Theta per konstruk dan phi (korelasi konstruk, rumus Tahap 3)."""
    lam = {k: satu_faktor(R[np.ix_(i, i)]) for k, i in grup.items()}
    ks = list(grup)
    phi = np.eye(len(ks))
    for a, b in itertools.combinations(range(len(ks)), 2):
        la, lb = lam[ks[a]][0], lam[ks[b]][0]
        phi[a, b] = phi[b, a] = la @ R[np.ix_(grup[ks[a]], grup[ks[b]])] @ lb / ((la @ la) * (lb @ lb))
    return lam, phi


def purifikasi(R, grup, nama_kol):
    """Buang indikator (satu per iterasi, konstruk tetap >= 3 indikator) yang: muatan lemah, melanggar
    kendala tetrad di dalam konstruk (s_ab s_ce - s_ac s_be = 0), atau melanggar tetrad lintas konstruk
    (a, b di d; c, e di d' -> s_ac s_be - s_ae s_bc = 0), yaitu berhubungan langsung dengan dimensi lain."""
    grup = {k: list(v) for k, v in grup.items()}; log = []
    while True:
        lam, phi = ukur(R, grup); ks = list(grup)
        calon = []
        for di, k in enumerate(ks):
            if len(grup[k]) <= 3:
                continue
            for pos, a in enumerate(grup[k]):
                la = lam[k][0][pos]
                lain = [x for x in grup[k] if x != a]
                tet = np.mean([abs(R[a, b] * R[c, e] - R[a, c] * R[b, e]) for b, c, e in itertools.permutations(lain, 3)])
                res = np.mean([abs(R[a, c] * R[b, e] - R[a, e] * R[b, c]) for b in lain
                               for k2 in ks if k2 != k for c, e in itertools.combinations(grup[k2], 2)])
                langgar = max(C.NOVELTY['mlc_muatan_min'] / max(abs(la), 1e-6), tet / C.NOVELTY['mlc_tetrad_maks'],
                              res / C.NOVELTY['mlc_lintas_maks'])
                if langgar > 1:
                    calon.append((langgar, k, a, la, tet, res))
        if not calon:
            return grup, lam, phi, pd.DataFrame(log)
        _, k, a, la, tet, res = max(calon)
        grup[k].remove(a)
        log.append(dict(konstruk=k, indikator=nama_kol[a], muatan=la, tetrad=tet, tetrad_lintas=res,
                        alasan='muatan lemah' if abs(la) < C.NOVELTY['mlc_muatan_min'] else
                        'tetrad dalam konstruk' if tet / C.NOVELTY['mlc_tetrad_maks'] >= res / C.NOVELTY['mlc_lintas_maks']
                        else 'tetrad lintas konstruk'))


def omega(lam, th):
    return float(lam.sum() ** 2 / (lam.sum() ** 2 + th.sum()))


def bangun_mlc(dd, obs, R=None, biner=None):
    """Lapis pengukuran N3 v2 -> statistik cukup Sigma_V dan skor unit.
    komposit : indeks formatif c = w'x / sqrt(w'R w), w = vektor eigen pertama R_dd (tanpa koreksi galat ukur)
    reflektif: satu-faktor + purifikasi tetrad; dipertahankan hanya bila omega >= mlc_omega_min, bila tidak
               indikatornya menjadi node teramati terpisah.
    Kovarians: reflektif-reflektif  l_d'R l_e / ((l_d'l_d)(l_e'l_e));  reflektif-x  l_d'R_dx / (l_d'l_d);
               komposit-x  w'R_cx / sqrt(w'R_cc w);  lainnya R."""
    ind = [c for v in C.MLC_KONSTRUK.values() for c in v]
    cols = list(dict.fromkeys(ind + obs))
    if R is None:
        R, biner = korelasi_laten(dd, cols)
    ix = {c: k for k, c in enumerate(cols)}
    jenis = {k: C.MLC_JENIS.get(k, "reflektif") for k in C.MLC_KONSTRUK}
    refl0 = {k: [ix[c] for c in v] for k, v in C.MLC_KONSTRUK.items() if jenis[k] == "reflektif"}
    grup, lam, _, plog = purifikasi(R, refl0, cols) if refl0 else ({}, {}, None, pd.DataFrame())
    om = {k: omega(*lam[k]) for k in grup}
    refl = [k for k in grup if om[k] >= P['mlc_omega_min']]
    pecah = [k for k in grup if k not in refl]
    komp = {}
    for k, v in C.MLC_KONSTRUK.items():
        if jenis[k] == "komposit":
            i = [ix[c] for c in v]
            val, vec = np.linalg.eigh(R[np.ix_(i, i)])
            w = vec[:, -1] * (np.sign(vec[:, -1].sum()) or 1)
            komp[k] = (i, w, float(val[-1] / val.sum()))
    tunggal = list(dict.fromkeys([cols[i] for k in pecah for i in grup[k]] + obs))    # node teramati
    Vm = refl + list(komp) + tunggal
    vek = {}                                                    # vektor pemetaan node -> kombinasi kolom R
    for k in refl:
        la = lam[k][0]; v = np.zeros(len(cols)); v[grup[k]] = la / (la @ la); vek[k] = v
    for k, (i, w, _) in komp.items():
        v = np.zeros(len(cols)); v[i] = w / np.sqrt(w @ R[np.ix_(i, i)] @ w); vek[k] = v
    for c in tunggal:
        v = np.zeros(len(cols)); v[ix[c]] = 1.0; vek[c] = v
    S = np.array([[vek[a] @ R @ vek[b] for b in Vm] for a in Vm])
    for a, k in enumerate(Vm):                                   # varians konstruk reflektif terkoreksi = 1
        if k in refl:
            S[a, a] = 1.0
    val, vec = np.linalg.eigh(S)
    S = vec @ np.diag(np.clip(val, 1e-4, None)) @ vec.T; sd = np.sqrt(np.diag(S)); S = S / np.outer(sd, sd)
    m_ = dict(refl=refl, lam=lam, grup=grup, komposit=komp, R=R, cols=cols)
    skor = skor_mlc(m_, dd)
    muat = pd.DataFrame(
        [dict(konstruk=k, jenis="reflektif" + ("" if k in refl else " → dipecah (ω < "
                                                  f"{P['mlc_omega_min']:.2f})"), indikator=cols[i],
              muatan=lam[k][0][q], galat=lam[k][1][q], bobot_komposit=np.nan, biner=biner[i])
         for k in grup for q, i in enumerate(grup[k])]
        + [dict(konstruk=k, jenis="komposit (formatif)", indikator=cols[i], muatan=np.nan, galat=np.nan,
                bobot_komposit=w[q], biner=biner[i]) for k, (ii, w, _) in komp.items() for q, i in enumerate(ii)])
    return dict(S=S, Vm=Vm, tier=[C.TIER[v] for v in Vm], skor=skor, R=R, cols=cols,
                biner=biner, muatan=muat, purifikasi=plog, omega=om, refl=refl, pecah=pecah, komposit=komp,
                indikator=ind, lam=lam, grup=grup)


def skor_mlc(m, dd):
    """Skor unit konstruk untuk data dd memakai parameter pengukuran m: Bartlett (reflektif) dan indeks
    (komposit), dari indikator yang dibakukan berbobot pada dd."""
    w_u = dd.bobot.values; skor = {}; cols, R = m['cols'], m['R']

    def baku(c):
        x = dd[c].astype(float).values; mu = w_u @ x / w_u.sum()
        s_ = np.sqrt(w_u @ (x - mu) ** 2 / w_u.sum()); return (x - mu) / (s_ if s_ > 0 else 1)
    for k in m['refl']:
        la, th = m['lam'][k]; wt = (la / th) / (la @ (la / th))
        skor[k] = np.column_stack([baku(cols[i]) for i in m['grup'][k]]) @ wt
    for k, (i, w, _) in m['komposit'].items():
        skor[k] = np.column_stack([baku(cols[q]) for q in i]) @ w / np.sqrt(w @ R[np.ix_(i, i)] @ w)
    return pd.DataFrame(skor, index=dd.index)


def data_mlc(spec, sumber=None):
    """Data kasus lengkap untuk MLC: semua indikator konstruk + variabel teramati kunci + T, Y analisis + variabel
    DAG analisis yang bukan indikator (confounder konteks tetap teramati), kecuali yang digantikan konstruk."""
    T, Y = spec['T'], spec['Y']
    ind = {c for v in C.MLC_KONSTRUK.values() for c in v}
    Vdag = [v for v in BL.build_dag(spec) if v not in spec['laten'] and v not in ind and v not in C.MLC_DIGANTI]
    obs = list(dict.fromkeys(list(C.MLC_TERAMATI) + [T, Y] + Vdag))
    cols = list(dict.fromkeys([c for v in C.MLC_KONSTRUK.values() for c in v] + obs))
    src = MLC_DATA[0] if sumber is None else sumber
    return (src.query(spec['filter']) if spec['filter'] else src).dropna(subset=cols).reset_index(drop=True), obs, cols


def mlc_dag(d, V, G, spec, out, B, rng):
    """N3 v2. d, V dari baseline tidak dipakai untuk struktur: node MLC = konstruk/komposit + variabel teramati."""
    T, Y = spec['T'], spec['Y']; t_all = time.time()
    dd, obs, cols = data_mlc(spec)
    tu = BL.mulai_ukur()
    R, biner = korelasi_laten(dd, cols)                 # dipakai bersama oleh MLC dan ablasinya
    d_kor, m_kor = BL.selesai_ukur(tu)
    tu = BL.mulai_ukur()
    m = bangun_mlc(dd, obs, R, biner)
    d_ukur = time.time() - tu
    Gi, info_pen = temukan(m['S'], len(dd), m['Vm'], m['tier'])
    d_struk, mem = BL.selesai_ukur(tu)
    d_struk -= d_ukur
    dp, mem = d_kor + d_struk + d_ukur, max(mem, m_kor)
    Vm = m['Vm']
    tier_raw = [C.TIER[c] if c in C.TIER else C.TIER[next(kk for kk, v in C.MLC_KONSTRUK.items() if c in v)]
                for c in cols]
    tu2 = BL.mulai_ukur()
    Gr, info_raw = temukan(R, len(dd), cols, tier_raw)
    d_struk_raw, mem_raw = BL.selesai_ukur(tu2)
    dp_raw, mem_raw = d_kor + d_struk_raw, max(mem_raw, m_kor)
    lemah = [f"{kk} ({cols[i]} λ={m['lam'][kk][0][q]:.2f})" for kk in m['refl'] for q, i in enumerate(m['grup'][kk])
             if abs(m['lam'][kk][0][q]) < P['mlc_muatan_min']]
    dd = pd.concat([dd, m['skor']], axis=1)
    Gb = nx.relabel_nodes(Gi, dict(enumerate(Vm)))
    Gbr = nx.relabel_nodes(Gr, dict(enumerate(cols)))
    BL.gambar(Vm, Gb.edges(), [], spec, f"N3 MLC-DAG v2 ({P['mlc_penemuan']} pada Σ̂_V, {len(Vm)} node)",
              out / "mlc_graf.png")
    pd.DataFrame(list(Gb.edges()), columns=['dari', 'ke']).to_csv(out / "mlc_dag.csv", index=False)
    r, Z, ok, cat = BL.efek_graf(Gb, dd, T, Y, B, rng)
    rr, Zr, _, catr = BL.efek_graf(Gbr, dd, T, Y, B, rng)
    pd.DataFrame(m['S'], index=Vm, columns=Vm).to_csv(out / "mlc_sigma.csv")
    m['muatan'].to_csv(out / "mlc_muatan.csv", index=False)
    (m['purifikasi'] if len(m['purifikasi']) else pd.DataFrame(columns=['konstruk', 'indikator', 'muatan', 'tetrad',
     'tetrad_lintas', 'alasan'])).to_csv(out / "mlc_purifikasi.csv", index=False)
    rel = {**{k: f"{v:.2f}" for k, v in m['omega'].items()},
           **{k: f"komposit (PC1 {v[2]:.0%})" for k, v in m['komposit'].items()}}
    BL.info(out / "mlc_info.csv", n=len(dd), penemuan=P['mlc_penemuan'], node_struktural=len(Vm),
            node_tanpa_konstruk=len(cols), indikator_awal=len(m['indikator']),
            indikator_dibuang=len(m['purifikasi']),
            konstruk_reflektif=', '.join(m['refl']) or '-', konstruk_komposit=', '.join(m['komposit']) or '-',
            konstruk_dipecah=', '.join(m['pecah']) or '-', omega_min=P['mlc_omega_min'],
            reliabilitas_omega=', '.join(f"{k}={v}" for k, v in rel.items()),
            entri_statistik_cukup=len(Vm) ** 2, entri_tanpa_konstruk=len(cols) ** 2,
            uji_atau_skor=info_pen, uji_atau_skor_tanpa_konstruk=info_raw,
            sisi=Gb.number_of_edges(), sisi_tanpa_konstruk=Gbr.number_of_edges(),
            adjustment=', '.join(Z) or '-', catatan=cat or '-',
            konstruk_bermasalah='; '.join(lemah) or '-',
            detik_korelasi=round(d_kor, 3), detik_model_ukur=round(d_ukur, 3),
            detik_struktur=round(d_struk, 3), detik_struktur_tanpa_konstruk=round(d_struk_raw, 3),
            detik_penemuan=round(dp, 3), memori_MB=round(mem, 3),
            detik_tanpa_konstruk=round(dp_raw, 3), memori_MB_tanpa_konstruk=round(mem_raw, 3),
            detik=round(time.time() - t_all, 1))
    rows = [baris_n('N3', 'N3 MLC-DAG', r, [], detik_penemuan=dp, memori_MB=mem, node=len(Vm),
                    catatan=f"{len(Vm)} node; reflektif: {', '.join(m['refl']) or '-'}; komposit: "
                            f"{', '.join(m['komposit'])}" + (f"; {cat}" if cat else "")),
            baris_n('N3-', 'N3 ablasi: tanpa konstruk laten', rr, [], detik_penemuan=dp_raw, memori_MB=mem_raw,
                    node=len(cols), catatan=f"{len(cols)} node indikator mentah" + (f"; {catr}" if catr else ""))]
    for x in rows:
        x['sisi'] = Gb.number_of_edges() if x['kode'] == 'N3' else Gbr.number_of_edges()
    lines = [f"N3 MLC-DAG v2 node {len(cols)}->{len(Vm)} reflektif={m['refl']} komposit={list(m['komposit'])}"
             f" dipecah={m['pecah']} omega={ {k: round(v, 2) for k, v in m['omega'].items()} }"
             f" sisi={Gb.number_of_edges()} detik={dp:.2f} (tanpa konstruk {dp_raw:.2f})"
             f" RD={r['RD']:+.4f} (tanpa konstruk {rr['RD']:+.4f})"]
    return rows, lines


def temukan(S, n, nodes, tier):
    """Discover(Sigma): TO-DAG skor Gauss atau PC Fisher z (+ tier + Meek, diperluas ke DAG)."""
    if P['mlc_penemuan'] == "pc":
        ci = UjiKov(S, n)
        A, sep = BL.pc_skeleton(ci, len(nodes), P['mlc_alpha'], C.BASELINE['maks_kondisi'])
        A = BL.orientasi(A, sep, np.array(tier))
        G = nx.DiGraph(); G.add_nodes_from(range(len(nodes)))
        G.add_edges_from((i, j) for i, j in itertools.permutations(range(len(nodes)), 2) if A[i, j] and not A[j, i])
        for i, j in itertools.combinations(range(len(nodes)), 2):
            if A[i, j] and A[j, i]:
                G.add_edge(*((j, i) if nx.has_path(G, j, i) else (i, j)))
        return G, f"{ci.jumlah} uji"
    sk = SkorKov(S, n)
    G, _, _, _ = TODAG(sk, P['to_maks_induk']).cari(nodes, tier, P['to_eksak_maks'])
    return G, f"{len(sk.cache)} skor lokal"


MLC_DATA = [None]    # dataset lengkap (bukan kasus lengkap V baseline), diisi oleh run()


# ================================================================== jalankan
FN = {"sd_hybrid": sd_hybrid, "to_dag": to_dag, "mlc_dag": mlc_dag}


def run(df, metode, nama=None, progress=None, simulasi=False):
    rng = np.random.default_rng(C.SEED); lines = []
    MLC_DATA[0] = df
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = folder(metode, n)
        d, V, G = BL.siapkan(df, spec)
        if progress:
            progress(f"{n}: {METODE[metode]['nama']} berjalan...")
        rows, l = FN[metode](d, V, G, spec, out, P['boot'], rng)
        lines += [f"NOV[{n}] {x}" for x in l]
        lines.append(f"NOV[{n}] " + banding_baseline(n, metode, rows, d if metode != "mlc_dag" else None, V, out))
        if simulasi and metode == "sd_hybrid":
            if progress:
                progress(f"{n}: simulasi galat tipe I ({P['sim_rep']} replikasi)...")
            sim = simulasi_uji(d, P['sim_rep'], P['sim_icc'], tuple(P['sim_efek']), rng=rng)
            sim.to_csv(out / "sd_uji.csv", index=False)
            kol = 'terkoreksi orde 2' if P['sd_rs_orde'] == 2 else 'terkoreksi orde 1'
            (sim[sim.efek == 0].rename(columns={kol: 'terkoreksi desain (N1)'})
             [['uji', 'naif (B2)', 'terkoreksi desain (N1)', 'nominal']].to_csv(out / "sd_tipe1.csv", index=False))
            lines.append(f"NOV[{n}] uji (naif/orde1/orde2): " + "; ".join(
                f"{r.uji} efek={r.efek}: {r._4:.3f}/{r._6:.3f}/{r._7:.3f}" for r in sim.itertuples()))
    return lines
