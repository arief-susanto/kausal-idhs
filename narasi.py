"""Rangkuman proses + narasi otomatis (Bahasa Indonesia) untuk setiap menu, dibangun dari berkas hasil.
Setiap fungsi mengembalikan dict(proses=[langkah...], narasi=[paragraf...]) atau None bila hasil belum ada."""
import json
import numpy as np
import pandas as pd
import config as C

LABEL = {
    "T_sanitasi": "sanitasi layak", "T_pbi": "kepesertaan JKN PBI", "T_fasilitas": "persalinan di fasilitas kesehatan",
    "Y_diare": "diare pada balita (2 minggu terakhir)", "Y_ispa": "ISPA pada balita",
    "Y_mati_neonatal": "kematian neonatal", "Y_mati_bayi": "kematian bayi",
}
lbl = lambda v: LABEL.get(v, v)


def a(x, d=3):
    """Angka format Indonesia: 1.234,567"""
    return f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def pct(x, d=1):
    return a(100 * x, d) + "%"


def ribu(n):
    return a(float(n), 0)


def ci_pct(lo, hi, d=1):
    return f"{a(100 * lo, d)}–{pct(hi, d)}"


def ci_rd(lo, hi):
    return f"[{a(lo, 4)}; {a(hi, 4)}]"


def bermakna(lo, hi, nol=0.0):
    if lo != lo or hi != hi:
        return "tanpa CI bootstrap"
    return "bermakna secara statistik (CI 95% tidak memuat nol)" if (lo > nol or hi < nol) \
        else "tidak bermakna secara statistik (CI 95% memuat nol)"


def arah(rd):
    return "menurunkan" if rd < 0 else "meningkatkan" if rd > 0 else "tidak mengubah"


def _csv(p, **kw):
    try:
        return pd.read_csv(p, **kw) if p.exists() else None
    except pd.errors.EmptyDataError:
        return None


def _kv(p):
    x = _csv(p, index_col=0)
    return None if x is None else x.nilai


def md(judul, r):
    if r is None:
        return ""
    return (f"## {judul}\n\n### Rangkuman proses\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(r['proses'], 1))
            + "\n\n### Narasi\n" + "\n\n".join(r['narasi']) + "\n")


# ================================================================== menu 1
def prep(df):
    if df is None:
        return None
    info = C.OUT / "prep_info.json"
    meta = json.loads(info.read_text()) if info.exists() else {}
    proses = [
        "Membaca recode kelahiran (IDBR71) dan rumah tangga (IDHR71) IDHS 2017 langsung dari berkas zip DHS.",
        "Membatasi unit analisis pada kelahiran dalam 5 tahun sebelum survei (v008 − b3 < 60 bulan).",
        "Membentuk treatment: sanitasi layak (jenis jamban v116), kepesertaan JKN PBI (v481c), dan persalinan di "
        "fasilitas kesehatan (tempat persalinan m15).",
        "Membentuk outcome: diare 2 minggu terakhir (h11, hanya anak hidup), ISPA, kematian neonatal (meninggal "
        "< 1 bulan, b5–b6), dan kematian bayi (b7).",
        "Menyusun kovariat ibu, anak, dan rumah tangga, termasuk indeks kekayaan non-WASH dari PCA aset tanpa "
        "komponen air, jamban, dan ternak.",
        "Menghitung agregat klaster leave-one-out (cakupan sanitasi, cuci tangan, fasilitas, hambatan jarak).",
        "Menggabungkan data konteks provinsi 2017 (kemiskinan, puskesmas per kecamatan, kekurangan bidan, "
        "cakupan PBI).",
        "Menyimpan dataset ke cache/analisis.pkl dan hasil/dataset_analisis.csv beserta bobot (v005/10⁶), "
        "PSU (v021), dan strata (v023).",
    ]
    wm = lambda v: np.average(df[v].dropna(), weights=df.loc[df[v].notna(), 'bobot'])
    kosong = df[[c for c in df if c.startswith(('T_', 'Y_'))]].isna().mean().sort_values(ascending=False)
    kosong = kosong[kosong > 0.01]
    narasi = [
        f"Dataset analisis memuat **{ribu(len(df))} kelahiran** dalam lima tahun terakhir dari "
        f"{ribu(df.klaster.nunique())} klaster di {df.kode_prov_v024.nunique()} provinsi, dengan {df.shape[1]} "
        "variabel. Setiap kelahiran membawa bobot sampel, PSU, dan strata sehingga seluruh estimasi pada menu "
        "berikutnya mewakili populasi Indonesia dan memperhitungkan desain survei berklaster.",
        f"Secara berbobot, {pct(wm('T_sanitasi'))} kelahiran tinggal di rumah tangga dengan sanitasi layak, "
        f"{pct(wm('T_pbi'))} ibu tercatat sebagai peserta JKN PBI, dan {pct(wm('T_fasilitas'))} persalinan "
        f"terjadi di fasilitas kesehatan. Prevalensi diare balita dalam dua minggu terakhir sebesar "
        f"{pct(wm('Y_diare'))}, sedangkan kematian neonatal sebesar {pct(wm('Y_mati_neonatal'), 2)} "
        f"({ribu(df.Y_mati_neonatal.sum())} kasus dalam sampel).",
    ]
    if len(kosong):
        narasi.append("Data kosong pada treatment dan outcome sebagian besar bersifat struktural, misalnya diare "
                      "hanya ditanyakan untuk anak yang masih hidup dan kematian bayi hanya dinilai bagi anak yang "
                      "sudah terpapar 12 bulan: " + ", ".join(f"{k} {pct(v)}" for k, v in kosong.items())
                      + ". Analisis kausal memakai kasus lengkap per analisis.")
    if 'pca_varians' in meta:
        narasi.append(f"Indeks kekayaan non-WASH (komponen utama pertama) menjelaskan {pct(meta['pca_varians'])} "
                      "varians aset. Komponen air, jamban, dan ternak sengaja dikeluarkan agar indeks kekayaan tidak "
                      "tumpang tindih dengan treatment sanitasi dan faktor risiko diare.")
    return dict(proses=proses, narasi=narasi)


# ================================================================== menu 2
def eda():
    o = C.OUT / "eda"
    desk = _csv(o / "02_deskriptif_svy.csv")
    if desk is None:
        return None
    q, prov = _csv(o / "03_per_kuintil.csv", index_col=0), _csv(o / "04_per_provinsi.csv", index_col=0)
    bal, miss = _csv(o / "05_smd_per_treatment.csv", index_col=0), _csv(o / "01_missing.csv", index_col=0)
    proses = [
        f"Menghitung rerata berbobot dan SE linearisasi Taylor (strata, PSU) untuk {len(desk)} variabel utama, "
        "beserta CI 95%.",
        "Menghitung design effect (deff) treatment dan outcome sebagai rasio varians desain terhadap varians "
        "sampel acak sederhana.",
        "Meringkas treatment dan outcome per kuintil kekayaan non-WASH dan per provinsi.",
        "Menghitung standardized mean difference (SMD) berbobot seluruh kovariat antara kelompok treatment dan "
        "kontrol.",
        "Menghitung proporsi data kosong dan matriks korelasi variabel utama.",
    ]
    d = desk.set_index('variabel')
    ty = [v for v in d.index if v.startswith(('T_', 'Y_'))]
    deff = {v: d.se[v] ** 2 / (d.rerata[v] * (1 - d.rerata[v]) / d.n[v]) for v in ty}
    narasi = [
        "Prevalensi berbobot (CI 95%): " + "; ".join(
            f"{lbl(v)} {pct(d.rerata[v], 2 if d.rerata[v] < 0.05 else 1)} "
            f"({ci_pct(d.ci_bawah[v], d.ci_atas[v], 2 if d.rerata[v] < 0.05 else 1)})" for v in ty) + ".",
        "Design effect berkisar " + f"{a(min(deff.values()), 2)}–{a(max(deff.values()), 2)}"
        + (f" (diare {a(deff['Y_diare'], 2)})" if 'Y_diare' in deff else "")
        + ". Artinya, karena pengambilan sampel berklaster, ukuran sampel efektif hanya sekitar n/deff; "
          "mengabaikan desain survei akan membuat standard error terlalu kecil dan uji terlalu sering menolak "
          "hipotesis nol.",
    ]
    if q is not None:
        g = [f"{lbl(v)} {'naik' if q[v].iloc[-1] > q[v].iloc[0] else 'turun'} dari {pct(q[v].iloc[0])} pada "
             f"kuintil termiskin menjadi {pct(q[v].iloc[-1])} pada kuintil terkaya" for v in ['T_sanitasi', 'T_fasilitas', 'T_pbi', 'Y_diare'] if v in q]
        narasi.append("Terdapat gradien sosial-ekonomi yang jelas: " + "; ".join(g) + ". Karena kekayaan "
                      "memengaruhi treatment sekaligus outcome, kekayaan adalah confounder utama yang wajib dikontrol.")
    if prov is not None:
        r = [f"{lbl(v)} {pct(prov[v].min())} ({prov[v].idxmin()}) hingga {pct(prov[v].max())} ({prov[v].idxmax()})"
             for v in ['T_sanitasi', 'T_pbi', 'T_fasilitas'] if v in prov]
        narasi.append("Variasi antarprovinsi besar: " + "; ".join(r) + ". Variasi ini dimanfaatkan melalui "
                      "variabel konteks provinsi dan agregat klaster dalam DAG.")
    if bal is not None:
        s = [f"{lbl(t)} memiliki {int((bal[t].abs() > 0.1).sum())} kovariat dengan |SMD| > 0,1 (terbesar "
             + ", ".join(f"{k} {a(bal[t][k], 2)}" for k in bal[t].abs().sort_values(ascending=False).index[:3]) + ")"
             for t in bal]
        narasi.append("Kelompok treatment dan kontrol tidak sebanding sebelum penyesuaian: " + "; ".join(s)
                      + ". Perbandingan naif akan bias oleh confounding, sehingga penyesuaian kovariat berbasis "
                        "DAG pada menu 3 diperlukan.")
    if miss is not None:
        m = miss.prop_kosong[miss.prop_kosong > 0.05]
        if len(m):
            narasi.append("Variabel dengan data kosong > 5%: " + ", ".join(f"{k} ({pct(v)})" for k, v in m.items())
                          + ". Variabel dengan kekosongan tinggi tidak dipakai di DAG kecuali memang diperlukan.")
    return dict(proses=proses, narasi=narasi)


# ================================================================== menu 3
def _adj(p):
    if not p.exists():
        return None
    r = {}
    for baris in p.read_text(encoding="utf-8").splitlines():
        k, _, v = baris.partition(":")
        r[k.split(" (")[0].strip()] = v.strip()
    return r


def evalue(rr):
    rr = 1 / rr if rr < 1 else rr
    return rr + np.sqrt(rr * (rr - 1))


def kausal(nama):
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    out = C.OUT / "kausal" / nama
    adj, est = _adj(out / "adjustment.txt"), _csv(out / "estimasi.csv", index_col=0)
    if adj is None and est is None:
        return None
    proses = [f"Membangun DAG pakar ({len(spec['edges'])} panah) untuk {lbl(T)} → {lbl(Y)} dari config.py dan "
              "memastikan graf asiklik."]
    if adj:
        proses.append(f"Menentukan adjustment set dengan kriteria backdoor: {adj['Dikontrol']} dikontrol"
                      + (f"; mediator {adj['Mediator']} sengaja tidak dikontrol" if adj['Mediator'] != '-' else "")
                      + (f"; laten {adj['Laten']}" if adj['Laten'] != '-' else "") + ".")
        proses.append(f"Membatasi data{' (' + adj['Filter'] + ')' if adj['Filter'] != '-' else ''} ke kasus "
                      f"lengkap: n = {ribu(adj['n analisis'])} kelahiran.")
    proses += ["Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity "
               "score dipangkas pada persentil 1 dan 99.",
               "Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), "
               "dalam skala risk difference (RD) dan risk ratio (RR).",
               f"Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = {C.BOOT}).",
               "Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap "
               "confounder tak terukur (E-value)."]
    narasi = []
    if adj:
        ok = adj['Teridentifikasi'] == 'True'
        narasi.append(
            f"Berdasarkan DAG pakar, efek {lbl(T)} terhadap {lbl(Y)} "
            + ("**teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor."
               if ok else f"**tidak teridentifikasi sepenuhnya** karena ada confounder laten ({adj['Laten']}) yang "
                          "tidak terukur; estimasi berikut berisiko bias dan harus dibaca bersama E-value.")
            + (f" {adj['Mediator']} diperlakukan sebagai mediator dan tidak dikontrol, sehingga estimasi "
               "merupakan efek total." if adj['Mediator'] != '-' else ""))
    if est is not None:
        e = est.estimasi; lo, hi = est.ci_bawah, est.ci_atas
        rd, rr = e['aipw_RD'], e['aipw_RR']
        n_txt = f" pada {ribu(adj['n analisis'])} kelahiran" if adj else ""
        narasi.append(
            f"Estimator utama AIPW{n_txt} menunjukkan bahwa {lbl(T)} **{arah(rd)} risiko {lbl(Y)} sebesar "
            f"{a(100 * abs(rd), 2)} poin persen** (RD {a(rd, 4)}; CI 95% {ci_rd(lo['aipw_RD'], hi['aipw_RD'])}), "
            f"setara RR {a(rr, 2)} (CI 95% {a(lo['aipw_RR'], 2)}–{a(hi['aipw_RR'], 2)}). Risiko terprediksi "
            f"{pct(e['aipw_p1'], 2)} bila seluruh populasi menerima treatment dibanding {pct(e['aipw_p0'], 2)} bila "
            f"tidak. Efek ini {bermakna(lo['aipw_RD'], hi['aipw_RD'])}.")
        rds = [e['gcomp_RD'], e['ipw_RD'], rd]
        searah = all(x < 0 for x in rds) or all(x > 0 for x in rds)
        narasi.append(
            f"Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD {a(e['gcomp_RD'], 4)} dan IPW "
            f"{a(e['ipw_RD'], 4)}. Ketiga estimator " + ("searah" if searah else "tidak searah")
            + f" dengan selisih terbesar {a(100 * (max(rds) - min(rds)), 2)} poin persen"
            + ("; hasilnya cukup konsisten." if searah and max(rds) - min(rds) < 0.01
               else "; perbedaan ini menandakan hasil peka terhadap spesifikasi model propensity atau outcome."))
        bal = _csv(out / "keseimbangan.csv", index_col=0)
        if bal is not None:
            m0, m1 = bal.smd_awal.abs().max(), bal.smd_ipw.abs().max()
            narasi.append(f"Pembobotan IPW menurunkan |SMD| maksimum dari {a(m0, 2)} menjadi {a(m1, 2)}"
                          + (", di bawah ambang 0,1 sehingga kovariat seimbang." if m1 < 0.1 else
                             ", sedikit di atas ambang 0,1; masih ada ketidakseimbangan kecil yang dikoreksi oleh "
                             "komponen model outcome pada AIPW."))
        rr_ci = lo['aipw_RR'] if rr > 1 else hi['aipw_RR']
        ev_ci = 1.0 if lo['aipw_RR'] <= 1 <= hi['aipw_RR'] else evalue(rr_ci)
        narasi.append(f"E-value sebesar {a(evalue(rr), 2)} (batas CI {a(ev_ci, 2)}): confounder tak terukur harus "
                      f"berasosiasi dengan treatment dan outcome dengan RR minimal {a(evalue(rr), 2)} untuk "
                      "menghapus estimasi titik"
                      + ("; karena CI sudah memuat 1, efek belum dapat dibedakan dari nol." if ev_ci == 1.0
                         else f", dan minimal {a(ev_ci, 2)} untuk menggeser CI hingga memuat 1."))
    else:
        narasi.append("Estimasi efek belum dijalankan; klik **Jalankan estimasi** untuk melengkapi narasi.")
    return dict(proses=proses, narasi=narasi)


# ================================================================== menu 4
def _fit_label(f):
    if f['RMSEA'] < 0.06 and f['CFI'] > 0.95 and f['SRMR'] < 0.08:
        return "baik"
    return "cukup" if f['RMSEA'] < 0.08 and f['CFI'] > 0.90 else "kurang"


def baseline(nama):
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    out = C.OUT / "baseline" / nama
    tab = _csv(out / "perbandingan.csv")
    if tab is None:
        return None
    P = C.BASELINE
    i1, i2, i3 = _kv(out / "b1_info.csv"), _kv(out / "b2_info.csv"), _kv(out / "b3_info.csv")
    n = next(i for i in (i1, i2, i3) if i is not None)['n']
    p = sum(1 for v in C.TIER if v in {x.strip() for e in spec['edges'] for x in
                                       e.format(T=T, Y=Y).split('->')} and v not in spec['laten'])
    proses = [f"Menyiapkan data bersama: {ribu(n)} kasus lengkap pada {p} variabel teramati DAG pakar, masing-masing "
              "diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome)."]
    if i1 is not None:
        proses.append("B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), "
                      f"menilai kecocokan dengan n efektif = n/{a(P['deff'], 2)}, mendekomposisi efek langsung dan "
                      "tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.")
    if i2 is not None:
        proses.append(f"B2: menjalankan PC-stable (uji {i2['uji']}, α = {str(i2['alpha']).replace('.', ',')}, himpunan kondisi ≤ "
                      f"{i2['maks_kondisi']}), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 "
                      "menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.")
    if i3 is not None:
        proses.append(f"B3: mencari DAG dengan Hill-Climbing ber-tier (skor {i3['skor'].upper()}, graf awal "
                      f"{i3['awal']}, induk maks. {i3['maks_induk']}), lalu inferensi do dengan g-komputasi.")
    proses += ["Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → "
               "g-komputasi berbobot survei → CI 95% bootstrap PSU.",
               "Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi "
               "estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik."]

    narasi = []
    fit = _csv(out / "b1_kecocokan.csv", index_col=0)
    if fit is not None:
        f = fit.nilai; dek = _csv(out / "b1_dekomposisi.csv").set_index('komponen').estimasi
        narasi.append(
            f"**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **{_fit_label(f)}** (RMSEA "
            f"{a(f['RMSEA'])}, CFI {a(f['CFI'])}, SRMR {a(f['SRMR'])}; χ² = {a(f['chi2'], 1)}, df = {f['df']:.0f})."
            + (" Artinya, sebagian independensi bersyarat yang disiratkan DAG pakar tidak didukung data, atau ada "
               "panah yang terlewat." if _fit_label(f) != "baik" else "")
            + f" Dalam skala probabilitas, efek total {lbl(T)} adalah {a(dek['probit_RD'], 4)}, terdiri dari efek "
              f"langsung {a(dek['probit_RD_langsung'], 4)} dan tak langsung {a(dek['probit_RD_tak_langsung'], 4)}"
            + (" (melalui mediator)." if abs(dek['probit_RD_tak_langsung']) > 1e-9 else
               " (tidak ada mediator dalam DAG pakar)."))
    if i2 is not None:
        ida = _csv(out / "b2_ida.csv")
        narasi.append(
            f"**B2 (PC + tier + IDA).** Dengan {ribu(i2['jumlah_uji'])} uji independensi bersyarat, PC menemukan "
            f"{i2['sisi_berarah']} sisi berarah dan {i2['sisi_tak_berarah']} sisi tak berarah. Dibanding DAG pakar, "
            f"{i2['sisi_sama_pakar']} sisi sama, {i2['sisi_tambahan']} sisi tambahan, {i2['sisi_hilang']} sisi hilang, "
            f"dan {i2['arah_beda']} berbeda arah (SHD = {i2['SHD']}). Induk pasti {T}: {i2['induk_pasti_T']}. "
            f"IDA menghasilkan {i2['jumlah_himpunan_IDA']} himpunan induk"
            + (f" dengan RD {a(ida.RD.iloc[0], 4)}; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek "
               "secara unik." if len(ida) == 1 else
               f" dengan RD berkisar {a(ida.RD.min(), 4)} hingga {a(ida.RD.max(), 4)}; batas konservatifnya adalah "
               f"{a(ida.RD[ida.RD.abs().idxmin()], 4)}."))
    if i3 is not None:
        tanpa_jalur = 'tidak ada jalur' in str(i3['catatan'])
        narasi.append(
            f"**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah {i3['langkah']} langkah dengan {i3['sisi']} "
            f"sisi; skor akhir {a(float(i3['skor_akhir']), 1)} "
            + ("lebih tinggi" if float(i3['skor_akhir']) > float(i3['skor_DAG_pakar']) else "lebih rendah")
            + f" daripada skor DAG pakar {a(float(i3['skor_DAG_pakar']), 1)} pada skor yang sama (SHD = {i3['SHD']}). "
            + (f"Graf B3 **tidak memuat jalur berarah dari {T} ke {Y}**, sehingga menurut graf ini efek kausalnya nol. "
               "Hal ini lazim terjadi pada outcome langka atau lemah: penalti BIC menghapus sisi yang penambahan "
               "kecocokannya kecil." if tanpa_jalur else
               "Graf B3 memuat jalur berarah dari treatment ke outcome sehingga efek dihitung dengan inferensi do."))
    b = tab.set_index('kode')
    est = [f"{k} {a(b.RD[k], 4)} {ci_rd(b.RD_lo[k], b.RD_hi[k])}" for k in ('B1', 'B2', 'B3') if k in b.index]
    rds = [b.RD[k] for k in ('B1', 'B2', 'B3') if k in b.index and b.RD[k] != 0]
    narasi.append("**Perbandingan estimasi** (RD, CI 95%): " + "; ".join(est) + ". "
                  + ("Metode yang menghasilkan efek tak nol sepakat pada arah efek." if rds and
                     (all(x < 0 for x in rds) or all(x > 0 for x in rds)) else
                     "Arah efek berbeda antar-metode; kesimpulan kausal peka terhadap struktur graf."))
    rk = _csv(out / "rangkuman.csv")
    if rk is not None:
        t = rk[rk.terbaik].iloc[0]
        nk = {"BIC_SEM": "BIC-SEM", "CFI": "CFI", "lebar_CI": "lebar CI"}
        unggul = [nk[k] for k in nk if t[f"rank_{k}"] == 1]
        narasi.append(
            f"**Metode terbaik: {t.metode}** (peringkat rata-rata {a(t.peringkat_rata2, 2)}; unggul pada "
            f"{', '.join(unggul) or '-'}), dengan RD {a(t.RD, 4)} yang {bermakna(t.RD_lo, t.RD_hi)}. Karena tidak ada "
            "ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan "
            "estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi "
            "SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.")
    return dict(proses=proses, narasi=narasi)


# ================================================================== menu N1-N3
def _banding(out, kode, nk):
    """Kalimat perbandingan dengan baseline dari banding.csv."""
    b = _csv(out / "banding.csv")
    if b is None:
        return None
    t = b[b.terbaik].iloc[0]
    kr = [c[5:] for c in b if c.startswith('rank_')]
    unggul = [nk.get(k, k) for k in kr if t[f"rank_{k}"] == 1]
    n = b[b.kode == kode].iloc[0]
    posisi = int(b.peringkat_rata2.rank(method='min')[b.kode == kode].iloc[0])
    return (f"**Perbandingan dengan baseline.** Dengan kriteria {', '.join(nk.get(k, k) for k in kr)}, peringkat "
            f"rata-rata terbaik diraih **{t.metode}** ({a(t.peringkat_rata2, 2)}; unggul pada {', '.join(unggul) or '-'}); "
            f"{n.metode} berada di urutan ke-{posisi} dari {b.peringkat_rata2.notna().sum()} metode yang diperingkat "
            f"(peringkat rata-rata {a(n.peringkat_rata2, 2)}). "
            + ("Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. "
               if n.RD == 0 and n.RD_lo == n.RD_hi == 0 else
               f"Estimasi efeknya RD {a(n.RD, 4)} {ci_rd(n.RD_lo, n.RD_hi)}, {bermakna(n.RD_lo, n.RD_hi)}. ")
            + "Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji "
            "pada evaluasi semi-sintetik.")


NK = {"BIC_SEM": "BIC-SEM", "CFI": "CFI", "lebar_CI": "lebar CI", "detik_penemuan": "waktu penemuan",
      "memori_MB": "memori puncak"}


def novelty(metode, nama):
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    out = C.OUT / "novelty" / metode / nama
    pre = {"sd_hybrid": "sd", "to_dag": "to", "mlc_dag": "mlc"}[metode]
    i = _kv(out / f"{pre}_info.csv")
    if i is None:
        return None
    P = C.NOVELTY
    kode = {"sd_hybrid": "N1", "to_dag": "N2", "mlc_dag": "N3"}[metode]
    nol = 'tidak ada jalur' in str(i.get('catatan', ''))
    kal_nol = (f" Graf yang ditemukan **tidak memuat jalur berarah dari {T} ke {Y}**, sehingga efek kausal menurut "
               "graf ini nol." if nol else "")
    if metode == "sd_hybrid":
        proses = [
            f"Menyiapkan data yang sama dengan baseline: {ribu(i['n'])} kasus lengkap, tier waktu, bobot, PSU, strata.",
            f"Menghitung design effect umum δ̄ = {a(float(i['delta_bar']), 2)} (rerata deff klaster seluruh variabel, "
            f"linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = {ribu(float(i['n_eff']))}.",
            f"Membangun skeleton PC-stable dengan uji terkoreksi desain ({i['jumlah_uji']} uji, α = "
            f"{str(i['alpha']).replace('.', ',')}): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain "
            f"(korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = {i['df_desain']}) bila tidak.",
            f"Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood "
            f"berbobot ({i['skor'].upper()}) dengan penalti (k/2)·log n_eff.",
            "Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).",
        ]
        narasi = [
            f"Koreksi desain membuat skeleton lebih jarang: **{i['sisi_skeleton']} sisi** dibanding "
            f"{i['sisi_skeleton_B2_naif']} sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah "
            "hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. "
            f"Penalti skor juga memakai n_eff = {ribu(float(i['n_eff']))}, bukan n = {ribu(i['n'])}, sehingga graf "
            f"akhir memuat {i['sisi']} sisi (SHD terhadap DAG pakar {i['SHD']}).{kal_nol}"]
        sim = _csv(out / "sd_tipe1.csv")
        if sim is not None:
            narasi.append("**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC "
                          f"{a(P['sim_icc'], 2)}): " + "; ".join(
                              f"{r.uji} naif {pct(r['naif (B2)'])} vs terkoreksi {pct(r['terkoreksi desain (N1)'])}"
                              for _, r in sim.iterrows())
                          + f" (nominal {pct(sim.nominal.iloc[0])}). Ini menguji hipotesis (a) dokumen Tahap 3: uji "
                            "terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.")
        su = _csv(out / "sd_uji.csv")
        if su is not None and (su.efek > 0).any():
            dy = su[su.efek > 0]
            narasi.append("**Daya uji** (efek > 0): " + "; ".join(
                f"{r.uji}, efek {a(r.efek, 2)}: terkoreksi orde 2 {pct(r['terkoreksi orde 2'])} vs naif disesuaikan "
                f"ukuran {pct(r['naif disesuaikan ukuran'])}" for _, r in dy.iterrows())
                + ". Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya "
                  "dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan "
                  "sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.")
    elif metode == "to_dag":
        proses = [
            f"Menyiapkan data dan tier yang sama dengan baseline ({i['ukuran_tier']}).",
            f"Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = {i['ruang_urutan_tier']} urutan, "
            f"dibanding {i['ruang_urutan_tanpa_tier']} urutan tanpa tier dan {i['ruang_DAG']} DAG.",
            "Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per "
            f"tier sehingga setiap tier dioptimalkan terpisah (cukup {i['ruang_setelah_dekomposisi']} urutan diperiksa); "
            f"tier ≤ {P['to_eksak_maks']} variabel diselesaikan eksak dengan pemrograman dinamis subset.",
            f"Memilih induk setiap node dengan grow-shrink (induk maks. {i['maks_induk']}) memakai skor "
            f"{i['skor'].upper()}" + (f" berbobot survei dengan penalti log n_eff (n_eff = "
                                      f"{ribu(float(i['n_penalti']))})" if str(i['berbobot']) == 'True' else "")
            + "; skor lokal disimpan dalam cache.",
            "Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).",
        ]
        narasi = [
            f"TO-DAG menyelesaikan penemuan graf dalam **{a(float(i['detik_penemuan']), 2)} detik** dengan memori "
            f"puncak {a(float(i['memori_MB']), 1)} MB dan {ribu(i['skor_lokal_dihitung'])} skor lokal. Pada fungsi "
            f"skor yang sama, skor graf TO-DAG {a(float(i['skor_TO_DAG']), 1)} dibanding graf B3 "
            f"{a(float(i['skor_B3_pada_skor_sama']), 1)} dan DAG pakar {a(float(i['skor_pakar_pada_skor_sama']), 1)}"
            + (", artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3."
               if float(i['skor_TO_DAG']) > float(i['skor_B3_pada_skor_sama']) else
               ", artinya Hill-Climbing B3 masih menemukan graf dengan skor lebih tinggi.")
            + f" Graf akhir memuat {i['sisi']} sisi (SHD terhadap DAG pakar {i['SHD']}).{kal_nol}",
            "Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya "
            "naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; "
            "satu variabel yang salah tier melarang panah yang benar.",
        ]
    else:
        proses = [
            f"Membentuk data MLC: {ribu(i['n'])} kasus lengkap pada {i['indikator_awal']} indikator konstruk dan "
            "variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).",
            "Menetapkan jenis konstruk (N3 v2): " + (f"komposit formatif {i['konstruk_komposit']}; reflektif "
            f"{i['konstruk_reflektif']}; reflektif yang dipecah karena ω < {str(i['omega_min']).replace('.', ',')}: "
            f"{i['konstruk_dipecah']}." if 'konstruk_komposit' in i else "semua reflektif (versi awal)."),
            "Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial "
            "(biner–kontinu), Pearson berbobot (lainnya).",
            f"Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan "
            f"lintas konstruk serta batas muatan {a(P['mlc_muatan_min'], 2)}: {i['indikator_dibuang']} indikator dibuang.",
            "Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), "
            f"sehingga statistik cukup Σ̂_V hanya berukuran {i['node_struktural']}×{i['node_struktural']}.",
            f"Menemukan DAG pada Σ̂_V ({i['penemuan']}), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan "
            f"yang sama pada {i['node_tanpa_konstruk']} node indikator mentah).",
            "Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.",
        ]
        narasi = [
            f"Konstruk laten mengecilkan graf dari **{i['node_tanpa_konstruk']} menjadi {i['node_struktural']} node** "
            f"(statistik cukup {ribu(i['entri_tanpa_konstruk'])} → {ribu(i['entri_statistik_cukup'])} entri). Tahap "
            f"penemuan struktur hanya {a(float(i['detik_struktur']), 3)} detik ({i['uji_atau_skor']}) dibanding "
            f"{a(float(i['detik_struktur_tanpa_konstruk']), 3)} detik ({i['uji_atau_skor_tanpa_konstruk']}) tanpa "
            f"konstruk; biaya terbesar justru korelasi tetrakorik ({a(float(i['detik_korelasi']), 2)} detik) yang "
            f"dipakai bersama oleh keduanya.{kal_nol}",
            f"Reliabilitas / jenis konstruk: {i['reliabilitas_omega'].replace('.', ',')}. Aset dan akses diperlakukan "
            "sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu "
            "faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai."
            + (f" **Konstruk bermasalah:** {i['konstruk_bermasalah'].replace('.', ',')}; indikator ini tetap bermuatan lemah setelah "
               "purifikasi karena konstruk sudah tinggal tiga indikator. Hal ini sesuai kelemahan yang diantisipasi "
               "dokumen: konstruk campuran level individu dan provinsi melanggar asumsi satu faktor."
               if i['konstruk_bermasalah'] != '-' else ""),
        ]
    kal = _banding(out, kode, NK)
    if kal:
        narasi.append(kal)
    return dict(proses=proses, narasi=narasi)


# ================================================================== SOL-DAG dan benchmark
def sol(nama):
    spec = C.ANALISIS[nama]; T, Y = spec['T'], spec['Y']
    out = C.OUT / "sol_dag" / nama
    v = _csv(out / "sol_varian.csv")
    if v is None:
        return None
    S = C.SOL
    s0 = v[v.varian == "SOL-DAG"].iloc[0] if (v.varian == "SOL-DAG").any() else v.iloc[0]
    proses = [
        f"Langkah 1 (MLC v2): konstruk reflektif {s0.reflektif}; komposit formatif {s0.komposit}; konstruk yang "
        f"dipecah menjadi indikator {s0.dipecah}; kovarians Σ̂_V terkoreksi galat ukur ({int(s0.node)} node).",
        f"Langkah 2 (SD-Hybrid): skeleton PC-stable dengan uji terkoreksi desain (Rao-Scott orde {S['rs_orde']} / "
        f"t-desain, α = {str(S['alpha']).replace('.', ',')}); {int(s0.jumlah_uji)} uji, {int(s0.sisi_skeleton)} sisi.",
        f"Langkah 3 (TO-DAG): pencarian urutan di dalam tier dengan skor Gauss berskala n_eff = {ribu(s0.n_eff)}, "
        "induk dibatasi skeleton.",
        f"Langkah 4 (estimasi): PSU dibagi dua di dalam strata; graf ditemukan pada separuh A ({ribu(s0.n_A)} kelahiran), "
        f"AIPW berbobot survei pada separuh B ({ribu(s0.n_B)}), CI bootstrap PSU ({S['boot']} replikasi).",
        "Ablasi: mengulang pipeline dengan mematikan satu komponen (MLC, koreksi desain, tier, pemisahan sampel).",
    ]
    nol = s0.catatan != "-"
    narasi = [
        f"SOL-DAG menemukan graf dengan {int(s0.sisi)} sisi pada {int(s0.node)} node dalam "
        f"{a(s0.detik_penemuan, 1)} detik (memori puncak {a(s0.memori_MB, 1)} MB). "
        + (f"Graf ini **tidak memuat jalur berarah dari {T} ke {Y}**, sehingga efek {lbl(T)} terhadap {lbl(Y)} "
           "menurut SOL-DAG adalah nol. Penyebabnya, uji terkoreksi desain menghapus sisi yang hanya lemah bermakna "
           "setelah dikondisikan pada variabel konteks; ini adalah kehilangan daya uji yang diantisipasi dokumen Tahap 3."
           if nol else
           f"AIPW pada separuh B memperkirakan {lbl(T)} **{arah(s0.RD)} risiko {lbl(Y)} sebesar "
           f"{a(100 * abs(s0.RD), 2)} poin persen** (RD {a(s0.RD, 4)}; CI 95% {ci_rd(s0.RD_lo, s0.RD_hi)}), "
           f"{bermakna(s0.RD_lo, s0.RD_hi)}."),
        "**Ablasi.** " + "; ".join(
            f"{r.varian}: {int(r.sisi)} sisi, skeleton {int(r.sisi_skeleton)}, RD {a(r.RD, 4)}"
            + (" (tanpa jalur T→Y)" if r.catatan != "-" else "") for r in v.itertuples() if r.varian != "SOL-DAG")
        + ". Perbedaan antar-varian menunjukkan kontribusi tiap komponen pada data nyata; uji formal H1–H5 dengan "
          "graf benar ada di menu Benchmark.",
    ]
    v2 = _csv(out / "sol_v2.csv")
    if v2 is not None:
        proses.append("SOL v2 (pra-registrasi): graf PC-stable + tier dengan uji-t desain hanya memilih himpunan "
                      "penyesuaian (induk T, ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU dan SE "
                      "fungsi pengaruh + linearisasi desain.")
        narasi.append("**SOL v2.** " + "; ".join(
            f"{r.varian}: RD {a(r.RD, 4)} {ci_rd(r.RD_lo, r.RD_hi)} ({bermakna(r.RD_lo, r.RD_hi)}), induk T: {r.induk_T}"
            for r in v2.itertuples()) + ". Berbeda dengan v1, efek tidak lagi dinolkan ketika graf tidak memuat jalur "
            "T→Y; graf hanya menentukan variabel yang dikontrol.")
    return dict(proses=proses, narasi=narasi)


def benchmark(nama):
    import json
    out = C.OUT / "benchmark" / nama
    pt, rk = _csv(out / "putusan.csv"), _csv(out / "ringkasan.csv")
    if pt is None or rk is None:
        return None
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8")) if (out / "meta.json").exists() else {}
    B = meta.get('konfigurasi', C.BENCH)
    proses = [
        f"Skenario A: graf benar = DAG pakar {nama} dengan {a(100 * B['perturbasi'], 0)}% panah diganti (patuh tier); "
        "SCM dicocokkan pada IDHS (logistik/linear berbobot) dengan efek acak PSU dari ANOVA residual.",
        "Skenario B: node = konstruk/komposit MLC v2 dan variabel teramati; graf benar = DAG pakar dipetakan ke "
        "tingkat konstruk lalu diperturbasi; indikator dibangkitkan dari konstruknya (muatan nyata, ambang prevalensi).",
        f"Setiap skenario diulang {meta.get('rep', B['rep'])} kali dengan bobot, PSU, dan strata IDHS asli; efek benar "
        "dihitung secara kontrafaktual do(T=1) − do(T=0) dengan noise bersama.",
        "Metrik yang sama untuk semua metode: SHD, SID, |galat RD| (RMSE), waktu dan memori penemuan, stabilitas "
        f"(SHD antar-replikasi), cakupan CI 95% ({B['boot']} bootstrap PSU), galat tipe I dan daya uji pada "
        f"{B['n_pernyataan']} pernyataan independensi/dependensi benar.",
        "Uji hipotesis: SOL-DAG vs setiap pembanding dengan Wilcoxon berpasangan satu sisi, p dikoreksi Holm per "
        "hipotesis; H5 dengan interval Wilson terhadap target nominal.",
    ]
    narasi = []
    for s in ("A", "B"):
        if s in meta:
            narasi.append(f"**Skenario {s}.** Efek benar RD = {a(meta[s]['RD_benar'], 4)} "
                          f"({pct(meta[s]['p1'])} vs {pct(meta[s]['p0'])}); graf benar {meta[s]['sisi_benar']} sisi.")
            r = rk[rk.skenario == s]
            if len(r):
                b_shd, b_rm = r.loc[r.SHD.idxmin()], r.loc[r.RMSE.idxmin()]
                sol_ = r[r.metode == "SOL-DAG"]
                narasi[-1] += (f" SHD terkecil: {b_shd.metode} ({a(b_shd.SHD, 1)}); RMSE efek terkecil: {b_rm.metode} "
                               f"({a(b_rm.RMSE, 4)}).")
                if len(sol_):
                    x = sol_.iloc[0]
                    narasi[-1] += (f" SOL-DAG: SHD {a(x.SHD, 1)}, SID {a(x.SID, 1)}, RMSE {a(x.RMSE, 4)}, efek nol pada "
                                   f"{pct(x.efek_nol, 0)} replikasi, cakupan CI {pct(x.cakupan, 0) if x.cakupan == x.cakupan else '–'}.")
    warna = {"didukung": "didukung", "didukung sebagian": "didukung sebagian", "tidak didukung": "tidak didukung"}
    narasi.append("**Putusan hipotesis.** " + "; ".join(
        f"{r.hipotesis} ({r.aspek}): **{warna.get(r.putusan, r.putusan)}** ({r.SOL_lebih_baik}/{r.perbandingan})"
        for r in pt.itertuples()) + ".")
    h5 = _csv(out / "hipotesis_H5.csv")
    if h5 is not None and len(h5):
        t1 = h5[h5.ukuran == "galat tipe I"].set_index('uji')
        if len(t1) == 2:
            narasi.append(f"**H5 — validitas koreksi desain.** Pada pernyataan independensi yang benar, uji naif menolak "
                          f"{pct(t1.loc['naif', 'nilai'])} (CI {ci_pct(t1.loc['naif', 'ci_lo'], t1.loc['naif', 'ci_hi'])}) "
                          f"dan uji terkoreksi {pct(t1.loc['terkoreksi', 'nilai'])} "
                          f"(CI {ci_pct(t1.loc['terkoreksi', 'ci_lo'], t1.loc['terkoreksi', 'ci_hi'])}) terhadap nominal "
                          f"{pct(C.BENCH['alpha_uji'], 0)}.")
    narasi.append("Benchmark ini memakai satu analisis dan satu graf benar per skenario; kesimpulan umum memerlukan "
                  "variasi graf, ukuran efek, dan kekuatan klaster.")
    import benchmark as BM
    _, hv = BM.evaluasi_v2()
    if len(hv):
        proses.append("Benchmark v2 (pra-registrasi): DAG acak patuh tier yang independen dari metode, grid ICC {0,05; "
                      "0,4} × β_TY {−0,6; −0,15; 0}, 200 replikasi per sel; varian v2 desain, v2 naif, dan aturan v1.")
        narasi.append("**Benchmark v2 (pra-registrasi).** " + "; ".join(
            f"{r.kode} ({r.hipotesis}): **{r.putusan}** — {r.hasil}" for r in hv.itertuples()) + ".")
    _, _, h3 = BM.evaluasi_v3()
    if len(h3):
        proses.append("Benchmark v3 (pra-registrasi S6–S10): desain sintetis setara IDHS (67 strata × 29 PSU × 9), ICC "
                      "heterogen U(0,1; 0,8) vs homogen 0,45; lima uji CI (naif, Kish, deff-global, sandwich CR1, desain "
                      "usulan); S8 200 replikasi, dampak hilir 100 replikasi (p = 15 utama, 30 sekunder).")
        narasi.append("**Benchmark v3 (pra-registrasi).** " + "; ".join(
            f"{r.kode} ({r.hipotesis}): **{r.putusan}** — {r.hasil}" for r in h3.itertuples()) + ". " + BM.TAFSIR_V3)
    return dict(proses=proses, narasi=narasi)


# ================================================================== benchmark v4 (M0-M6, bench_v4.py)
_CACHE_V4 = {}
URUT_V4 = ["M0", "M1", "M2", "M3", "M4(aT=0.1)", "M4(aT=0.2)", "M4(aT=0.3)", "M5", "M6"]


def data_v4(dasar=None):
    """per_rep.csv benchmark v4 (+ kolom galat) dari <dasar>/benchmark_v4; None bila belum ada. dasar = C.OUT."""
    f = (dasar or C.OUT) / "benchmark_v4" / "per_rep.csv"
    if not f.exists():
        return None
    kunci = (str(f), f.stat().st_mtime)
    if kunci not in _CACHE_V4:
        _CACHE_V4.clear()
        d = pd.read_csv(f, dtype={"icc": str}); d['galat'] = d.RD_hat - d.RD_benar
        _CACHE_V4[kunci] = d
    return _CACHE_V4[kunci]


def kinerja_v4(d):
    """Satu baris per metode: validitas (+ interval Wilson), bias, RMSE, cakupan, lebar CI, |Z|, FDR, recall."""
    def f(g):
        n, p = len(g), g.valid.mean(); z = 1.96; dd = 1 + z ** 2 / n
        c, h = (p + z ** 2 / (2 * n)) / dd, z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / dd
        return pd.Series(dict(replikasi=n, valid=p, valid_lo=c - h, valid_hi=c + h, bias=g.galat.mean(),
                              RMSE=np.sqrt((g.galat ** 2).mean()), cakupan=g.cakup.mean(),
                              lebar_CI=(g.RD_hi - g.RD_lo).mean(), n_Z=g.n_Z.mean(), FDR=g.FDR.mean(), recall=g.recall.mean()))
    t = d.groupby("metode").apply(f)
    return t.reindex([m for m in URUT_V4 if m in t.index]).reset_index()


def benchmark_v4(dasar=None):
    dasar = dasar or C.OUT
    d, hp = data_v4(dasar), _csv(dasar / "benchmark_v4" / "hipotesis.csv")
    if d is None or hp is None:
        return None
    f = dasar / "benchmark_v4" / "meta.json"
    B = (json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}).get('konfigurasi', C.BENCH_V4)
    h = kinerja_v4(d[d.icc == "heterogen"]).set_index("metode")
    v, rm, ck, fd = (lambda m: pct(h.valid[m])), (lambda m: a(h.RMSE[m], 4)), (lambda m: pct(h.cakupan[m])), (lambda m: pct(h.FDR[m]))
    n_sel, n_rep = d.sel.nunique(), d.groupby(['sel', 'rep']).ngroups
    S, K, U = B['desain']
    proses = [
        f"Setiap replikasi membangkitkan graf acak patuh tier ({' atau '.join(str(x) for x in B['p'])} node): kovariat di "
        "tier 0–2, treatment biner T di tier 3, outcome biner Y di tier 4; tiga kovariat dipaksa menjadi confounder "
        f"(kuat: koefisien 0,30–0,50; lemah: 0,05–0,15) dan {a(100 * B['laten_frac'], 0)}% kovariat lain disembunyikan dari metode.",
        f"Data dibangkitkan pada desain sintetis setara IDHS ({S} strata × {K} PSU × {U} unit) dengan efek acak PSU per "
        "variabel (ICC heterogen U(0,1; 0,8) atau 0,15); efek benar dihitung eksak dari model probit.",
        "Tujuh strategi memilih himpunan penyesuaian: M0 semua kovariat pra-treatment; M1 induk T di DAG pakar yang 30% "
        "panahnya keliru; M2 PC naif; M3 PC dengan uji terkoreksi desain; M4 = M3 dengan α longgar "
        f"({', '.join(a(x, 2) for x in B['alpha_T'])}) untuk pasangan yang melibatkan T atau Y; M5 induk T dari M3 ∪ M1; "
        "M6 induk T atau induk Y dari graf M3.",
        f"Semua strategi memakai estimator yang sama: AIPW cross-fitting {B['K']} lipatan per PSU, SE linearisasi desain, "
        "sehingga perbedaan hasil hanya berasal dari himpunan penyesuaian.",
        f"Grid {n_sel} sel (ICC × efek × kekuatan confounder × jumlah node), {ribu(n_rep / n_sel)} replikasi per sel = "
        f"{ribu(n_rep)} survei simulasi. Ukuran: validitas himpunan penyesuaian di graf benar, FDR skeleton, RMSE, dan cakupan CI 95%.",
        "Hipotesis H10–H13 dan cara membacanya dikunci sebelum simulasi penuh (RENCANA_ANALISIS_v4.md, tag git "
        "rencana-v4) dan diuji pada sel ICC heterogen.",
    ]
    k = d.pivot_table(index="metode", columns="kuat", values="valid")
    pen = d[d.metode.str.match(r"M[234]")]
    rmse = lambda x: a(np.sqrt((x.galat ** 2).mean()), 4)
    narasi = [
        f"**Kalibrasi melawan identifikasi.** Koreksi desain memperbaiki graf: FDR skeleton turun dari {fd('M2')} (M2, uji "
        f"naif) menjadi {fd('M3')} (M3, uji terkoreksi). Namun himpunan penyesuaian yang valid justru turun dari {v('M2')} "
        f"menjadi {v('M3')}, dan RMSE naik dari {rm('M2')} menjadi {rm('M3')}. Uji yang ukurannya benar lebih sulit "
        "mendeteksi sisi confounder yang lemah, sehingga graf yang lebih baik menghasilkan himpunan penyesuaian yang lebih buruk.",
        f"**Melonggarkan α (M4) hanya memulihkan sebagian.** Validitas naik dari {v('M4(aT=0.1)')} pada α_T = 0,10 menjadi "
        f"{v('M4(aT=0.3)')} pada 0,30, dengan FDR tetap {fd('M4(aT=0.1)')}–{fd('M4(aT=0.3)')}. Memperbesar himpunan lebih "
        f"efektif: M5 mencapai {v('M5')} dan M6 {v('M6')}.",
        f"**Dua acuan.** M0 (semua kovariat pra-treatment) valid pada {v('M0')} replikasi dengan RMSE {rm('M0')} dan cakupan "
        f"{ck('M0')}, memakai rata-rata {a(h.n_Z['M0'], 1)} kovariat (M6: {a(h.n_Z['M6'], 1)}). M1 (DAG pakar yang 30% "
        f"keliru) adalah pilihan terburuk: valid {v('M1')}, RMSE {rm('M1')}, cakupan {ck('M1')}.",
        f"**Kekuatan confounder menentukan.** Pada semua sel, validitas dengan confounder kuat adalah {pct(k.kuat['M2'])} "
        f"(M2), {pct(k.kuat['M3'])} (M3), dan {pct(k.kuat['M6'])} (M6); dengan confounder lemah turun menjadi "
        f"{pct(k.lemah['M2'])}, {pct(k.lemah['M3'])}, dan {pct(k.lemah['M6'])}. Untuk M2–M4, RMSE {rmse(pen[pen.valid])} bila "
        f"himpunannya valid dan {rmse(pen[~pen.valid])} bila tidak; cakupan {pct(pen[pen.valid].cakup.mean())} dan "
        f"{pct(pen[~pen.valid].cakup.mean())}.",
        "**Putusan hipotesis.** " + "; ".join(f"{r.kode}: **{r.putusan}** — {r.hasil}" for r in hp.itertuples()
                                               if r.kode.startswith("H")) + ". H10 ditolak, sehingga sesuai rencana hasil ini "
        "dibaca sebagai peringatan: penemuan graf dengan uji terkalibrasi belum dapat diandalkan untuk memilih confounder. "
        "H12 ditolak hanya pada nilai titik; M6 dan M0 praktis setara dalam ketepatan.",
    ]
    idhs = []
    for an in ("sanitasi_diare", "pbi_diare"):
        rd = _csv(dasar / "idhs_m0m6" / an / "rd.csv")
        if rd is not None:
            idhs.append(f"{lbl(C.ANALISIS[an]['T'])} → {lbl(C.ANALISIS[an]['Y'])}: RD {a(rd.RD.min(), 4)} sampai "
                        f"{a(rd.RD.max(), 4)} di ketujuh strategi (n = {ribu(rd.n.iloc[0])}), "
                        + ("semua CI 95% tidak memuat nol" if ((rd.RD_lo > 0) | (rd.RD_hi < 0)).all() else "sebagian CI 95% memuat nol"))
    if idhs:
        narasi.append("**M0–M6 pada IDHS 2017.** " + "; ".join(idhs) + ". Efek benar tidak diketahui pada data nyata; yang "
                      "dibaca adalah konsistensi antar-himpunan, bukan peringkat metode. Arah positif pada JKN PBI "
                      "mencerminkan confounding penargetan, bukan bukti bahaya.")
    narasi.append("Keterbatasan: graf simulasi tidak memuat mediator antara T dan Y, sehingga M0 aman secara konstruksi; "
                  "efek laten linear, satu desain sampling, dan satu algoritma penemuan (PC-stable).")
    return dict(proses=proses, narasi=narasi)


# ================================================================== semua
def semua(df):
    bag = [md("1. Persiapan Data", prep(df)), md("2. Eksplorasi Data", eda())]
    bag += [md(f"3. Inferensi Kausal — {n}", kausal(n)) for n in C.ANALISIS]
    bag += [md(f"4. Baseline — {n}", baseline(n)) for n in C.ANALISIS]
    for k, j in [("sd_hybrid", "N1 SD-Hybrid"), ("to_dag", "N2 TO-DAG"), ("mlc_dag", "N3 MLC-DAG")]:
        bag += [md(f"{j} — {n}", novelty(k, n)) for n in C.ANALISIS]
    bag += [md(f"SOL-DAG — {n}", sol(n)) for n in C.ANALISIS]
    bag += [md(f"Benchmark semi-sintetik — {n}", benchmark(n)) for n in C.ANALISIS]
    bag += [md("Benchmark v4 — pemilihan confounder M0–M6", benchmark_v4())]
    return "# Narasi hasil analisis IDHS 2017\n\n" + "\n".join(b for b in bag if b)
