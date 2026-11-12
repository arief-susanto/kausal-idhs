"""Butir 2 catatan perbaikan: apakah drift CI bootstrap aplikasi (E3) berasal dari benih per proses?

causal.run() membuat SATU aliran acak default_rng(C.SEED) yang dipakai bergiliran oleh semua analisis, sehingga
CI suatu analisis bergantung pada analisis apa yang dijalankan sebelumnya dalam proses yang sama.
Empat skema dihitung dengan langkah yang sama persis dengan causal.run() (tanpa menulis ke hasil/):
  S1 aliran_semua   : satu aliran, semua analisis berurutan    (kode lama, menu "semua")
  S2 aliran_sendiri : aliran baru per analisis yang dijalankan  (kode lama, menu satu analisis)
  S3 benih_unit     : default_rng([SEED, crc32(nama)]) per analisis, urutan normal   (perbaikan)
  S4 benih_unit_bal : sama dengan S3, urutan analisis dibalik    (uji ketakbergantungan pada komposisi run)
Lalu CI dibandingkan dengan salinan beku (naskah/01 Resti/data/kausal) dan hasil aktif (hasil/kausal).

Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/uji_bootstrap_benih.py
Keluaran: naskah/03_reproduksibilitas/tabel/E9_bootstrap/
"""
import os
import sys
import time
import zlib
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
ROOT = Path(__file__).resolve().parents[1]
PROYEK = ROOT.parents[1]
sys.path.insert(0, str(PROYEK)); os.chdir(PROYEK)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import causal  # noqa: E402
import config as C  # noqa: E402
import prep  # noqa: E402

OUT = ROOT / "tabel" / "E9_bootstrap"
BEKU = PROYEK / "naskah" / "01 Resti" / "data" / "kausal"
AKTIF = PROYEK / "hasil" / "kausal"


def siapkan(df, n):
    spec = C.ANALISIS[n]
    G = causal.build_dag(spec); T, Y = spec['T'], spec['Y']
    Z, _, _ = causal.adjustment(G, T, Y, spec['laten'])
    d = df.query(spec['filter']) if spec['filter'] else df
    return d.dropna(subset=[T, Y] + Z).reset_index(drop=True), T, Y, Z


def tabel_ci(d, T, Y, Z, rng):
    est, _, _ = causal.estimate(d, T, Y, Z)
    bs = causal.bootstrap(d, T, Y, Z, C.BOOT, rng)
    return pd.DataFrame({'estimasi': est, 'se_boot': bs.std(), 'ci_bawah': bs.quantile(.025), 'ci_atas': bs.quantile(.975)})


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    df = prep.load()
    nama = list(C.ANALISIS)
    data = {n: siapkan(df, n) for n in nama}
    hasil, t0 = {}, time.time()
    rng = np.random.default_rng(C.SEED)                                   # S1
    for n in nama:
        hasil[("S1", n)] = tabel_ci(*data[n], rng); print("S1", n, f"{(time.time() - t0) / 60:.1f} mnt", flush=True)
    for n in nama:                                                        # S2
        hasil[("S2", n)] = tabel_ci(*data[n], np.random.default_rng(C.SEED)); print("S2", n, flush=True)
    for lab, urut in (("S3", nama), ("S4", nama[::-1])):                  # S3, S4
        for n in urut:
            hasil[(lab, n)] = tabel_ci(*data[n], np.random.default_rng([C.SEED, zlib.crc32(n.encode())]))
            print(lab, n, flush=True)
    rows = []
    for (s, n), t in hasil.items():
        t.to_csv(OUT / f"{s}_{n}.csv")
        for acuan, folder in (("beku", BEKU), ("aktif", AKTIF)):
            f = folder / n / "estimasi.csv"
            if not f.exists():
                continue
            a = pd.read_csv(f, index_col=0, float_precision="round_trip")
            b = pd.read_csv(OUT / f"{s}_{n}.csv", index_col=0, float_precision="round_trip")
            rows.append(dict(skema=s, analisis=n, acuan=acuan,
                             estimasi_identik=bool((a.estimasi == b.estimasi).all()),
                             ci_identik_bit=bool(((a.ci_bawah == b.ci_bawah) & (a.ci_atas == b.ci_atas)).all()),
                             ci_selisih_maks=float(np.nanmax(np.abs(np.r_[a.ci_bawah - b.ci_bawah, a.ci_atas - b.ci_atas])))))
    # S3 vs S4: CI suatu analisis harus sama walau komposisi/urutan run berbeda
    for n in nama:
        a, b = hasil[("S3", n)], hasil[("S4", n)]
        rows.append(dict(skema="S3 vs S4", analisis=n, acuan="urutan dibalik",
                         estimasi_identik=bool((a.estimasi == b.estimasi).all()),
                         ci_identik_bit=bool(((a.ci_bawah == b.ci_bawah) & (a.ci_atas == b.ci_atas)).all()),
                         ci_selisih_maks=float(np.nanmax(np.abs(np.r_[a.ci_bawah - b.ci_bawah, a.ci_atas - b.ci_atas])))))
        a, b = hasil[("S1", n)], hasil[("S2", n)]
        rows.append(dict(skema="S1 vs S2", analisis=n, acuan="semua vs sendiri",
                         estimasi_identik=bool((a.estimasi == b.estimasi).all()),
                         ci_identik_bit=bool(((a.ci_bawah == b.ci_bawah) & (a.ci_atas == b.ci_atas)).all()),
                         ci_selisih_maks=float(np.nanmax(np.abs(np.r_[a.ci_bawah - b.ci_bawah, a.ci_atas - b.ci_atas])))))
    R = pd.DataFrame(rows); R.to_csv(OUT / "E9_banding.csv", index=False)
    print(R.to_string()); print(f"selesai {(time.time() - t0) / 60:.1f} menit")
