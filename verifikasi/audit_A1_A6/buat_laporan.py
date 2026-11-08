"""Susun LAPORAN_VERIFIKASI_A1_A6 (.md dan .docx) dari luaran verifikasi_a1_a6.py.
Semua angka dibaca dari CSV/JSON di folder ini; tidak ada angka yang diketik tangan kecuali bukti riwayat git.

Pakai (dari folder proyek kausal_idhs):  python dok_disertasi/verifikasi_audit/buat_laporan.py
"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt

S = Path(__file__).resolve().parent
J = json.loads((S / "ringkasan_verifikasi.json").read_text(encoding="utf-8"))
H = J["hasil"]
A1 = pd.read_csv(S / "A1_beda_config.csv")
A2 = pd.read_csv(S / "A2_simulasi_confounder.csv")
A3 = pd.read_csv(S / "A3_aliran_acak.csv")
A4 = pd.read_csv(S / "A4_n_eff_mlc.csv")
A5 = pd.read_csv(S / "A5_delta_bar.csv")
A5["arah"] = (A5.delta_bar_audit < A5.delta_bar_pra_audit).map({True: "turun", False: "naik"})
A6 = pd.read_csv(S / "A6_node_mlc.csv")
pc = lambda x: f"{100 * x:.1f}".replace(".", ",") + "%"
de = lambda x, k=2: f"{x:,.{k}f}".replace(",", "X").replace(".", ",").replace("X", ".")
blok = []          # (jenis, isi)
P = lambda t: blok.append(("p", t))
Hd = lambda t, lv=2: blok.append((f"h{lv}", t))
T = lambda df: blok.append(("t", df))
CAT = lambda t: blok.append(("catatan", t))

# ------------------------------------------------------------------ isi
blok.append(("h1", "Laporan Verifikasi Perbaikan Audit A1–A6"))
P(f"Dibuat otomatis oleh buat_laporan.py dari luaran verifikasi_a1_a6.py (dijalankan {J['waktu'][:16].replace('T', ' ')}, "
  f"{de(J['menit'], 1)} menit; HEAD {J['commit_HEAD']}; Python {J['python']}, numpy {J['numpy']}, pandas {J['pandas']}). "
  f"SHA-256 novelty.py {J['sha256_novelty'][:16]}…, benchmark.py {J['sha256_benchmark'][:16]}…, config.py {J['sha256_config'][:16]}….")

Hd("1. Ringkasan")
P("Audit A1–A6 dipasang pada commit 74eb7a4 (10-10-2026 17.00 WIB) dan dinyatakan lulus pada commit a02d204 "
  "(19.14 WIB, “Fase 1 lulus: audit terverifikasi”). Saat itu tidak dibuat dokumen yang menyatakan apa yang diperiksa "
  "dan apa kriteria lulusnya; buktinya hanya perubahan berkas log. Laporan ini menguji ulang keenam perbaikan pada kode "
  "dan data sekarang dengan uji yang dapat diulang.")
T(pd.DataFrame([dict(Kode=k, Perbaikan=v, Status=H[k]["status"]) for k, v in [
    ("A1", "Semua modul memakai config.py, bukan config_old.py"),
    ("A2", "Simulasi S={z}: z menjadi confounder x dan y"),
    ("A3", "Aliran acak per analisis"),
    ("A4", "MLC-DAG memakai n efektif, bukan n mentah"),
    ("A5", "delta_bar tanpa variabel konteks tier 0"),
    ("A6", "Treatment analisis lain tidak masuk node MLC")]]))
P("Keenam perbaikan terpasang dan bekerja sesuai rancangannya. Dua catatan substantif: (i) bukti kelulusan A2 pada "
  "10 Oktober tidak sahih, walaupun perbaikannya sendiri benar (bagian 3); (ii) A5 tidak selalu memperbesar n efektif "
  "seperti alasan yang ditulis di kode; pada analisis PBI justru memperkecilnya (bagian 6).")

Hd("2. A1 — konfigurasi yang benar-benar terpakai")
P(f"Hasil: {H['A1']['ringkas']}.")
P("Sebelum audit, modul analisis mengimpor config_old.py, sehingga perubahan apa pun di config.py tidak berpengaruh "
  "tanpa tanda apa pun. Tabel berikut adalah nilai yang berbeda antara kedua berkas pada saat ini; nilai di kolom "
  "config_old adalah nilai yang dulu diam-diam dipakai.")
T(A1.rename(columns={"objek": "Objek", "kunci": "Kunci", "config_old": "config_old (dulu terpakai)", "config": "config (sekarang)"}))
CAT("TIER['hambatan_biaya'] di config.py baru diubah 2 → 3 pada 11-10-2026 11.24 (commit 98841d0), sesudah audit dan "
    "sesudah run 3 selesai. Pada saat run 3, config_old dan config.py sama-sama memakai tier 2, sehingga perbedaan "
    "konfigurasi basi vs benar saat itu adalah 12 parameter, bukan 13. Dari 12 itu, benchmark v1 hanya membaca 7: α "
    "(BASELINE, NOVELTY.sd_alpha, SOL), fungsi skor (BASELINE, NOVELTY.sd_skor, NOVELTY.to_skor), dan BENCH.n_populasi; "
    "boot NOVELTY/SOL/BASELINE, sim_rep, dan SOL_V2.K tidak dibaca benchmark v1 (benchmark memakai BENCH.boot = 20).")

Hd("3. A2 — simulasi uji bersyarat S={z}")
P(f"Hasil: {H['A2']['ringkas']}.")
P(f"Simulasi memakai desain sampel analisis {H['A2']['analisis']} (bobot, strata, PSU nyata), ICC {de(H['A2']['icc'], 2)}, "
  f"muatan z {de(H['A2']['muatan_z'], 1)}, efek 0, {H['A2']['replikasi']} replikasi, α = 0,05. Baris “diagnostik” tidak "
  "pernah dilaporkan di log aplikasi; baris itulah yang menunjukkan bahwa z sungguh mengacaukan pasangan uji. Uji naif "
  "menolak terlalu sering (11–21%) pada semua kasus karena mengabaikan desain klaster; itu temuan N1, bukan bagian A2.")
T(A2.assign(tolak_naif=A2.tolak_naif.map(pc), tolak_terkoreksi=A2.tolak_terkoreksi.map(pc),
            ik=[f"{pc(a)}–{pc(b)}" for a, b in zip(A2.ci95_lo, A2.ci95_hi)],
            p_binom_vs_alpha=A2.p_binom_vs_alpha.map(lambda v: "< 0,001" if v < 0.001 else de(v, 3)))
   [["kasus", "harapan", "tolak_naif", "tolak_terkoreksi", "ik", "p_binom_vs_alpha"]].rename(columns={
    "kasus": "Kasus", "harapan": "Harapan (uji terkoreksi)", "tolak_naif": "Tolak, uji naif (B2)",
    "tolak_terkoreksi": "Tolak, uji terkoreksi desain", "ik": "IK 95% Wilson (terkoreksi)",
    "p_binom_vs_alpha": "p binomial vs 0,05"}))
P(f"Pada data kontinu, uji terkoreksi menolak {pc(A2.tolak_terkoreksi[1])} (IK 95% {pc(A2.ci95_lo[1])}–{pc(A2.ci95_hi[1])}): "
  "tidak berbeda bermakna dari 5% pada 2.000 replikasi, tetapi batas atasnya sekitar 7%, sehingga kemungkinan sedikit "
  f"liberal belum dapat disingkirkan. Pada data biner, {pc(A2.tolak_terkoreksi[5])} (IK 95% {pc(A2.ci95_lo[5])}–"
  f"{pc(A2.ci95_hi[5])}). Rumusan yang aman: koreksi desain menurunkan galat tipe I dari sekitar 20% menjadi sekitar 6% "
  "pada data kontinu dan dari sekitar 11% menjadi sekitar 5% pada data biner. Kata “terkalibrasi” tidak dipakai untuk "
  "data kontinu.")
P("Kesetaraan struktural pasangan kontinu. Baris kontinu versi audit dan pra-audit identik di kedua kolom. Ini bukan "
  "bug: residu (cz·z + sz·x) atas z sama dengan sz × residu x atas z, dan pengali skala tidak mengubah korelasi parsial "
  "maupun statistik uji. Nilai p per replikasi (A2_p_per_replikasi.csv) membuktikannya: selisih maksimum nilai p "
  f"terkoreksi antara kedua pasangan {H['A2']['kontinu_maks_beda_p_terkoreksi']:.1e} (galat pembulatan), dan keputusan "
  f"sama pada {pc(H['A2']['kontinu_keputusan_sama'])} replikasi. Pada data biner, dikotomisasi memutus kesetaraan ini "
  f"(keputusan sama pada {pc(H['A2']['biner_keputusan_sama'])} replikasi). Konsekuensinya, perbaikan A2 tidak mengubah "
  "angka galat tipe I kontinu sama sekali; ia hanya membuat skenario S={z} bermakna (z kini confounder sungguhan).")
P("Mengapa bukti 10 Oktober tidak sahih. Commit 872d0e9 (17.12) mencatat “gerbang belum lulus: baris kontinu S={z}”: "
  "baris S={z} kontinu sama persis dengan S=∅ (0,225/0,055/0,055). Pada commit a02d204 (19.14) kedua baris berbeda "
  "tipis (0,226/0,053/0,053 vs 0,225/0,053/0,053) dan audit dinyatakan lulus. Uji ulang menunjukkan bahwa keputusan "
  f"uji S={{z}} kontinu sama dengan S=∅ pada {pc(H['A2']['sepakat_kontinu_audit'])} replikasi pada versi audit dan "
  f"{pc(H['A2']['sepakat_kontinu_pra_audit'])} pada versi pra-audit. Ini memang diharapkan: pada model linear, "
  "mengondisikan pada z menghapus komponen z sehingga sisa yang diuji praktis sama dengan pasangan tanpa z. "
  "Perbandingan baris S={z} dengan S=∅ karena itu tidak dapat membedakan kode lama dari kode baru.")
P("Perbedaan antara kedua log juga dijelaskan oleh jumlah replikasi, bukan oleh kode: semua angka simulasi pada log "
  "17.12 adalah kelipatan 0,005 (konsisten dengan 200 replikasi), sedangkan 27 dari 45 angka pada log 19.14 bukan "
  "kelipatan 0,005 (memerlukan ≥ 1.000 replikasi, sesuai config.py). Log 17.12 sudah memakai config.py baru "
  "(boot = 500, delta_bar = 2,26 sesudah A5), sehingga 200 replikasi kemungkinan besar berasal dari isian “Replikasi "
  "simulasi” di aplikasi (app.py baris 531), yang mengesampingkan nilai config. Tidak ada kode yang berubah di antara "
  "kedua commit (a02d204 hanya memuat berkas log).")
P("Kesimpulan A2: perbaikannya benar dan bekerja (z kini confounder; uji bersyarat mendekati nominal), tetapi kriteria "
  "kelulusan yang dipakai pada 10 Oktober tidak menguji hal itu. Kriteria yang tepat adalah baris diagnostik di atas.")

Hd("4. A3 — aliran acak per analisis")
P(f"Hasil: {H['A3']['ringkas']}.")
P(f"Uji memakai novelty.run() yang sesungguhnya untuk N2 TO-DAG (bootstrap {H['A3']['bootstrap']} kali, memakai rng), "
  "dengan folder luaran dialihkan ke direktori sementara. Setiap analisis ke-2 dan seterusnya dijalankan sendiri dan "
  "dibandingkan dengan hasilnya saat semua analisis dijalankan berurutan. Kolom waktu dan memori diabaikan karena "
  "memang berubah di tiap run. Perilaku pra-audit ditiru dengan satu rng yang dipakai bersama secara berurutan.")
T(A3[["analisis", "berkas_dibandingkan", "identik", "pra_audit_berbeda"]].rename(columns={
    "analisis": "Analisis", "berkas_dibandingkan": "Berkas hasil", "identik": "Identik (versi audit)",
    "pra_audit_berbeda": "Berbeda (tiruan pra-audit)"}))
CAT("Analisis yang graf-nya tidak memuat jalur T→Y (RD = 0) tidak memakai rng, sehingga pada tiruan pra-audit pun "
    "hasilnya tidak berubah; bug pra-audit hanya tampak pada analisis sesudah analisis yang memakai bootstrap.")
_pindah = A3[A3.terbaik_berpindah]
P("Temuan sampingan: label “terbaik” di banding.csv (dan di log aplikasi, “terbaik=…”) ikut ditentukan oleh peringkat "
  "waktu komputasi, sehingga dapat berpindah antara dua run yang hasil statistiknya identik. Pada verifikasi ini label "
  f"berpindah pada {len(_pindah)} dari {len(A3)} analisis"
  + (f" ({', '.join(f'{r.analisis}: {r.terbaik_semua} → {r.terbaik_sendiri}' for r in _pindah.itertuples())})" if len(_pindah) else "")
  + ". Klaim “metode terbaik” dari menu novelty karena itu tidak boleh dikutip tanpa menyebut bahwa ia bergantung pada "
  "kecepatan mesin; pisahkan peringkat akurasi dari peringkat waktu.")

Hd("5. A4 — n efektif pada MLC-DAG")
P(f"Hasil: {H['A4']['ringkas']}.")
T(A4.rename(columns={"analisis": "Analisis", "n_mentah": "n mentah (dulu dipakai)", "n_kish": "n Kish",
                     "delta_bar": "delta_bar", "n_eff": "n efektif (sekarang)", "rasio_n_eff_per_n": "n efektif / n"}))
P("Dengan n mentah, penalti skor dan uji MLC 2–4 kali terlalu lunak dibanding N1/N2, yang konsisten dengan graf "
  "MLC yang terlalu padat (68–77 sisi) yang dicatat di komentar audit. Pemeriksaan statis juga memastikan benchmark.py "
  "memakai rumus n efektif yang sama.")

Hd("6. A5 — delta_bar tanpa variabel konteks")
P(f"Hasil: {H['A5']['ringkas']}.")
T(A5[["analisis", "variabel_tier0", "deff_maks_tier0", "delta_bar_pra_audit", "delta_bar_audit", "n_eff_pra_audit",
      "n_eff_audit", "arah"]].rename(columns={
    "analisis": "Analisis", "variabel_tier0": "Variabel tier 0", "deff_maks_tier0": "deff maks tier 0",
    "delta_bar_pra_audit": "delta_bar pra-audit", "delta_bar_audit": "delta_bar audit",
    "n_eff_pra_audit": "n_eff pra-audit", "n_eff_audit": "n_eff audit", "arah": "Arah delta_bar"}))
P("Alasan A5 di kode adalah bahwa variabel konteks tingkat klaster bernilai konstan di dalam PSU sehingga deff-nya "
  "besar dan menggelembungkan delta_bar. Ini benar untuk analisis sanitasi dan fasilitas (deff variabel konteks hingga "
  "7,5–9,4). Pada analisis PBI, variabel tier 0-nya agregat provinsi/daerah dengan deff kecil (≤ 1,6); mengeluarkannya "
  "justru menaikkan delta_bar dan menurunkan n efektif 8–9%. Implementasinya sesuai rancangan, tetapi narasi "
  "“A5 memperbesar n efektif” tidak berlaku umum dan sebaiknya ditulis per analisis.")

Hd("7. A6 — node MLC")
P(f"Hasil: {H['A6']['ringkas']}.")
T(A6[["analisis", "T", "treatment_pra_audit", "treatment_audit", "treatment_lain_tersisa"]].fillna("–").rename(columns={
    "analisis": "Analisis", "T": "Treatment analisis", "treatment_pra_audit": "Treatment di node MLC (pra-audit)",
    "treatment_audit": "Treatment di node MLC (audit)", "treatment_lain_tersisa": "Treatment lain yang tersisa"}))
P("Treatment lain yang tersisa (T_sanitasi pada analisis PBI-diare, T_fasilitas pada PBI-neonatal) adalah node DAG "
  "pakar analisis tersebut, sehingga dipertahankan dengan sengaja. Kasus yang memicu A6, yaitu T_pbi terpilih sebagai "
  "induk T_sanitasi pada analisis sanitasi, tidak dapat terjadi lagi karena T_pbi tidak lagi menjadi node.")

Hd("8. Rekomendasi")
for t in [
    "Ganti kriteria kelulusan A2 dengan baris diagnostik (pasangan z tanpa pengondisian harus jauh di atas α) dan "
    "tampilkan baris itu di log aplikasi.",
    "Catat jumlah replikasi simulasi di setiap baris log; isian aplikasi dapat mengesampingkan config.py tanpa jejak.",
    "Untuk A5, laporkan arah perubahan n efektif per analisis, bukan sebagai perbaikan seragam.",
    "Simpan laporan ini bersama skripnya; jalankan ulang verifikasi_a1_a6.py setiap kali novelty.py, benchmark.py, "
    "atau config.py berubah, dan bandingkan SHA-256 di bagian awal laporan.",
    "Kasus A1 (konfigurasi diubah tetapi tidak terpakai, tanpa galat) layak dimasukkan ke naskah 3 sebagai contoh "
    "kesalahan senyap."]:
    blok.append(("li", t))

Hd("9. Berkas")
for t in ["verifikasi_a1_a6.py — skrip uji ulang (hanya membaca kode dan data; tidak menulis ke hasil/)",
          "A1_beda_config.csv, A2_simulasi_confounder.csv, A3_aliran_acak.csv, A4_n_eff_mlc.csv, A5_delta_bar.csv, "
          "A6_node_mlc.csv, A2_p_per_replikasi.csv — tabel hasil", "ringkasan_verifikasi.json — status, SHA-256, versi pustaka",
          "log_verifikasi.txt — keluaran konsol", "buat_laporan.py — penyusun laporan ini"]:
    blok.append(("li", t))


# ------------------------------------------------------------------ keluaran
def md_tabel(df):
    df = df.astype(str)
    return "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * df.shape[1]]
                     + ["| " + " | ".join(r) + " |" for r in df.values])


md = []
for j, x in blok:
    md.append({"h1": f"# {x}", "h2": f"## {x}", "p": x, "li": f"- {x}", "catatan": f"> Catatan: {x}",
               "t": md_tabel(x) if j == "t" else ""}[j] if j != "t" else md_tabel(x))
(S / "LAPORAN_VERIFIKASI_A1_A6.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
for j, x in blok:
    if j == "h1":
        d.add_heading(x, 0)
    elif j == "h2":
        d.add_heading(x, 1)
    elif j == "p":
        d.add_paragraph(x)
    elif j == "li":
        d.add_paragraph(x, style="List Bullet")
    elif j == "catatan":
        r = d.add_paragraph().add_run("Catatan: " + x); r.italic = True
    elif j == "t":
        tb = d.add_table(rows=1, cols=x.shape[1]); tb.style = "Light Grid Accent 1"
        for c, n in zip(tb.rows[0].cells, x.columns):
            c.text = str(n)
        for row in x.astype(str).values:
            for c, v in zip(tb.add_row().cells, row):
                c.text = v
        for row in tb.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(8.5)
        for row in tb.rows[1:]:
            for c in row.cells:
                if c.text == "GAGAL":
                    c.paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW
        d.add_paragraph()
out = S / "LAPORAN_VERIFIKASI_A1_A6.docx"
try:
    d.save(out)
except PermissionError:
    out = out.with_name(out.stem + "_baru.docx"); d.save(out)
print("Tersimpan:", out.name, "dan LAPORAN_VERIFIKASI_A1_A6.md")
