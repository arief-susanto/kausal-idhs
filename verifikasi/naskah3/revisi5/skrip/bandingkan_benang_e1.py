"""Butir 7: bandingkan run ulang dengan utas BLAS = 1 (uji_benang_e1.py) terhadap hasil asli benchmark v4,
dan pembandingnya: run ulang tanpa penguncian utas (label venv, E7) pada tugas yang sama.

Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/bandingkan_benang_e1.py
Keluaran: naskah/03_reproduksibilitas/tabel/E1_uji_benang.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROYEK = ROOT.parents[1]
U = ROOT / "tabel" / "E7_ulang"
KUNCI = ["sel", "rep", "metode"]
NUM = ["RD_hat", "se", "RD_lo", "RD_hi", "FDR", "recall"]
DISKRIT = ["n_Z", "Z", "valid", "cakup"]
baca = lambda f: pd.read_csv(f, low_memory=False, float_precision="round_trip")


def banding(b, a, label):
    m = b.merge(a, on=KUNCI, suffixes=("_b", "_a"), how="inner", validate="one_to_one")
    bit = np.ones(len(m), bool)
    for k in NUM:
        bit &= ((m[f"{k}_b"] == m[f"{k}_a"]) | (m[f"{k}_b"].isna() & m[f"{k}_a"].isna())).to_numpy()
    sel = np.nanmax(np.abs(m[[f"{k}_b" for k in NUM]].to_numpy(float) - m[[f"{k}_a" for k in NUM]].to_numpy(float)), axis=1)
    disk = np.ones(len(m), bool)
    for k in DISKRIT:
        disk &= (m[f"{k}_b"].fillna("").astype(str) == m[f"{k}_a"].fillna("").astype(str)).to_numpy()
    return dict(banding=label, estimasi=len(m), identik_bit=int(bit.sum()), selisih_maks=float(np.nanmax(np.nan_to_num(sel))),
                keputusan_sama=int(disk.sum()))


if __name__ == "__main__":
    asli = baca(PROYEK / "hasil/benchmark_v4/per_rep.csv")
    b1 = baca(U / "per_rep_venv_benang1.csv")
    tugas = b1[["sel", "rep"]].drop_duplicates()
    venv = baca(U / "per_rep_venv.csv").merge(tugas, on=["sel", "rep"])
    py39 = baca(U / "per_rep_py39.csv").merge(tugas, on=["sel", "rep"])
    rows = [banding(b1, asli, "utas=1 vs asli"), banding(venv, asli, "utas bawaan (venv) vs asli"),
            banding(b1, venv, "utas=1 vs utas bawaan"), banding(py39, asli, "py39 (utas bawaan) vs asli")]
    R = pd.DataFrame(rows)
    meta = json.loads((U / "meta_venv_benang1.json").read_text())
    R["tugas"] = len(tugas)
    R.to_csv(ROOT / "tabel" / "E1_uji_benang.csv", index=False)
    print(R.to_string()); print(json.dumps(meta.get("blas"), indent=1))
