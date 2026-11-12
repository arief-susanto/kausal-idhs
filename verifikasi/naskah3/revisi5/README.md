# Bahan verifikasi naskah 3, revisi 5 (rilis v1.3)

Naskah: *Kesalahan Senyap pada Pipeline Analitik Data: Bukti Empiris dari Praktik Reproduksibilitas Berlapis pada Proyek Nyata*.

| Evaluasi | Skrip (`skrip/`) | Hasil (`tabel/`) |
|---|---|---|
| E1 Utas BLAS dan pergeseran bit | `uji_benang_e1.py`, `bandingkan_benang_e1.py` | `E1_uji_benang.csv`, `log_E1_benang1.txt` |
| E4 Desain 2×2 kode × konfigurasi | `ulang_sel_kode_lama.py` (sel kode pra-audit), `analisis_2x2_mc.py` (efek utama, interaksi, IK Newcombe dan bootstrap berpasangan) | `E4_2x2_efek_nol.csv`, `E4_2x2_validasi.json`, `E4_sel4/`, `log_E4_sel4_*.txt` |
| E7 Pemeriksa impor konfigurasi | `periksa_impor_config.py` (AST; `--riwayat` memindai riwayat git) | `E7_pemeriksa_impor_riwayat.csv` |
| E8 Injeksi kesalahan | `injeksi_kesalahan.py` | `E8_injeksi_kesalahan.csv`, `log_E8_injeksi.txt` |
| E9 Skema benih bootstrap | `uji_bootstrap_benih.py` | `E9_bootstrap/`, `log_E9_bootstrap.txt` |
| E10 Stempel waktu rencana | `stempel_ots.py` | `E10_opentimestamps/` |

## Catatan

**Sel E4.**
- `lama_cfglama` = kode pra-audit (tag `67d1dfb`) dengan konfigurasi basi. Sel ini adalah validasi bahwa kode itu menghasilkan ulang run 1b.
- `lama_cfgbenar` = kode pra-audit dengan konfigurasi benar (commit `74eb7a4`).
- Kode pra-audit diekstrak ke folder sementara. Path folder itu disamarkan di `meta.json` dan log.

**Verifikasi OpenTimestamps.**
1. Hitung SHA-256 tiap berkas yang tercantum di manifest, sesudah CRLF diubah menjadi LF, lalu bandingkan dengan isi manifest.
2. Jalankan `ots verify MANIFEST_RENCANA_NASKAH1.txt.ots` (perlu node Bitcoin atau penjelajah blok).

Berkas manifest disimpan tanpa konversi akhir baris (`.gitattributes`). Atestasi paling awal tercatat pada blok Bitcoin #975540. Berkas rencana yang tercantum di manifest merujuk ke struktur repositori pribadi dan akan dipublikasikan bersama naskah pendampingnya.

**Batas menjalankan ulang.** Seperti `../README` dan `../../README.md`, skrip ini ditulis untuk struktur folder repositori pribadi. Sebagian membaca riwayat git lengkap, dan sebagian membutuhkan `cache/analisis.pkl` dari mikrodata SDKI 2017, yang tidak disertakan.
