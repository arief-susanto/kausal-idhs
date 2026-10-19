# Catatan deviasi dan pencabutan klaim: SOL-DAG v1 → v2 → v3

Dokumen ini dilampirkan pada disertasi/artikel dan dirujuk dari proposal serta dokumen Tahap 3.
Status: 27-09-2026. Hilir p = 15 selesai; hilir p = 30 (sekunder) masih berjalan.

## 1. Klaim yang dicabut

| Klaim lama (proposal / Tahap 3) | Status | Bukti |
|---|---|---|
| "SD-Hybrid memakai uji independensi bersyarat **baru** yang konsisten desain survei" | **Dicabut** | v3 H8c: keputusan uji t-desain usulan identik dengan uji Wald berpenaksir sandwich terklaster CR1 pada 99,9% pernyataan H0 (heterogen dan homogen). Lemma 2 (TEORI_S10): kedua statistik setara asimtotik (Frisch–Waugh–Lovell); perbedaannya hanya strata dan derajat bebas. |
| "SOL-DAG lebih cepat dan hemat memori daripada baseline" | **Dicabut** | Benchmark v1 (100 replikasi): H2 kecepatan didukung sebagian (3/8); SOL lebih lambat daripada B2, B3, dan N2 di skenario A. H3 memori didukung sebagian (6/8); pada skenario A tidak lebih hemat daripada B2/B3. Keunggulan waktu/memori hanya muncul pada skenario B terhadap metode yang bekerja pada 33 indikator mentah, yaitu efek pengecilan graf oleh MLC, bukan sifat SOL-DAG secara umum. |
| "SOL-DAG lebih akurat daripada baseline" (v1) | **Dicabut** | Benchmark v1 H1 didukung sebagian (6/27): pada skenario A efek T→Y dinolkan pada 97% replikasi (RMSE 0,020 vs 0,009 untuk B1/B2; cakupan CI 3%). |

Usulan redaksi untuk proposal/Tahap 3:
> "Uji independensi bersyarat yang dipakai setara dengan uji Wald berpenaksir sandwich terklaster (CR1) yang sudah dikenal; kontribusi penelitian ini bukan pada statistik ujinya, melainkan pada (i) bukti bahwa koreksi desain yang lazim (Kish, deff global) salah kalibrasi dalam penemuan kausal pada survei kompleks, (ii) penurunan FDR sisi dalam penemuan graf (H7b), meskipun validitas himpunan penyesuaian tidak meningkat (H7a gagal), dan (iii) Proposisi 3 tentang laju konsistensi skeleton yang ditentukan oleh jumlah PSU."

Hapus dari proposal dan Tahap 3: klaim "lebih cepat", "lebih hemat memori", dan "uji baru"; kriteria H2/H3 (kecepatan, memori) sebagai kontribusi SOL-DAG.

## 2. Deviasi v1 → v2 (dari PRAREGISTRASI_v2.md, ditambah deviasi pelaksanaan)

| Komponen | v1 | v2 | Alasan |
|---|---|---|---|
| Estimasi efek | Efek = 0 bila graf tak memuat jalur T→Y | Graf hanya memilih himpunan penyesuaian; efek selalu diestimasi (AIPW, himpunan ala IDA) | Efek nol 97%, cakupan CI 3% |
| Pemisahan sampel | Separuh A menemukan, separuh B mengestimasi | Cross-fitting K = 2 per PSU di dalam strata | Membuang separuh data |
| Koreksi desain | Rao-Scott + α = 0,01 + penalti n_eff + split | Satu koreksi: uji t-desain, α = 0,05, tanpa tahap skor | Tipe I 3,6% (konservatif), daya hilang |
| SE efek | Bootstrap PSU 20 replikasi | Fungsi pengaruh + linearisasi desain | Persentil 20 replikasi tidak stabil |
| Graf acuan | DAG pakar diperturbasi 30% / model MLC | DAG acak patuh tier | Benchmark v1 menguntungkan B1 (A) dan SOL (B) |

Deviasi pelaksanaan v2 (wajib dilaporkan):
1. `run_bench.py` yang diterima berisi 4 sel grid; diubah menjadi 6 sel agar sesuai pra-registrasi (ICC {0,05; 0,4} × β {−0,6; −0,15; 0}) dan ditambah opsi paralel per sel. Seed dan isi sel tidak berubah.
2. Hash kode dicatat pada v2/HASH_KODE_v2.txt; benchmark dijalankan 27-09-2026 pukul 07.29. Tanggal registrasi OSF: ________ (bila setelah 07.29, catat sebagai deviasi).
3. Evaluasi H2v2: versi awal kode evaluasi hanya memeriksa p Wilcoxon; diperbaiki agar mensyaratkan RMSE v2 < v1 **dan** p Holm < 0,05 sesuai teks. Putusan akhir: **gagal** (ICC 0,4: RMSE v2 0,0341 vs v1 0,0307).
4. Evaluasi H3v2: n pernyataan diasumsikan 20 × replikasi per sel (sol_v2 hanya menyimpan proporsi); H3v2–H6v2 digabung antar-sel ICC 0,4 (H5v2 semua sel).

Hasil v2: H1v2, H3v2, H4v2, H5v2, H6v2 diterima; H2v2 gagal.

## 3. Deviasi v2 → v3 (dari PRAREGISTRASI_v3.md, ditambah deviasi pelaksanaan)

- Desain benchmark: sintetis setara IDHS (67 strata × 29 PSU × 9), ICC heterogen U(0,1; 0,8) vs homogen 0,45; kalibrasi deff tingkat-uji ke IDHS nyata (S6 terkonfirmasi: p10/median/p90 = 1,36/2,39/4,41).
- Pembanding: lima uji (naif, Kish, deff-global, sandwich CR1, desain usulan).
- Pengungkapan pilot: 15 replikasi `run_s8.py` dilihat sebelum registrasi; H8c ditambahkan setelah pilot.
- Hash kode: v3/HASH_KODE_v3.txt (27-09-2026 13.11); run dimulai 13.12. Tanggal registrasi OSF: ________.
- Pelaksanaan: `run_downstream.py 100 15` dan `100 30` dijalankan paralel (bukan berurutan); tidak memengaruhi hasil (seed per replikasi).

**Tafsiran skenario H8 dan bagian ambigu (ditetapkan sebelum melihat hasil hilir):**
H8a, H8b, H8d diuji pada skenario heterogen (inti S8); H8c pada gabungan kedua skenario; H7a pada skenario
heterogen seperti tertulis; H7b dan H9 memakai heterogen sebagai skenario utama (homogen dilaporkan); H9 diuji
pada uji desain_usulan dengan p = 15.

Hasil v3 (S8, 200 replikasi × 2 skenario):

| Kode | Hasil | Putusan |
|---|---|---|
| H8a | Tipe I uji desain 5,2% (Wilson 4,7–5,7%) | diterima |
| H8b | Naif 18,2%, Kish 18,4%; deff-global 0,4% | diterima |
| H8c | Kesepakatan dengan CR1 99,9% | diterima → klaim "uji baru" dicabut |
| H8d | Daya desain 54,3% vs deff-global 43,4% (+10,8 pp) | diterima |
| H7a | Validitas penyesuaian: desain 78% vs naif 91%, Kish 86% (p = 15, heterogen) | gagal (arah berlawanan) |
| H7b | FDR sisi: desain 6,2% vs naif 19,3% (heterogen), p Holm 4e-18 | diterima |
| H9 | Cakupan gabungan dan utama 98% (heterogen dan homogen) | diterima |

## 4. Arah berikutnya (bergantung pada H7a/H7b)

- Jika H7a atau H7b diterima: kontribusi "kalibrasi desain survei diperlukan agar penemuan kausal menghasilkan himpunan penyesuaian yang valid", ditambah Proposisi 3.
- Jika keduanya gagal: kebaruan metodologis habis; disertasi dialihkan menjadi studi kausal terapan (pipeline dan temuan sanitasi), dengan hasil kalibrasi sebagai satu bab evaluasi, termasuk hasil negatifnya.


> Bagian 5–6 (riwayat run benchmark untuk naskah yang sedang disiapkan dan kunci simulasi perluasan) akan ditambahkan setelah naskah terkait dikirim.
