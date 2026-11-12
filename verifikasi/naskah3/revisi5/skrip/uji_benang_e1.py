"""Butir 7 catatan perbaikan: uji penyebab pergeseran tingkat bit E1 (run ulang benchmark v4 vs hasil asli).

Hipotesis: run asli bench_v4.py menetapkan OMP/OPENBLAS/MKL_NUM_THREADS=1 sebelum membuat proses pekerja,
sedangkan ulang_bench_v4.py (label venv, venv_ulang2) tidak, sehingga pekerjanya memakai BLAS multi-utas.
Uji: jalankan ulang tugas yang sama dengan utas dikunci ke 1 SEBELUM numpy dimuat (juga di proses pekerja,
karena variabel lingkungan diwarisi), lalu bandingkan dengan hasil asli (bandingkan_benang_e1.py).

Pakai (dari folder proyek kausal_idhs):
    python naskah/03_reproduksibilitas/skrip/uji_benang_e1.py --label venv_benang1 --rep 0 1 2 --pekerja 2
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

PROYEK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROYEK)); os.chdir(PROYEK)
warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import bench_v4 as B  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tabel" / "E7_ulang"


def kerja(t):
    warnings.filterwarnings("ignore")
    return B.satu(t)


def info_blas():
    try:
        from threadpoolctl import threadpool_info
        return [{k: i.get(k) for k in ("internal_api", "num_threads", "version")} for i in threadpool_info()]
    except Exception as e:  # threadpoolctl tidak wajib
        return str(e)


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--label", required=True)
    a.add_argument("--rep", type=int, nargs="+", default=[0]); a.add_argument("--pekerja", type=int, default=2)
    a = a.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tugas = [(s, r) for r in a.rep for s in B.sel_list()]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.pekerja) as ex:
        baris = [b for hasil in ex.map(kerja, tugas) for b in hasil]
    pd.DataFrame(baris).to_csv(OUT / f"per_rep_{a.label}.csv", index=False)
    meta = dict(label=a.label, utas={v: os.environ[v] for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                blas=info_blas(), python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                tugas=len(tugas), baris=len(baris), rep=a.rep, menit=round((time.time() - t0) / 60, 1))
    (OUT / f"meta_{a.label}.json").write_text(json.dumps(meta, indent=1, default=str))
    print(meta)
