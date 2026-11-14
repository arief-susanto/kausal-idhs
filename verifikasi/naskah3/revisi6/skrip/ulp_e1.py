"""Review 14-11-2026, minor 5: selisih E1/E6 dalam satuan ULP dan selisih relatif (bukan hanya selisih mutlak).

ULP dihitung sebagai jarak representasi biner IEEE 754 (bilangan bulat berurutan) antara dua nilai double.
Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/ulp_e1.py
Keluaran: naskah/03_reproduksibilitas/tabel/E1_ulp.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; PROYEK = ROOT.parents[1]; T = ROOT / "tabel"
baca = lambda f: pd.read_csv(f, low_memory=False, float_precision="round_trip")
NUM = ["RD_hat", "se", "RD_lo", "RD_hi", "FDR", "recall"]


def ulp(a, b):
    ia, ib = a.view(np.int64), b.view(np.int64)
    ia = np.where(ia < 0, np.int64(-2**63) - ia, ia); ib = np.where(ib < 0, np.int64(-2**63) - ib, ib)
    return np.abs(ia - ib)


asli = baca(PROYEK / "hasil/benchmark_v4/per_rep.csv")
rows = []
for nama, f, acuan in [("venv vs asli", "per_rep_venv.csv", asli), ("py39 vs venv", "per_rep_py39.csv", baca(T / "E7_ulang/per_rep_venv.csv"))]:
    m = baca(T / "E7_ulang" / f).merge(acuan, on=["sel", "rep", "metode"], suffixes=("_b", "_a"))
    a = np.concatenate([m[f"{k}_a"].to_numpy(float) for k in NUM]); b = np.concatenate([m[f"{k}_b"].to_numpy(float) for k in NUM])
    ok = np.isfinite(a) & np.isfinite(b); a, b = a[ok], b[ok]
    u = ulp(a, b); beda = u > 0
    rel = np.abs(a - b)[beda] / np.maximum(np.abs(a[beda]), np.abs(b[beda]))
    rows.append(dict(banding=nama, nilai=len(a), berbeda=int(beda.sum()), ulp_median=float(np.median(u[beda])) if beda.any() else 0,
                     ulp_maks=int(u.max()), ulp_p99=float(np.quantile(u[beda], .99)) if beda.any() else 0,
                     rel_maks=float(rel.max()) if beda.any() else 0, abs_maks=float(np.abs(a - b).max())))
R = pd.DataFrame(rows); R.to_csv(T / "E1_ulp.csv", index=False); print(R.to_string())
