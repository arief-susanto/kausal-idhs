"""Review 14-11-2026: penjaga runtime D1r dijalankan pada kesalahan E8 (tanpa D3 yang mahal), agar Tabel injeksi lengkap.
Pakai (dari folder proyek kausal_idhs): python naskah/03_reproduksibilitas/skrip/d1r_e8.py
Keluaran: naskah/03_reproduksibilitas/tabel/E8_d1r.csv
"""
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import injeksi_kesalahan as I  # noqa: E402
from injeksi_eksternal import d1r  # noqa: E402
import pandas as pd

baris = []
for nama, f in I.KESALAHAN.items():
    sb = I.buat_sandbox()
    if f:
        f(sb)
    baris.append(dict(kesalahan=nama, D1r=d1r(sb, None))); print(baris[-1], flush=True)
    shutil.rmtree(sb, ignore_errors=True)
pd.DataFrame(baris).to_csv(I.ROOT / "tabel" / "E8_d1r.csv", index=False)
