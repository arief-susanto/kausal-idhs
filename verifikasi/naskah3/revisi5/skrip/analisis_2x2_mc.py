"""Butir 5 dan 6 catatan perbaikan: desain 2x2 (kode x konfigurasi) untuk E4 dengan galat Monte Carlo.

Sel (proporsi efek dinihilkan = RD_hat == 0, per skenario x metode, 100 replikasi):
  lama_lama  : kode pra-audit + konfigurasi basi      (run 1b; per replikasi dari run validasi lama_cfglama
                                                        bila ringkasannya identik dengan run 1b)
  lama_benar : kode pra-audit + konfigurasi benar     (tabel/E4_sel4/lama_cfgbenar)
  baru_lama  : kode sesudah audit + konfigurasi basi  (run gabungan, tabel/E4_config_lama)
  baru_benar : kode sesudah audit + konfigurasi benar (run 3; per replikasi direkonstruksi: skenario A dari run 4,
                                                        yang identik dengan run 3 di seluruh ringkasan A; skenario B
                                                        dari run ulang tier 2, identik dengan run 3 pada 60/60 nilai)
Efek: kode = rerata (baru - lama) atas dua taraf konfigurasi; konfigurasi = rerata (benar - basi) atas dua taraf kode;
interaksi = (baru_benar - baru_lama) - (lama_benar - lama_lama).
CI 95%: Newcombe metode 10 (skor hibrida) untuk selisih berpasangan per replikasi (benih replikasi sama di semua sel);
efek utama dan interaksi: bootstrap berpasangan atas replikasi (10.000 kali, benih tetap).

Pakai (dari folder proyek kausal_idhs, sesudah ulang_sel_kode_lama.py untuk kedua label):
    python naskah/03_reproduksibilitas/skrip/analisis_2x2_mc.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROYEK = ROOT.parents[1]
T = ROOT / "tabel"
RIW = PROYEK / "naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run"
baca = lambda f: pd.read_csv(f, float_precision="round_trip")
Z = 1.959963984540054


def wilson(k, n):
    if n == 0:
        return np.nan, np.nan
    p = k / n; d = 1 + Z ** 2 / n
    c = (p + Z ** 2 / (2 * n)) / d; h = Z * np.sqrt(p * (1 - p) / n + Z ** 2 / (4 * n * n)) / d
    return c - h, c + h


def newcombe_berpasangan(x1, x2):
    """CI 95% untuk p1 - p2 dari dua indikator biner berpasangan (Newcombe 1998, metode 10)."""
    x1, x2 = np.asarray(x1, bool), np.asarray(x2, bool); n = len(x1)
    a = int((x1 & x2).sum()); b = int((x1 & ~x2).sum()); c = int((~x1 & x2).sum()); d = n - a - b - c
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n); l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = (a * d - b * c) / np.sqrt(den) if den > 0 else 0.0
    dl = np.sqrt(max((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0))
    de = np.sqrt(max((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0))
    return p1 - p2, p1 - p2 - dl, p1 - p2 + de


def nol(d):
    """Indikator efek dinihilkan per (skenario, metode, rep)."""
    return d.assign(nol=(d.RD_hat == 0)).set_index(["skenario", "metode", "rep"]).nol


if __name__ == "__main__":
    S = {}
    S["lama_benar"] = nol(baca(T / "E4_sel4/lama_cfgbenar/per_rep.csv"))
    S["baru_lama"] = nol(baca(T / "E4_config_lama/per_rep_config_lama.csv"))
    r4 = baca(PROYEK / "hasil/benchmark/sanitasi_diare/per_rep.csv")
    rb = baca(T / "E5_run3_tier2/per_rep_B_tier2.csv")
    S["baru_benar"] = nol(pd.concat([r4[r4.skenario == "A"], rb]))
    val = baca(T / "E4_sel4/lama_cfglama/per_rep.csv")
    S["lama_lama"] = nol(val)
    # validasi: ringkasan run validasi vs run 1b dan per replikasi vs run 2 (161 tugas, konfigurasi basi)
    b1 = json.loads((T / "E4_sel4/lama_cfglama/meta.json").read_text(encoding="utf-8"))["ringkas"]
    r2 = baca(RIW / "run2_2026-10-10_terhenti/per_rep.csv")
    m2 = val.merge(r2, on=["skenario", "metode", "rep"], suffixes=("_v", "_r2"))
    num = ["RD_hat", "RD_lo", "RD_hi", "SHD", "SID"]
    sel2 = np.nanmax(np.abs(m2[[f"{k}_v" for k in num]].to_numpy(float) - m2[[f"{k}_r2" for k in num]].to_numpy(float)), axis=1)
    validasi = dict(ringkas_vs_acuan=b1, run2_baris=len(m2), run2_identik_1e12=int((np.nan_to_num(sel2) <= 1e-12).sum()),
                    run2_selisih_maks=float(np.nanmax(sel2)) if len(sel2) else None,
                    run2_efek_nol_sama=int((m2.RD_hat_v.eq(0) == m2.RD_hat_r2.eq(0)).sum()))
    (T / "E4_2x2_validasi.json").write_text(json.dumps(validasi, indent=1, default=str), encoding="utf-8")
    print(json.dumps(validasi, indent=1, default=str))

    idx = S["baru_benar"].index
    for k in S:
        assert set(S[k].index) == set(idx), k
    rng = np.random.default_rng(2017)
    rows = []
    for (sk, me), _ in S["baru_benar"].groupby(level=[0, 1], sort=False):
        X = {k: S[k].loc[(sk, me)].sort_index().to_numpy() for k in S}
        n = len(X["baru_benar"])
        p = {k: X[k].mean() for k in X}
        r = dict(skenario=sk, metode=me, n=n, **{f"p_{k}": p[k] for k in X})
        for nama, (u, v) in {"konfig|kode_baru": ("baru_benar", "baru_lama"), "konfig|kode_lama": ("lama_benar", "lama_lama"),
                             "kode|konfig_benar": ("baru_benar", "lama_benar"), "kode|konfig_basi": ("baru_lama", "lama_lama")}.items():
            dlt, lo, hi = newcombe_berpasangan(X[u], X[v])
            r[f"{nama}"], r[f"{nama}_lo"], r[f"{nama}_hi"] = dlt, lo, hi
        # efek utama dan interaksi + bootstrap berpasangan atas replikasi
        def efek(ix):
            q = {k: X[k][ix].mean() for k in X}
            return ((q["baru_benar"] - q["lama_benar"] + q["baru_lama"] - q["lama_lama"]) / 2,
                    (q["baru_benar"] - q["baru_lama"] + q["lama_benar"] - q["lama_lama"]) / 2,
                    (q["baru_benar"] - q["baru_lama"]) - (q["lama_benar"] - q["lama_lama"]))
        e0 = efek(np.arange(n))
        bs = np.array([efek(rng.integers(0, n, n)) for _ in range(10000)])
        for j, nama in enumerate(("utama_kode", "utama_konfig", "interaksi")):
            r[nama] = e0[j]; r[f"{nama}_lo"], r[f"{nama}_hi"] = np.percentile(bs[:, j], [2.5, 97.5])
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv(T / "E4_2x2_efek_nol.csv", index=False)
    with pd.option_context("display.float_format", "{:.3f}".format, "display.width", 250):
        print(R[["skenario", "metode", "p_lama_lama", "p_lama_benar", "p_baru_lama", "p_baru_benar",
                 "utama_kode", "utama_kode_lo", "utama_kode_hi", "utama_konfig", "utama_konfig_lo", "utama_konfig_hi",
                 "interaksi", "interaksi_lo", "interaksi_hi"]].to_string())
