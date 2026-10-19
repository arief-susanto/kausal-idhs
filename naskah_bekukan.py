"""Bekukan keluaran yang dipakai naskah: salin dari hasil/ ke naskah/data/ (struktur folder sama).
Setelah ini naskah_bahan.py dan naskah_tulis.py membaca naskah/data/, sehingga menjalankan ulang menu apa pun di
aplikasi (yang menimpa hasil/) TIDAK mengubah angka naskah. Jalankan lagi hanya bila naskah memang mau diperbarui.
Jalankan:  python naskah_bekukan.py"""
import shutil
import config as C

BEKU = C.ROOT / "naskah" / "data"
NASKAH = ["sanitasi_diare", "sanitasi_diare_ctps", "pbi_diare", "pbi_diare_biaya"]
POLA = (["benchmark_v4/per_rep.csv", "benchmark_v4/ringkasan.csv", "benchmark_v4/hipotesis.csv", "benchmark_v4/meta.json",
         "tanpa_trim/kausal/sanitasi_diare/estimasi.csv", "tanpa_trim/kausal/sanitasi_diare/adjustment.txt"]
        + [f"novelty/sd_hybrid/{n}/sd_uji.csv" for n in list(C.ANALISIS)[:4]]
        + [f"idhs_m0m6/{n}/{f}" for n in ("sanitasi_diare", "pbi_diare") for f in ("rd.csv", "forest.png")]
        + [f"kausal/{n}/{f}" for n in NASKAH for f in ("estimasi.csv", "keseimbangan.csv", "adjustment.txt", "dag.png", "overlap.png")]
        + [f"baseline/{n}/rangkuman.csv" for n in NASKAH] + [f"sol_dag/{n}/sol_v2.csv" for n in NASKAH])

if __name__ == "__main__":
    for rel in POLA:
        src, dst = C.OUT / rel, BEKU / rel
        if not src.exists():
            raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    import json, prep
    df = prep.load()                                                    # ukuran populasi analisis (teks 2.7)
    (BEKU / "populasi.json").write_text(json.dumps(dict(lahir=len(df), psu=int(df.groupby(['strata', 'psu']).ngroups),
                                                        strata=int(df.strata.nunique()))), encoding="utf-8")
    print(f"{len(POLA) + 1} file dibekukan ke {BEKU}")
