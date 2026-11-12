"""Butir 5 catatan perbaikan: lengkapi desain 2x2 E4 (kode x konfigurasi) dengan sel KODE LAMA.

Kode lama = tag pra-audit (snapshot sebelum audit A1-A6), diekstrak ke folder terpisah dengan `git archive`.
Dua label:
  - lama_cfgbenar : kode pra-audit + konfigurasi benar (config.py commit 74eb7a4 = konfigurasi run 3, tier
                    hambatan_biaya = 2) dipasang sebagai config_old.py dan config.py  -> sel keempat
  - lama_cfglama  : kode pra-audit apa adanya (config_old)                           -> validasi bahwa kode
                    pra-audit memang mereproduksi run 1b (run 1b tidak menyimpan per replikasi)
Sel lain sudah ada: run 1b (lama, lama), run gabungan (baru, lama; tabel/E4_config_lama), run 3 (baru, benar).

Data dibaca dari cache proyek utama; semua luaran ke tabel/E4_sel4/<label>/ (hasil/ tidak disentuh).
Pakai (dari folder proyek kausal_idhs):
    git archive pra-audit | tar -x -C <DIR>          # lalu untuk lama_cfgbenar: git show 74eb7a4:config.py > <DIR>/config_old.py
    python naskah/03_reproduksibilitas/skrip/ulang_sel_kode_lama.py --kode <DIR> --label lama_cfgbenar [--pekerja 4]
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
RIWAYAT = PROYEK / "naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run"
ACUAN = {"run1b": RIWAYAT / "run1_2026-09-27/ringkasan.csv",
         "gabungan": ROOT / "tabel/E4_config_lama/ringkasan_config_lama.csv",
         "run3": RIWAYAT / "run3_2026-10-10_11_dilaporkan/ringkasan.csv"}
KOL = ["SHD", "SID", "RMSE", "bias", "sd_RD", "efek_nol", "cakupan", "stabilitas_SHD", "langkah", "sisi"]


def _pakai_kode(kode):
    sys.path.insert(0, str(kode))


def _init(kode, kt, out):
    _pakai_kode(kode)
    import benchmark as BM
    BM.folder = lambda nama: out
    BM.KTX.update(kt)


def _satu(t):
    import benchmark as BM
    return BM.satu(t)


def ringkas(d, BM):
    """Sama dengan ringkas() di ulang_config_lama.py (run gabungan), memakai _stabil/_wilson kode yang dijalankan."""
    import numpy as np
    import pandas as pd
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
    a = argparse.ArgumentParser()
    a.add_argument("--kode", required=True); a.add_argument("--label", required=True)
    a.add_argument("--pekerja", type=int, default=4); a.add_argument("--rep", type=int, default=100)
    a = a.parse_args()
    kode = Path(a.kode).resolve()
    _pakai_kode(kode)
    import numpy as np
    import pandas as pd
    import benchmark as BM
    import config_old as C
    assert Path(BM.__file__).resolve().parent == kode, BM.__file__
    out = ROOT / "tabel/E4_sel4" / a.label
    out.mkdir(parents=True, exist_ok=True)
    BM.folder = lambda nama: out
    t0 = time.time()
    df = pd.read_pickle(PROYEK / "cache/analisis.pkl")
    kt, meta = BM.siapkan(df, "sanitasi_diare")
    tugas = [(s, r) for s in ("A", "B") for r in range(a.rep)]
    f_rep = out / "per_rep.csv"; f_rep.unlink(missing_ok=True)
    selesai = 0
    with ProcessPoolExecutor(max_workers=a.pekerja, initializer=_init, initargs=(str(kode), kt, out)) as ex:
        fut = {ex.submit(_satu, t): t for t in tugas}
        for f in as_completed(fut):
            baris, _ = f.result()
            pd.DataFrame(baris).to_csv(f_rep, mode="a", index=False, header=not f_rep.exists())
            selesai += 1
            print(f"{selesai}/{len(tugas)} ({(time.time() - t0) / 60:.1f} menit)", flush=True)
    d = pd.read_csv(f_rep, float_precision="round_trip")
    R = ringkas(d, BM); R.to_csv(out / "ringkasan.csv", index=False)
    baris = []
    for lab, f in ACUAN.items():
        X = pd.read_csv(f, float_precision="round_trip")
        m = R.merge(X, on=["skenario", "metode"], suffixes=("", f"_{lab}"))
        for _, r in m.iterrows():
            for k in KOL:
                if f"{k}_{lab}" not in m:
                    continue
                x, y = r[k], r[f"{k}_{lab}"]
                baris.append(dict(acuan=lab, skenario=r.skenario, metode=r.metode, metrik=k, nilai=x, acuan_nilai=y,
                                  selisih=(abs(x - y) if pd.notna(x) and pd.notna(y)
                                           else (0.0 if pd.isna(x) and pd.isna(y) else np.nan))))
    B = pd.DataFrame(baris); B.to_csv(out / "banding.csv", index=False)
    rk = B.groupby("acuan").agg(sel=("selisih", "size"), identik_1e12=("selisih", lambda s: int((s <= 1e-12).sum())),
                                selisih_maks=("selisih", "max"))
    meta_out = dict(label=a.label, kode=str(kode), tier=int(C.TIER["hambatan_biaya"]),
                    alpha=C.BASELINE.get("alpha"), skor=C.BASELINE.get("skor"), n_populasi=C.BENCH.get("n_populasi"),
                    rep=a.rep, pekerja=a.pekerja, menit=round((time.time() - t0) / 60, 1),
                    RD_benar={s: meta[s]["RD_benar"] for s in meta}, ringkas=rk.reset_index().to_dict("records"))
    (out / "meta.json").write_text(json.dumps(meta_out, indent=1, default=str), encoding="utf-8")
    print(rk.to_string()); print(json.dumps(meta_out, indent=1, default=str))
