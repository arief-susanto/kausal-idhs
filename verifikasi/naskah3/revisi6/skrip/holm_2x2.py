"""Review 14-11-2026, minor 3: koreksi perbandingan berganda (Holm) untuk efek utama dan interaksi desain 2x2 E4.

Data, benih, dan bootstrap berpasangan (10.000 kali) sama persis dengan analisis_2x2_mc.py, sehingga IK identik dengan
Tabel 5; tambahan: p bootstrap dua sisi = min(1, 2 * min(P(b <= 0), P(b >= 0))) dan p Holm atas semua uji
(metode x {kode, konfigurasi, interaksi}). Sel yang identik di semua replikasi diberi p = 1.

Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/holm_2x2.py
Keluaran: naskah/03_reproduksibilitas/tabel/E4_2x2_holm.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SKRIP = Path(__file__).resolve().parent
sys.path.insert(0, str(SKRIP))
from analisis_2x2_mc import PROYEK, T, baca, nol  # noqa: E402

if __name__ == "__main__":
    S = {"lama_benar": nol(baca(T / "E4_sel4/lama_cfgbenar/per_rep.csv")),
         "baru_lama": nol(baca(T / "E4_config_lama/per_rep_config_lama.csv"))}
    r4 = baca(PROYEK / "hasil/benchmark/sanitasi_diare/per_rep.csv")
    rb = baca(T / "E5_run3_tier2/per_rep_B_tier2.csv")
    S["baru_benar"] = nol(pd.concat([r4[r4.skenario == "A"], rb]))
    S["lama_lama"] = nol(baca(T / "E4_sel4/lama_cfglama/per_rep.csv"))
    rng = np.random.default_rng(2017)                       # urutan pemakaian benih sama dengan analisis_2x2_mc.py
    rows = []
    for (sk, me), _ in S["baru_benar"].groupby(level=[0, 1], sort=False):
        X = {k: S[k].loc[(sk, me)].sort_index().to_numpy() for k in ("lama_benar", "baru_lama", "baru_benar", "lama_lama")}
        n = len(X["baru_benar"])

        def efek(ix):
            q = {k: X[k][ix].mean() for k in X}
            return ((q["baru_benar"] - q["lama_benar"] + q["baru_lama"] - q["lama_lama"]) / 2,
                    (q["baru_benar"] - q["baru_lama"] + q["lama_benar"] - q["lama_lama"]) / 2,
                    (q["baru_benar"] - q["baru_lama"]) - (q["lama_benar"] - q["lama_lama"]))
        e0 = efek(np.arange(n)); bs = np.array([efek(rng.integers(0, n, n)) for _ in range(10000)])
        for j, nama in enumerate(("kode", "konfigurasi", "interaksi")):
            b = bs[:, j]
            p = 1.0 if np.all(b == 0) else min(1.0, 2 * min((b <= 0).mean(), (b >= 0).mean()))
            rows.append(dict(skenario=sk, metode=me, efek=nama, nilai=e0[j], lo=np.percentile(b, 2.5),
                             hi=np.percentile(b, 97.5), p_boot=p))
    R = pd.DataFrame(rows)
    m = len(R); urut = np.argsort(R.p_boot.values); adj = np.empty(m); run = 0.0
    for i, k in enumerate(urut):
        run = max(run, min(1.0, (m - i) * R.p_boot.values[k])); adj[k] = run
    R["p_holm"] = adj
    ref = pd.read_csv(T / "E4_2x2_efek_nol.csv")
    for nama, kol in (("kode", "utama_kode"), ("konfigurasi", "utama_konfig"), ("interaksi", "interaksi")):
        a = R[R.efek == nama].set_index(["skenario", "metode"]); b = ref.set_index(["skenario", "metode"])
        assert np.allclose(a.lo, b[f"{kol}_lo"].loc[a.index]) and np.allclose(a.hi, b[f"{kol}_hi"].loc[a.index]), nama
    R.to_csv(T / "E4_2x2_holm.csv", index=False)
    with pd.option_context("display.width", 200):
        print(R[(R.p_boot < 0.05)].round(4).to_string()); print("uji:", m)
