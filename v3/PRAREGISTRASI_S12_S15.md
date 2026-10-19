# Addendum pra-registrasi v3 — S12, S13, S14 (dan penutup S15)

Dikunci: 2026-09-30 21:37 WIB, **sebelum** run utama `run_downstream_v4.py`.
Hash SHA-256 kode (lihat juga HASH_KODE_v4.txt):
- sol_v4.py `c5b52404e76a83fa6bb874f825d12c52ce2f4f8b4af08b301ebf46d5e65e932b`
- run_downstream_v4.py `1cbd58b44c7abf168b0e5ce58bff8791d040908d322c8af21e4a4d91a95065f6`
- sol_v3.py `66c3e8283d11ccd1982ae3e71f55cc28e1179689ecdfa7fff11fa996be5c63e9` (tidak berubah sejak pra-registrasi v3)

Stempel waktu di atas bersifat lokal. Unggah file ini ke OSF sebagai addendum agar stempel waktunya dapat diverifikasi pihak ketiga.

## Pengungkapan (apa yang sudah dilihat penulis)
1. Hasil hilir v3 p=15 dengan **100 replikasi** (27-09-2026, `log_ds15.txt`) dan run ulang ad hoc dengan **50 replikasi**
   (30-09-2026, `RINGKASAN_downstream_p15.txt`). Keduanya menunjukkan uji desain FDR ≈ 0,06 dan validitas ≈ 0,72–0,81,
   sedangkan naif FDR ≈ 0,19 dan validitas ≈ 0,88–0,91. **S12 dan S13 dirancang setelah melihat hasil ini.**
2. Uji asap kode: 3 replikasi p=8 (metrik tidak dibaca) dan 1 replikasi seed 5000 (hanya waktu komputasi).
3. Tidak ada hasil S12/S13/S14 yang dilihat sebelum penguncian ini.

## Deviasi dari pra-registrasi v3
- Run 50 replikasi pada 30-09 bersifat eksploratori dan menimpa CSV 100 replikasi tanggal 27-09. Karena seed
  deterministik (rep = 0..99), run v4 membuat ulang kolom v3 untuk **100 replikasi sesuai rencana**. Jadi tidak ada deviasi jumlah replikasi.
- p=30 (sekunder) belum pernah dijalankan (`log_ds30.txt` kosong). p=30 kini dijalankan dengan 100 replikasi.

## Metode
- **S12 (himpunan cadangan):** Z_S12 = pâ(T) ∪ (pâ(Y) \ dê(T)) \ {T, Y} dari graf yang dipelajari (sisi terarah).
  Himpunan ini dilaporkan berdampingan dengan himpunan utama v3 (`cand_sets`) untuk kelima uji. α tidak diubah.
- **S13 (α sadar-query):** uji dasar = `desain_usulan`. α = 0,05 untuk uji yang tidak melibatkan T atau Y, dan α_q untuk uji
  yang melibatkan T atau Y. **α_q = 0,20 adalah analisis utama.** α_q = 0,10 dan 0,30 adalah sensitivitas. Nilai lain tidak akan dicoba.
- **S14 (bias akibat himpunan):** bias_set = θ̂(Ẑ) − θ̂(Z_orakel), dengan Z_orakel = pa(T) di graf acuan dan data,
  lipatan, serta R=5 yang sama. Himpunan disebut *material* jika tidak sah **dan** |bias_set| > SE orakel.
- Desain, skenario (heterogen U(0,1; 0,8) vs homogen 0,45), β_TY = −0,3, max_k = 2, dan R = 5 sama dengan v3.
  Replikasi 0..99 digunakan untuk p = 15 (utama) dan p = 30 (sekunder).

## Hipotesis (dianalisis per skenario; skenario heterogen p=15 = konfirmatori, sisanya pendukung)
| Kode | Hipotesis | Diterima jika |
|---|---|---|
| H12a | Validitas Z_S12 > validitas himpunan utama, untuk tiap uji | Wilcoxon bertanda satu sisi berpasangan per replikasi, Holm atas 5 uji, p < 0,05 |
| H12b | Himpunan cadangan tidak merusak inferensi efek | cakupan CI Z_S12 (desain_usulan) ≥ 92% |
| H13 | α sadar-query (α_q = 0,20) memberi validitas setara naif dengan FDR setara desain | **keduanya**: batas bawah bootstrap satu sisi 95% dari (FDR_desain − FDR_S13 + 0,02) > 0, **dan** dari (valid_S13 − valid_naif + 0,05) > 0 |
| H14 | (deskriptif, tanpa uji) proporsi himpunan tidak sah yang material per uji; rata-rata \|bias_set\| | dilaporkan apa adanya |

Klaim "metode baru" untuk S13 hanya dibuat jika H13 diterima pada skenario heterogen p=15 **dan** arahnya sama pada p=30.
Jika H13 hanya diterima pada α_q sensitivitas, hasilnya dilaporkan sebagai eksploratori.
Hasil negatif dilaporkan apa adanya.
