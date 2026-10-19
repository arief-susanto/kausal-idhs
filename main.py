"""Titik masuk.
  python main.py            -> buka tampilan Streamlit di browser (menu di kiri, proses di kanan)
  python main.py prep|eda|kausal|dag|baseline|sd_hybrid|to_dag|mlc_dag|sol|sol_v2|benchmark|narasi|laporan|semua [nama_analisis]   -> jalankan tanpa tampilan
Setiap langkah menambahkan ringkasan pendek ke hasil/RINGKASAN.txt.
Untuk diskusi dengan AI, cukup tempelkan isi RINGKASAN.txt (hemat token)."""
import subprocess
import sys
import time
import config as C


def log(lines):
    C.OUT.mkdir(exist_ok=True)
    with open(C.OUT / "RINGKASAN.txt", "a", encoding="utf-8") as f:
        f.write(f"# {time.strftime('%Y-%m-%d %H:%M')}\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))


def main(step, nama=None):
    import prep, eda, causal
    if step in ("prep", "semua"):
        log(prep.run())
    if step in ("eda", "semua"):
        log(eda.run(prep.load()))
    if step == "dag":
        log(causal.cek_dag(nama))
    if step in ("kausal", "semua"):
        log(causal.run(prep.load(), nama))
    if step == "baseline":
        import baseline
        log(baseline.run(prep.load(), nama))
    if step in ("sd_hybrid", "to_dag", "mlc_dag"):
        import novelty
        log(novelty.run(prep.load(), step, nama, simulasi=(step == "sd_hybrid")))
    if step == "sol":
        import sol_dag
        log(sol_dag.run(prep.load(), nama))
    if step == "sol_v2":
        import sol_dag
        log(sol_dag.run_v2(prep.load(), nama))
    if step == "benchmark":
        import benchmark
        log(benchmark.run(prep.load(), nama or "sanitasi_diare"))
    if step == "laporan":
        import laporan
        for k in list(laporan.BAGIAN) + ["lengkap"]:
            laporan.buat_menu(k)
            print(f"Laporan Word ditulis ke {laporan.berkas(k)}")
    if step == "narasi":
        import narasi
        (C.OUT / "NARASI.md").write_text(narasi.semua(prep.load()), encoding="utf-8")
        print(f"Narasi seluruh menu ditulis ke {C.OUT / 'NARASI.md'}")


def tampilan():
    """Buka app.py dengan Python dari .venv (walau main.py dipanggil dengan Python lain)."""
    py = C.ROOT / ".venv" / "Scripts" / "python.exe"
    py = str(py) if py.exists() else sys.executable
    print("Membuka tampilan di browser... (tutup jendela ini atau tekan Ctrl+C untuk berhenti)")
    try:
        subprocess.run([py, "-m", "streamlit", "run", str(C.ROOT / "app.py")], cwd=C.ROOT)
    except KeyboardInterrupt:
        pass


def di_streamlit():
    try:
        from streamlit import runtime
        return runtime.exists()
    except ImportError:
        return False


if __name__ == "__main__":
    if di_streamlit():          # "streamlit run main.py" -> tampilkan app.py langsung, tanpa server kedua
        import runpy
        if sys.version_info < (3, 10):  # Streamlit global (Python lama) tak bisa membaca cache pandas dari .venv
            import streamlit as st
            st.error(f"Streamlit berjalan dengan Python {sys.version.split()[0]} ({sys.executable}). "
                     "Proyek ini butuh Python dari .venv. Jalankan `jalankan_app.bat` atau "
                     "`.venv\\Scripts\\python.exe main.py`.")
            st.stop()
        runpy.run_path(str(C.ROOT / "app.py"), run_name="__main__")
    elif len(sys.argv) > 1:
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        tampilan()
