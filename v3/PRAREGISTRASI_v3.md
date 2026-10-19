# Pra-registrasi v3 (S6–S10, inti S8) — isi tanggal & unggah ke OSF SEBELUM run penuh

Tanggal: ________ · Hash kode: ________
**Pengungkapan pilot:** uji coba 15 replikasi `run_s8.py` sudah dilihat penulis (hasil di RINGKASAN_PILOT.txt).
Hipotesis di bawah TIDAK diubah setelah pilot kecuali H8c yang ditambahkan karena pilot menunjukkan kesetaraan.

## Desain (S6)
Desain sintetis setara IDHS: 67 strata × 29 PSU × 9 kelahiran (n ≈ 17.487); ICC per variabel U(0,1; 0,8),
dikalibrasi agar deff tingkat-uji menyerupai IDHS nyata (p10/median/p90 = 1,36/2,39/4,41).
Skenario: heterogen U(0,1; 0,8) vs homogen 0,45. p = 15 (utama), 30 (sekunder). 200 replikasi (S8), 100 (hilir).

## Hipotesis
| Kode | Hipotesis | Diterima jika |
|---|---|---|
| H8a | Uji desain terkalibrasi pada deff heterogen | galat tipe I 2,5–7,5% |
| H8b | Pembanding lazim salah kalibrasi | naif & Kish > 10%; deff-global < 2,5% |
| H8c | Uji desain setara sandwich CR1 | kesepakatan keputusan H0 ≥ 99% → klaim "uji baru" DICABUT |
| H8d | Daya uji desain > deff-global | selisih ≥ 5 poin persen |
| H7a | Validitas himpunan penyesuaian desain ≥ naif dan Kish | Wilcoxon satu sisi, Holm p < 0,05 (heterogen) |
| H7b | FDR sisi desain < naif | Wilcoxon satu sisi, Holm p < 0,05 |
| H9  | Cakupan CI | cakupan gabungan ≥ 94%; cakupan utama ≥ 92% |
Hasil negatif dilaporkan apa adanya.
