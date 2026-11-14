# Verifikasi

| Folder | Isi |
|---|---|
| `audit_A1_A6/` | Verifikasi ulang perbaikan audit A1–A6: `verifikasi_a1_a6.py` (uji), `buat_laporan.py` (penyusun laporan), tabel hasil (CSV/JSON), dan `LAPORAN_VERIFIKASI_A1_A6.md`/`.docx`. `verifikasi_a1_a6.py` membutuhkan `cache/analisis.pkl`, yang dibuat dari mikrodata SDKI 2017 (`python main.py prep`); mikrodata tidak disertakan. |
| `naskah3/` | Pemeriksaan N3-1 sampai N3-4 untuk naskah reproduksibilitas: `LAPORAN_VERIFIKASI_NASKAH3.md`/`.docx`, tabel pendukung, dan penyusunnya `buat_laporan_naskah3.py`. |
| `naskah3/revisi5/` | Bahan verifikasi naskah 3 revisi 5 (rilis v1.3): pemeriksa impor (E7), injeksi kesalahan (E8), uji utas BLAS (E1), skema benih bootstrap (E9), desain 2×2 kode × konfigurasi (E4), dan bukti OpenTimestamps (E10). Lihat `naskah3/revisi5/README.md`. |
| `naskah3/revisi6/` | Bahan verifikasi naskah 3 revisi 6 (rilis v1.4): batas deteksi pemeriksa impor dengan Import Linter dan penjaga runtime (E7b), injeksi dari kategori Yin dkk. (E8b), koreksi Holm (E4), ULP (E1/E6), dan verifikasi blok OpenTimestamps (E10). Lihat `naskah3/revisi6/README.md`. |

Catatan untuk `naskah3/`: penyusun laporan membaca riwayat git lengkap (tag, commit lama, dan log pada commit tertentu)
serta luaran run di repositori pribadi penulis, sehingga tidak dapat dijalankan ulang dari repositori publik ini.
Hash commit yang dirujuk dapat dicocokkan dengan `JEJAK_VERSI.md`; riwayat lengkap tersedia untuk reviewer atas permintaan.
Arsip rilis ini membuktikan keberadaan kode per tanggal rilis, bukan waktu penyusunan rencana analisis.

Path `naskah_ke_2/...`, `naskah_lanjutan/...`, dan `dok_disertasi/...` di `CATATAN_DEVIASI.md` dan di laporan merujuk ke
struktur repositori pribadi. Padanannya di sini: `dok_disertasi/verifikasi_audit/` = `verifikasi/audit_A1_A6/`,
`dok_disertasi/verifikasi_naskah3/` = `verifikasi/naskah3/`, `naskah_ke_2/03_reproduksibilitas/skrip/` = `verifikasi/naskah3/skrip/`
(bila disertakan). Bahan `naskah_lanjutan/` (riwayat run benchmark v1) tidak disertakan.
Skrip run N3-3 dan N3-4 ada di `naskah3/skrip/` (`ulang_config_lama.py`, `putusan_config_lama.py`, `ulang_run3_tier2.py`); skrip itu ditulis untuk struktur folder repositori pribadi dan membutuhkan `cache/analisis.pkl`.
