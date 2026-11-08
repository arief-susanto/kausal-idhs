"""Lengkapi uji pemisah E4: hitung putusan H1-H5 untuk run "kode sekarang + config_old" (ulang_config_lama.py).

uji_pernyataan (dasar H5) tidak memakai aliran acak metode; datanya dibangkitkan ulang per replikasi skenario A
persis seperti benchmark.satu(), lalu putusan dihitung dengan benchmark.hipotesis() atas per_rep_config_lama.csv.
Catatan: H2 (kecepatan) dan H3 (memori) bergantung pada waktu komputasi, jadi tidak dapat dibandingkan antar-run.

Pakai (dari folder proyek kausal_idhs):  python naskah_ke_2/03_reproduksibilitas/skrip/putusan_config_lama.py
"""
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "1"
SKRIP = Path(__file__).resolve().parent
sys.path.insert(0, str(SKRIP))
import ulang_config_lama as U                                     # noqa: E402  (mengatur sys.path dan cwd proyek)

if __name__ == "__main__":
    import numpy as np
    import pandas as pd
    U.pasang_config_lama()
    import config as C
    import benchmark as BM
    BM.folder = lambda nama: U.OUT
    df = pd.read_pickle(C.CACHE / "analisis.pkl")
    kt, _ = BM.siapkan(df, "sanitasi_diare")
    k = kt["A"]; uji = []
    for r in range(100):
        rng = np.random.default_rng([C.SEED, r, ord("A")])
        nz = BM.noise_A(k['par'], len(k['pc']), k['npsu'], rng)
        X, _ = BM.bangkit_A(k['par'], k['pc'], nz)
        uji += [dict(**u, rep=r, skenario="A") for u in BM.uji_pernyataan(k['desain'].assign(**X), k)]
    pd.DataFrame(uji).to_csv(U.OUT / "uji_pernyataan.csv", index=False)
    d = pd.read_csv(U.OUT / "per_rep_config_lama.csv", float_precision="round_trip")
    d["galat"] = d.RD_hat - d.RD_benar; d["abs_galat"] = d.galat.abs()     # sama dengan benchmark.ringkas()
    BM.hipotesis(d, U.OUT)
    put = pd.read_csv(U.OUT / "putusan.csv")
    print(put.to_string()); print(pd.read_csv(U.OUT / "hipotesis_H5.csv").to_string())
