# Pra-registrasi SOL-DAG v2 (isi tanggal & unggah ke OSF SEBELUM menjalankan `run_bench.py 200`)

Tanggal registrasi: ________  ·  Commit/hash kode: ________

## Deviasi dari v1 (wajib dilaporkan di disertasi/artikel)
| Komponen | v1 (gagal) | v2 | Alasan (dari hasil v1) |
|---|---|---|---|
| Estimasi efek | Efek = 0 jika graf tak memuat jalur T→Y | Graf hanya memilih himpunan penyesuaian; efek selalu diestimasi (AIPW), himpunan efek ala IDA | Efek nol 97%, cakupan CI 3% (skenario A) |
| Pemisahan sampel | Separuh A menemukan graf, separuh B mengestimasi | Cross-fitting K=2 per PSU di dalam strata | Membuang separuh data |
| Koreksi desain | Rao-Scott + α=0,01 + penalti n_eff + split (berlapis) | Satu koreksi: uji-t desain per uji, α=0,05, tanpa tahap skor | Tipe I 3,6% (terlalu konservatif), kehilangan daya uji |
| SE efek | Bootstrap PSU 20 replikasi | Fungsi pengaruh + linearisasi desain | Persentil dari 20 replikasi tidak stabil |
| Graf acuan benchmark | DAG pakar dipertubasi 30% / model MLC | DAG acak patuh tier, independen dari metode | Benchmark v1 menguntungkan B1 (A) dan SOL (B) |

## Hipotesis v2 dan kriteria (ditetapkan sebelum melihat hasil v2)
| Kode | Hipotesis | Diterima jika | Gagal jika |
|---|---|---|---|
| H1v2 | Estimasi sadar-query memulihkan efek | Efek nol 0% dan cakupan CI ≥ 85% di semua skenario efek ≠ 0 | Cakupan < 80% di salah satu skenario |
| H2v2 | v2 lebih akurat daripada aturan v1 pada efek kecil | RMSE v2 < v1 (Wilcoxon satu sisi, Holm p < 0,05) pada beta_ty = −0,15 | Tidak lebih kecil |
| H3v2 | Uji desain terkalibrasi | Galat tipe I 2,5–7,5% dan batas atas Wilson ≤ 9% pada ICC 0,4 | Di luar rentang |
| H4v2 | Uji naif tidak terkalibrasi pada data berklaster | Galat tipe I naif > 10% pada ICC 0,4 | ≤ 10% |
| H5v2 | Kehilangan daya uji terbatas | Daya uji desain ≥ daya naif − 5 poin persen | Selisih > 5 poin persen |
| H6v2 | Akurasi struktur tidak lebih buruk | SHD desain ≤ SHD naif + 1 (non-inferioritas) pada ICC 0,4 | Selisih > 1 |

Grid: ICC ∈ {0,05; 0,4}, beta_ty ∈ {−0,6; −0,15; 0}, 200 replikasi per sel, seed 0–199.
Hasil negatif dilaporkan apa adanya. Perubahan setelah registrasi ini = deviasi baru yang harus dicatat.
