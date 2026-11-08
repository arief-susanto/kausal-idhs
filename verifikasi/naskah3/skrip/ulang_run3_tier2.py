"""Uji kunci E5: jalankan ulang SELURUH skenario B benchmark semi-sintetik (100 replikasi) dengan konfigurasi sekarang
tetapi TIER['hambatan_biaya'] = 2 (nilai saat run 3, 10-11 Okt 2026), lalu bandingkan ringkasannya dengan run 3.
Kode benchmark/baseline/novelty/sol_dag tidak berubah sejak commit 74eb7a4 (run 3), dan satu-satunya perubahan
config.py sesudahnya adalah blok Fase 3 (commit 98841d0) yang menaikkan tier ke 3. Bila hasil sama dengan run 3,
perubahan tier menjelaskan seluruh selisih run 3 vs run 4 (termasuk SID 9,5).

Semua luaran ditulis ke tabel/E5_run3_tier2/ (hasil/ tidak disentuh).
Pakai (dari folder proyek kausal_idhs):  python naskah_ke_2/03_reproduksibilitas/skrip/ulang_run3_tier2.py [--pekerja 3]
"""
import argparse
import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

warnings.filterwarnings("ignore")
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "1"
ROOT = Path(__file__).resolve().parents[1]
PROYEK = ROOT.parents[1]
sys.path.insert(0, str(PROYEK)); os.chdir(PROYEK)
OUT = ROOT / "tabel" / "E5_run3_tier2"
RUN3 = PROYEK / "naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run/run3_2026-10-10_11_dilaporkan/ringkasan.csv"
RUN4 = PROYEK / "hasil/benchmark/sanitasi_diare/ringkasan.csv"
TIER_RUN3 = 2


def _init(kt):
    import config as C
    import benchmark as BM
    C.TIER["hambatan_biaya"] = TIER_RUN3                    # proses pekerja mengimpor config.py baru (tier 3)
    BM.folder = lambda nama: OUT
    BM.KTX.update(kt)


def _satu(t):
    import benchmark as BM
    return BM.satu(t)


def ringkas_B(d):
    import numpy as np
    import pandas as pd
    import benchmark as BM
    d = d.copy()
    d["galat"] = d.RD_hat - d.RD_benar
    d["cakup"] = (d.RD_lo <= d.RD_benar) & (d.RD_benar <= d.RD_hi)
    rows = []
    for (s, m), g in d.groupby(["skenario", "metode"], sort=False):
        st = BM._stabil(g)
        lo, hi = BM._wilson(int(g.cakup.sum()), int(g.RD_lo.notna().sum()))
        rows.append(dict(skenario=s, metode=m, rep=len(g), SHD=g.SHD.mean(), SID=g.SID.mean(),
                         RMSE=np.sqrt((g.galat ** 2).mean()), bias=g.galat.mean(), sd_RD=g.RD_hat.std(),
                         efek_nol=(g.RD_hat == 0).mean(), cakupan=g.cakup.mean() if g.RD_lo.notna().any() else np.nan,
                         cakupan_lo=lo, cakupan_hi=hi, stabilitas_SHD=st.mean() if len(st) else np.nan,
                         langkah=g.langkah.mean(), sisi=g.sisi.mean()))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--pekerja", type=int, default=3); a.add_argument("--rep", type=int, default=100)
    a = a.parse_args()
    import numpy as np
    import pandas as pd
    import config as C
    import benchmark as BM
    OUT.mkdir(parents=True, exist_ok=True)
    BM.folder = lambda nama: OUT                             # graf_benar_* ditulis ke sini, bukan ke hasil/
    C.TIER["hambatan_biaya"] = TIER_RUN3
    t0 = time.time()
    df = pd.read_pickle(C.CACHE / "analisis.pkl")
    kt, meta = BM.siapkan(df, "sanitasi_diare")             # A juga disiapkan agar urutan rng sama dengan run 3
    tugas = [("B", r) for r in range(a.rep)]
    f_rep = OUT / "per_rep_B_tier2.csv"; f_rep.unlink(missing_ok=True)
    selesai = 0
    with ProcessPoolExecutor(max_workers=a.pekerja, initializer=_init, initargs=(kt,)) as ex:
        fut = {ex.submit(_satu, t): t for t in tugas}
        for f in as_completed(fut):
            baris, _ = f.result()
            pd.DataFrame(baris).to_csv(f_rep, mode="a", index=False, header=not f_rep.exists())
            selesai += 1
            print(f"{selesai}/{len(tugas)} ({(time.time() - t0) / 60:.1f} menit)", flush=True)
    d = pd.read_csv(f_rep, float_precision="round_trip")
    R = ringkas_B(d); R.to_csv(OUT / "ringkasan_B_tier2.csv", index=False)
    # banding dengan run 3 (tier 2) dan run 4 (tier 3); kolom waktu/memori dikecualikan
    KOL = ["SHD", "SID", "RMSE", "bias", "sd_RD", "efek_nol", "cakupan", "stabilitas_SHD", "langkah", "sisi"]
    baris = []
    for lab, f in (("run3", RUN3), ("run4", RUN4)):
        X = pd.read_csv(f, float_precision="round_trip"); X = X[X.skenario == "B"]
        m = R.merge(X, on=["skenario", "metode"], suffixes=("", f"_{lab}"))
        for _, r in m.iterrows():
            for k in KOL:
                x, y = r[k], r[f"{k}_{lab}"]
                baris.append(dict(acuan=lab, metode=r.metode, metrik=k, tier2_ulang=x, acuan_nilai=y,
                                  selisih=(abs(x - y) if pd.notna(x) and pd.notna(y) else (0.0 if pd.isna(x) and pd.isna(y) else np.nan))))
    B = pd.DataFrame(baris); B.to_csv(OUT / "banding_run3_run4.csv", index=False)
    rk = B.groupby("acuan").agg(sel=("selisih", "size"), identik_1e12=("selisih", lambda s: int((s <= 1e-12).sum())),
                                selisih_maks=("selisih", "max"))
    meta_out = dict(tier=TIER_RUN3, rep=a.rep, pekerja=a.pekerja, menit=round((time.time() - t0) / 60, 1),
                    RD_benar_B=meta["B"]["RD_benar"], RD_benar_B_run3=json.loads(RUN3.with_name("meta.json").read_text())["B"]["RD_benar"],
                    ringkas=rk.reset_index().to_dict("records"))
    (OUT / "meta.json").write_text(json.dumps(meta_out, indent=1, default=str), encoding="utf-8")
    print(rk.to_string()); print(json.dumps(meta_out, indent=1, default=str))
