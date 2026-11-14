# Bahan verifikasi naskah 3, revisi 6 (rilis v1.4)

Naskah: *Kesalahan Senyap pada Pipeline Analitik Data: Bukti Empiris dari Praktik Reproduksibilitas Berlapis pada Proyek Nyata*.
Rilis ini melengkapi `../revisi5/` (v1.3) dengan evaluasi yang diminta review 14-11-2026.

| Evaluasi | Skrip (`skrip/`) | Hasil (`tabel/`) |
|---|---|---|
| E7b Batas deteksi pemeriksa impor: 11 varian impor basi, diuji dengan pemeriksa AST (D1), Import Linter, dan penjaga runtime (D1r) | `negatif_palsu_impor.py` | `E7b_negatif_palsu_impor.csv`, `log_E7b_negatif_palsu.txt` |
| E8b Injeksi kesalahan dari kategori Yin dkk. (SOSP 2011), target dipilih acak berbenih | `injeksi_eksternal.py` | `E8b_injeksi_eksternal.csv`, `log_E8b_injeksi_eksternal.txt` |
| E8 + penjaga runtime D1r | `d1r_e8.py` | `E8_d1r.csv` |
| E4 Koreksi Holm atas 45 uji desain 2×2 (IK identik dengan `../revisi5/tabel/E4_2x2_efek_nol.csv`) | `holm_2x2.py` | `E4_2x2_holm.csv` |
| E1/E6 Selisih dalam satuan ULP dan selisih relatif | `ulp_e1.py` | `E1_ulp.csv` |
| E10 Waktu header dan merkle root blok atestasi OpenTimestamps, dicocokkan dengan dua penjelajah blok | `verifikasi_blok_ots.py` | `E10_verifikasi_blok.csv` |

`periksa_impor_config.py`, `injeksi_kesalahan.py`, dan `analisis_2x2_mc.py` identik dengan versi di `../revisi5/skrip/`
dan disalin karena diimpor oleh skrip baru.

## Catatan

**Import Linter.** `negatif_palsu_impor.py` membutuhkan Import Linter 2.16:
`python -m pip install -r requirements-verifikasi.txt` (berkas di akar repositori). Dependensi ini dipisahkan dari
`requirements-lock.txt` agar lingkungan analisis terkunci tidak berubah. Import Linter hanya menerima paket, sehingga
skrip pipeline dibungkus sementara ke satu paket; berkas arsip `*_sebelum_audit.py` dikecualikan seperti pada D1.

**D5 relatif pada E8b.** `baseline.py`, `causal.py`, dan `sol_dag.py` sudah sah berbeda dari tag `v-paper1` sejak
perbaikan benih per analisis (v1.3, CATATAN_DEVIASI.md bagian 8). Jejak versi (D5) karena itu dinilai relatif
terhadap kontrol.

**Penjelajah blok.** `verifikasi_blok_ots.py` membaca log `ots info` dari `../revisi5/tabel/E10_opentimestamps/` dan
memakai blockchain.info serta api.blockcypher.com. Sebagian penjelajah lain dapat diblokir penyaring DNS penyedia
internet; `ots verify` dengan node Bitcoin sendiri adalah alternatif tanpa pihak ketiga. Hasil: blok #975540 bertanggal
2026-11-12 11:00:19 UTC, dan merkle root ketiga atestasi cocok pada kedua sumber.

**Batas menjalankan ulang.** Seperti `../revisi5/`, skrip ditulis untuk struktur folder repositori pribadi
(`naskah/03_reproduksibilitas/skrip` dan `tabel`). `holm_2x2.py` membaca keluaran sel E4 dan run benchmark, dan
injeksi membutuhkan salinan beku serta `cache/analisis.pkl` dari mikrodata SDKI 2017, yang tidak disertakan.
