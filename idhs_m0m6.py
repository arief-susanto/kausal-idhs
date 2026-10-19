"""FASE 3: metode M0-M6 dari bench_v4.py diterapkan pada data IDHS (forest plot naskah).

Fungsi penemuan graf dan estimator dipakai apa adanya dari bench_v4 (pc_induk, Memo, Longgar, aipw), sehingga
angka di sini sebanding dengan benchmark. Penyesuaian untuk data nyata (di simulasi tidak ada mediator dan T
sendirian di tiernya; di IDHS tidak):
  M0 = semua variabel dengan tier < tier(T), ditambah induk T di DAG pakar
  M1 = induk T di DAG pakar (asli, tanpa perturbasi)
  M6 = induk T atau induk Y dari graf M3, induk Y dibatasi ke tier <= tier(T)
  lipatan cross-fitting SAMA untuk semua metode (benih per analisis), agar selisih RD hanya berasal dari Z
Efek benar tidak diketahui: yang dibaca adalah konsistensi RD antar-himpunan, bukan peringkat metode.
Jalankan:  python idhs_m0m6.py [nama_analisis ...]
Keluaran:  hasil/idhs_m0m6/<analisis>/rd.csv dan forest.png"""
import sys
import zlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C
import baseline as BL
import novelty as N
import prep
import bench_v4 as B4

P = C.BENCH_V4
NASKAH = ["sanitasi_diare", "pbi_diare"]


def himpunan(d, V, G, T, Y):
    """Himpunan penyesuaian tiap metode; d sudah memakai nama kolom 'T' dan 'Y'."""
    nm = lambda v: 'T' if v == T else 'Y' if v == Y else v
    Vn = [nm(v) for v in V]; tier = [C.TIER[v] for v in V]; tT = C.TIER[T]
    ds = N.Desain(d)
    pakar = [v for v in G.predecessors(T) if v in V]
    Zs = {'M0': sorted({v for v in V if C.TIER[v] < tT} | set(pakar)), 'M1': sorted(pakar)}
    Zs['M2'], _, _ = B4.pc_induk(BL.UjiCI(d, Vn, "campuran"), Vn, tier)
    des = B4.Memo(N.UjiDesain(d, Vn, "desain", ds, C.NOVELTY['sd_rs_orde']))
    paT3, paY3, _ = B4.pc_induk(des, Vn, tier)
    Zs['M3'] = paT3
    khusus = [Vn.index('T'), Vn.index('Y')]
    for a in P['alpha_T']:
        Zs[f"M4(aT={a})"], _, _ = B4.pc_induk(B4.Longgar(des, khusus, P['alpha'], a), Vn, tier)
    Zs['M5'] = sorted(set(paT3) | set(pakar))
    Zs['M6'] = sorted(set(paT3) | {v for v in paY3 if C.TIER[v] <= tT})
    return Zs, ds


def forest(tab, T, Y, path):
    t = tab.iloc[::-1]; y = np.arange(len(t))
    plt.figure(figsize=(8, 0.6 * len(t) + 1.2))
    plt.errorbar(t.RD, y, xerr=np.vstack([t.RD - t.RD_lo, t.RD_hi - t.RD]), fmt='o', color='#1f77b4', capsize=4)
    plt.axvline(0, color='#888888', ls='--', lw=1)
    plt.yticks(y, [f"{m} (|Z|={k})" for m, k in zip(t.metode, t.n_Z)], fontsize=8)
    plt.xlabel(f"Risk difference {T} -> {Y} (AIPW cross-fitting per PSU, CI 95% linearisasi desain)")
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def run(df, nama):
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    d, V, G = BL.siapkan(df, spec)
    d = d.rename(columns={T: 'T', Y: 'Y'})
    Zs, ds = himpunan(d, V, G, T, Y)
    w = d.bobot.values; rows = []
    for m, Z in Zs.items():
        rng = np.random.default_rng([C.SEED, zlib.crc32(nama.encode())])     # lipatan sama untuk semua metode
        rd, se, lo, hi = B4.aipw(d, list(Z), ds, w, P['K'], rng)
        rows.append(dict(analisis=nama, metode=m, n=len(d), n_Z=len(Z), RD=rd, se=se, RD_lo=lo, RD_hi=hi,
                         Z=", ".join(Z) or "-"))
    tab = pd.DataFrame(rows)
    out = C.OUT / "idhs_m0m6" / nama; out.mkdir(parents=True, exist_ok=True)
    tab.to_csv(out / "rd.csv", index=False)
    forest(tab, T, Y, out / "forest.png")
    return [f"M0M6[{nama}] {r.metode}: |Z|={r.n_Z} RD={r.RD:+.4f} [{r.RD_lo:+.4f},{r.RD_hi:+.4f}] Z={r.Z}"
            for r in tab.itertuples()]


if __name__ == "__main__":
    df = prep.load()
    for nama in sys.argv[1:] or NASKAH:
        print("\n".join(run(df, nama)), flush=True)
