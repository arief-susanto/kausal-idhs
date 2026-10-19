"""Jalankan: python run_bench.py [reps] [pekerja]. Grid skenario = pra-registrasi v2 (ubah SEBELUM menjalankan).
pekerja > 1 menjalankan sel grid secara paralel (hasil identik dengan berurutan: seed per replikasi tetap)."""
import os, sys
from concurrent.futures import ProcessPoolExecutor
from sol_v2 import benchmark, ringkas

GRID = [dict(icc=0.05, beta_ty=-0.6), dict(icc=0.4, beta_ty=-0.6),
        dict(icc=0.05, beta_ty=-0.15), dict(icc=0.4, beta_ty=-0.15),   # efek kecil ~ kasus IDHS (RD sekitar -0,02)
        dict(icc=0.05, beta_ty=0.0), dict(icc=0.4, beta_ty=0.0)]       # efek nol = uji galat tipe I pada efek
# Grid = pra-registrasi v2: ICC {0,05; 0,4} x beta_ty {-0,6; -0,15; 0} (6 sel)


def sel(arg):
    sim, reps = arg
    tab, t1, pw, df = benchmark(reps=reps, **sim)
    df.to_csv(f"hasil_{sim['icc']}_{sim['beta_ty']}.csv", index=False)
    return ringkas(tab, t1, pw, sim)


if __name__ == "__main__":
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    pekerja = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    tugas = [(sim, reps) for sim in GRID]
    if pekerja > 1:
        with ProcessPoolExecutor(max_workers=pekerja) as ex:
            out = list(ex.map(sel, tugas))
    else:
        out = [sel(t) for t in tugas]
    for s in out:
        print(s + "\n")
    open("RINGKASAN_v2.txt", "w", encoding="utf-8").write("\n\n".join(out))
