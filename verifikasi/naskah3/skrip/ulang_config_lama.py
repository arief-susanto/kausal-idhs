"""Uji pemisah E4: jalankan benchmark semi-sintetik v1 (skenario A dan B, 100 replikasi) dengan KODE SEKARANG
(sesudah audit A1-A6) tetapi seluruh nilai config_old yang berbeda dari config.py (12 parameter; benchmark membaca 7)
dan tier hambatan_biaya = 2 (sama di config_old dan saat run 3).

  - banding dengan run 3 (config benar + kode sesudah audit)  -> selisih = efek konfigurasi basi saja
  - banding dengan run 1b (config_old + kode sebelum audit)    -> selisih = efek perubahan kode (A4-A6 dan
    perubahan kode lain sejak 27-09-2026)

Semua luaran ditulis ke tabel/E4_config_lama/ (hasil/ tidak disentuh).
Pakai (dari folder proyek kausal_idhs):  python naskah_ke_2/03_reproduksibilitas/skrip/ulang_config_lama.py [--pekerja 4]
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
OUT = ROOT / "tabel" / "E4_config_lama"
RIWAYAT = PROYEK / "naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run"
ACUAN = {"run3": RIWAYAT / "run3_2026-10-10_11_dilaporkan/ringkasan.csv",
         "run1b": RIWAYAT / "run1_2026-09-27/ringkasan.csv"}
BLOK = ["BASELINE", "NOVELTY", "SOL", "SOL_V2", "BENCH"]
DIBACA_BENCHMARK = {("BASELINE", "alpha"), ("BASELINE", "skor"), ("NOVELTY", "sd_alpha"), ("NOVELTY", "sd_skor"),
                    ("NOVELTY", "to_skor"), ("SOL", "alpha"), ("BENCH", "n_populasi")}


def pasang_config_lama():
    """Timpa nilai config.py yang berbeda dengan nilai config_old; kembalikan daftar perubahan."""
    import config as C
    import config_old as O
    beda = []
    for b in BLOK:
        baru, lama = getattr(C, b), getattr(O, b, {})
        for k in sorted(set(baru) & set(lama)):
            if baru[k] != lama[k]:
                beda.append(dict(blok=b, kunci=k, config_sekarang=baru[k], config_old=lama[k],
                                 dibaca_benchmark=(b, k) in DIBACA_BENCHMARK))
                baru[k] = lama[k]
    C.TIER["hambatan_biaya"] = O.TIER["hambatan_biaya"]
    return beda


def _init(kt):
    pasang_config_lama()                                    # sebelum benchmark dipakai; semua dibaca saat jalan
    import benchmark as BM
    BM.folder = lambda nama: OUT
    BM.KTX.update(kt)


def _satu(t):
    import benchmark as BM
    return BM.satu(t)


def ringkas(d):
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
    a = argparse.ArgumentParser(); a.add_argument("--pekerja", type=int, default=4); a.add_argument("--rep", type=int, default=100)
    a = a.parse_args()
    import numpy as np
    import pandas as pd
    beda = pasang_config_lama()
    import config as C
    import benchmark as BM
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(beda).to_csv(OUT / "config_lama_dipasang.csv", index=False)
    BM.folder = lambda nama: OUT                             # graf_benar_* ditulis ke sini, bukan ke hasil/
    t0 = time.time()
    df = pd.read_pickle(C.CACHE / "analisis.pkl")
    kt, meta = BM.siapkan(df, "sanitasi_diare")
    tugas = [(s, r) for s in ("A", "B") for r in range(a.rep)]
    f_rep = OUT / "per_rep_config_lama.csv"; f_rep.unlink(missing_ok=True)
    selesai = 0
    with ProcessPoolExecutor(max_workers=a.pekerja, initializer=_init, initargs=(kt,)) as ex:
        fut = {ex.submit(_satu, t): t for t in tugas}
        for f in as_completed(fut):
            baris, _ = f.result()
            pd.DataFrame(baris).to_csv(f_rep, mode="a", index=False, header=not f_rep.exists())
            selesai += 1
            print(f"{selesai}/{len(tugas)} ({(time.time() - t0) / 60:.1f} menit)", flush=True)
    d = pd.read_csv(f_rep, float_precision="round_trip")
    R = ringkas(d); R.to_csv(OUT / "ringkasan_config_lama.csv", index=False)
    KOL = ["SHD", "SID", "RMSE", "bias", "sd_RD", "efek_nol", "cakupan", "stabilitas_SHD", "langkah", "sisi"]
    baris = []
    for lab, f in ACUAN.items():
        X = pd.read_csv(f, float_precision="round_trip")
        m = R.merge(X, on=["skenario", "metode"], suffixes=("", f"_{lab}"))
        for _, r in m.iterrows():
            for k in KOL:
                if f"{k}_{lab}" not in m:
                    continue
                x, y = r[k], r[f"{k}_{lab}"]
                baris.append(dict(acuan=lab, skenario=r.skenario, metode=r.metode, metrik=k, config_lama=x, acuan_nilai=y,
                                  selisih=(abs(x - y) if pd.notna(x) and pd.notna(y) else (0.0 if pd.isna(x) and pd.isna(y) else np.nan))))
    B = pd.DataFrame(baris); B.to_csv(OUT / "banding_run3_run1b.csv", index=False)
    rk = B.groupby("acuan").agg(sel=("selisih", "size"), identik_1e12=("selisih", lambda s: int((s <= 1e-12).sum())),
                                selisih_maks=("selisih", "max"))
    meta_out = dict(tier=int(C.TIER["hambatan_biaya"]), rep=a.rep, pekerja=a.pekerja, menit=round((time.time() - t0) / 60, 1),
                    parameter_dipasang=len(beda), parameter_dibaca_benchmark=sum(b["dibaca_benchmark"] for b in beda),
                    RD_benar={s: meta[s]["RD_benar"] for s in meta},
                    ringkas=rk.reset_index().to_dict("records"))
    (OUT / "meta.json").write_text(json.dumps(meta_out, indent=1, default=str), encoding="utf-8")
    print(rk.to_string()); print(json.dumps(meta_out, indent=1, default=str))
