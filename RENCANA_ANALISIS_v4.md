# Rencana analisis benchmark v4 (dikunci sebelum simulasi penuh)
Skrip: bench_v4.py; setelan: config.BENCH_V4 (200 replikasi x 24 sel).
M4 utama: alpha_T = 0,10 (0,20 dan 0,30 = sensitivitas).
Metode terbaik = validitas tertinggi di antara M4 utama, M5, M6 pada ICC heterogen.
H10: validitas himpunan penyesuaian metode terbaik >= 90% pada ICC heterogen, dan >= M2.
H11: rerata FDR sisi M4 utama <= M2, dan Wilcoxon satu sisi p < 0,05.
H12: RMSE metode terbaik <= M0 (nilai titik; Wilcoxon |galat| dilaporkan).
H13: cakupan CI 95% metode terbaik >= 92%.
Gerbang 2: skenario A jika H10 diterima; selain itu skenario B (studi peringatan).
