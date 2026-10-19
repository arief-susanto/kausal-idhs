"""FASE 4: kumpulkan gambar dan tabel naskah ke naskah/gambar dan naskah/tabel dari folder hasil/.
Semua angka dibaca dari keluaran kode (tidak ada angka yang diketik tangan), sehingga bisa ditelusuri ke satu commit.
  G2 DAG pakar sanitasi->diare        G3 galat tipe I lima uji (simulasi N1)     G4 validitas penyesuaian dan FDR
  G5 forest plot RD IDHS (M0-M6)      G6 overlap propensity
  T1 desain simulasi   T2 kinerja per metode   T3 hipotesis H10-H13   T4 RD IDHS   T5 SMD   T6 galat tipe I
Jalankan:  python naskah_bahan.py"""
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C

BEKU = C.ROOT / "naskah" / "data"       # salinan beku keluaran (naskah_bekukan.py); hasil/ boleh ditimpa aplikasi
H = BEKU if BEKU.exists() else C.OUT
GB, TB = C.ROOT / "naskah" / "gambar", C.ROOT / "naskah" / "tabel"
UTAMA = "sanitasi_diare"
TINTA, REDUP, KISI = "#0b0b0b", "#898781", "#e1e0d9"          # teks, label sumbu, garis bantu
BIRU, BIRU_MUDA, ABU = "#1c5cab", "#86b6ef", "#b5b4ae"       # satu rona: tua = sorotan, muda = pembanding
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": TINTA, "text.color": TINTA,
                     "xtick.color": REDUP, "ytick.color": TINTA, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 300, "savefig.bbox": "tight"})


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z ** 2 / n
    c, h = (p + z ** 2 / (2 * n)) / d, z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return c - h, c + h


def g3_galat_tipe1():
    s = pd.read_csv(H / "novelty" / "sd_hybrid" / UTAMA / "sd_uji.csv").query("efek == 0").iloc[::-1]
    y = np.arange(len(s)); a, b = s['naif (B2)'].values * 100, s['terkoreksi orde 2'].values * 100
    fig, ax = plt.subplots(figsize=(6.5, 2.9))
    ax.hlines(y, b, a, color=KISI, lw=2, zorder=1)
    ax.scatter(a, y, s=42, color=BIRU_MUDA, zorder=2, label="Naive test")
    ax.scatter(b, y, s=42, color=BIRU, zorder=2, label="Design-corrected test (Rao-Scott 2nd order / design t)")
    ax.axvline(5, color=REDUP, lw=1, ls="--", zorder=0); ax.text(5.3, len(s) - 0.45, "nominal 5%", color=REDUP, fontsize=8)
    for yi, ai, bi in zip(y, a, b):
        ax.text(ai + 0.5, yi, f"{ai:.1f}", va="center", fontsize=8); ax.text(bi - 0.5, yi, f"{bi:.1f}", va="center", ha="right", fontsize=8)
    ax.set_yticks(y, s.uji.str.replace("biner", "binary").str.replace("kontinu", "continuous")); ax.set_ylim(-0.6, len(s) - 0.1); ax.set_xlim(0, max(a) + 3)
    ax.set_xlabel("Type I error rate (%)"); ax.grid(axis="x", color=KISI, lw=0.6); ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=8)
    fig.savefig(GB / "G3_galat_tipe1.png"); plt.close(fig)
    s.iloc[::-1].to_csv(TB / "T6_galat_tipe1.csv", index=False)


def kinerja(d):
    def f(g):
        e = g.RD_hat - g.RD_benar; lo, hi = wilson(g.valid.sum(), len(g))
        return pd.Series(dict(rep=len(g), valid=g.valid.mean(), valid_lo=lo, valid_hi=hi, bias=e.mean(),
                              RMSE=np.sqrt((e ** 2).mean()), cakupan=g.cakup.mean(), lebar_CI=(g.RD_hi - g.RD_lo).mean(),
                              n_Z=g.n_Z.mean(), FDR=g.FDR.mean(), recall=g.recall.mean()))
    return d.groupby("metode").apply(f).reset_index()


def g4_validitas_fdr(t):
    t = t.iloc[::-1].reset_index(drop=True); y = np.arange(len(t))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True, gridspec_kw={"wspace": 0.08})
    w = [ABU if m in ("M0", "M1") else BIRU for m in t.metode]            # M0/M1 = acuan, bukan penemuan graf
    v = t.valid.values * 100
    a1.barh(y, v, height=0.6, color=w, zorder=2)
    a1.errorbar(v, y, xerr=[(t.valid - t.valid_lo) * 100, (t.valid_hi - t.valid) * 100], fmt="none", ecolor=TINTA, lw=0.8, capsize=2, zorder=3)
    a1.axvline(90, color=REDUP, lw=1, ls="--", zorder=1); a1.text(91.5, len(t) - 0.35, "H10: 90%", color=REDUP, fontsize=8)
    for yi, vi, lo, hi in zip(y, v, t.valid_lo.values * 100, t.valid_hi.values * 100):   # label di dalam batang bila muat
        a1.text(*((lo - 1.5, yi) if vi > 30 else (hi + 1.5, yi)), f"{vi:.1f}", va="center", fontsize=8,
                ha="right" if vi > 30 else "left", color="white" if vi > 30 and t.metode[yi] not in ("M0", "M1") else TINTA)
    a1.set_xlim(0, 112); a1.set_xticks([0, 25, 50, 75, 100]); a1.set_yticks(y, t.metode); a1.set_ylim(-0.6, len(t) - 0.1)
    a1.set_xlabel("Valid adjustment set (%)")
    f = t.FDR.values * 100; ada = ~np.isnan(f)
    a2.barh(y[ada], f[ada], height=0.6, color=BIRU, zorder=2)
    for yi, fi in zip(y[ada], f[ada]):
        a2.text(fi + 0.6, yi, f"{fi:.1f}", va="center", fontsize=8)
    for yi in y[~ada]:
        a2.text(0.6, yi, "no graph discovery" if t.metode[yi] in ("M0", "M1") else "uses M3 graph", va="center", fontsize=8, color=REDUP)
    a2.set_xlim(0, 34); a2.set_xlabel("Skeleton false discovery rate (%)"); a2.tick_params(left=False)
    for a in (a1, a2):
        a.grid(axis="x", color=KISI, lw=0.6); a.set_axisbelow(True)
    fig.savefig(GB / "G4_validitas_fdr.png"); plt.close(fig)


def salin(sumber, tujuan):
    if sumber.exists():
        shutil.copyfile(sumber, tujuan); return True
    print("TIDAK ADA:", sumber); return False


def main():
    GB.mkdir(parents=True, exist_ok=True); TB.mkdir(parents=True, exist_ok=True)
    salin(H / "kausal" / UTAMA / "dag.png", GB / "G2_dag_pakar_sanitasi.png")
    g3_galat_tipe1()
    d = pd.read_csv(H / "benchmark_v4" / "per_rep.csv", dtype={"icc": str})
    het = kinerja(d[d.icc == "heterogen"])
    g4_validitas_fdr(het)
    pd.concat([het.assign(icc="heterogen"), kinerja(d[d.icc != "heterogen"]).assign(icc="0.15"),
               kinerja(d).assign(icc="semua")]).to_csv(TB / "T2_kinerja_metode.csv", index=False)
    P = C.BENCH_V4
    pd.DataFrame([("Replikasi per sel", P['rep']), ("Sel (ICC x efek x confounder x p)", 24),
                  ("ICC", "heterogen U(0,1; 0,8) per variabel; 0,15"), ("Efek T->Y (laten probit)", P['beta_ty']),
                  ("Kekuatan confounder", P['kuat_confounder']), ("Jumlah node p", P['p']),
                  ("Alpha uji (M2/M3)", P['alpha']), ("Alpha_T (M4); utama", f"{P['alpha_T']}; {P['alpha_T_utama']}"),
                  ("Ukuran maksimum himpunan kondisi", P['maks_kondisi']), ("Proporsi X laten", P['laten_frac']),
                  ("Desain (strata x PSU x unit)", P['desain']), ("Lipatan cross-fitting K", P['K'])],
                 columns=["parameter", "nilai"]).to_csv(TB / "T1_desain_simulasi.csv", index=False)
    salin(H / "benchmark_v4" / "hipotesis.csv", TB / "T3_hipotesis.csv")
    rd = [pd.read_csv(C.ROOT / "ringkasan" / "fase3_rd.csv")]
    for an in ("sanitasi_diare", "pbi_diare"):
        f = H / "idhs_m0m6" / an
        if salin(f / "forest.png", GB / f"G5_forest_idhs_{an}.png"):
            rd.append(pd.read_csv(f / "rd.csv").assign(sumber="M0-M6 (AIPW cross-fitting)"))
    pd.concat(rd, ignore_index=True).to_csv(TB / "T4_rd_idhs.csv", index=False)
    salin(H / "kausal" / UTAMA / "overlap.png", GB / "G6_overlap_propensity.png")
    salin(H / "kausal" / UTAMA / "keseimbangan.csv", TB / "T5_smd.csv")
    print("gambar:", sorted(p.name for p in GB.iterdir())); print("tabel:", sorted(p.name for p in TB.iterdir()))


if __name__ == "__main__":
    main()
