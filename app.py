"""Tampilan Streamlit: menu di kiri, proses & hasil di kanan.
  .venv\\Scripts\\streamlit run app.py"""
import time
import pandas as pd
import streamlit as st
import config as C
import prep, eda, causal, baseline, narasi, novelty, laporan, sol_dag, benchmark
from main import log

st.set_page_config(page_title="Kausal IDHS 2017", page_icon="🧭", layout="wide")

NOVELTY_MENU = {"N1 SD-Hybrid": "sd_hybrid", "N2 TO-DAG": "to_dag", "N3 MLC-DAG": "mlc_dag"}
MENU_V4 = "Benchmark v4 (M0–M6)"
MENU = ["Persiapan Data", "EDA", "Inferensi Kausal", "Baseline (B1–B3)", *NOVELTY_MENU, "SOL-DAG",
        "Benchmark (H1–H5)", MENU_V4]
PKL = C.CACHE / "analisis.pkl"
EDA_OUT = C.OUT / "eda"


@st.cache_data(show_spinner="Memuat dataset analisis...")
def load_data(mtime):
    return pd.read_pickle(PKL)


def data():
    return load_data(PKL.stat().st_mtime) if PKL.exists() else None


def csv(p, **kw):
    try:
        return pd.read_csv(p, **kw) if p.exists() else None
    except pd.errors.EmptyDataError:
        return None


def ringkasan(lines):
    st.code("\n".join(lines), language=None)


def proses(label, fn):
    """Jalankan satu langkah dengan indikator status; galat ditampilkan, aplikasi tetap hidup."""
    t0 = time.time()
    with st.status(label, expanded=True) as s:
        try:
            lines = fn()
            log(lines)
            ringkasan(lines)
            s.update(label=f"{label} — selesai ({time.time() - t0:.0f} detik)", state="complete")
            return True
        except Exception as e:
            st.exception(e)
            s.update(label=f"{label} — GAGAL", state="error")
            return False


def tampil_narasi(judul, r, berkas):
    """Panel rangkuman proses + narasi otomatis, dengan unduhan Markdown."""
    if r is None:
        return
    with st.expander("📝 Rangkuman proses & narasi", expanded=True):
        a, b = st.columns(2)
        a.markdown("**Rangkuman proses**\n\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(r['proses'], 1)))
        b.markdown("**Narasi**\n\n" + "\n\n".join(r['narasi']))
        st.download_button("⬇️ Unduh narasi (.md)", narasi.md(judul, r).encode("utf-8"), berkas,
                           mime="text/markdown", key=f"unduh_{berkas}")


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def panel_laporan(kunci):
    """Tombol unduh laporan Word bernama sesuai menu (kunci BAGIAN, atau 'lengkap') + tombol buat/perbarui."""
    f = laporan.berkas(kunci)
    if f.exists():
        st.download_button(f"⬇️ {f.name}", f.read_bytes(), f.name, mime=DOCX_MIME,
                           type="primary", width="stretch", key=f"lap_unduh_{kunci}")
        st.caption("Versi " + time.strftime('%d-%m-%Y %H:%M', time.localtime(f.stat().st_mtime))
                   + ". Perbarui setelah menjalankan ulang menu.")
    else:
        st.caption(f"{f.name} belum dibuat.")
    if st.button("🔄 Buat / perbarui laporan" if f.exists() else "🛠️ Buat laporan", width="stretch",
                 key=f"lap_buat_{kunci}"):
        with st.spinner("Menyusun dokumen..."):
            laporan.buat_menu(kunci)
        st.rerun()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.title("🧭 Kausal IDHS 2017")
    st.caption("Sanitasi, JKN PBI, persalinan di fasilitas")
    halaman = st.radio("Menu", MENU, label_visibility="collapsed")
    st.divider()
    raw_ok = all((C.RAW / f"{k}DT.zip").exists() for k in ("IDBR71", "IDHR71"))
    st.markdown(f"**Data mentah:** {'✅ ada' if raw_ok else '❌ belum ada'}")
    st.markdown("**Dataset analisis:** " + (
        "✅ " + time.strftime('%d-%m-%Y %H:%M', time.localtime(PKL.stat().st_mtime)) if PKL.exists() else "⏳ belum dibuat"))
    st.markdown(f"**Hasil EDA:** {'✅ ada' if (EDA_OUT / '02_deskriptif_svy.csv').exists() else '⏳ belum'}")
    st.divider()
    semua_klik = st.button("⏩ Jalankan semua (1 → 2 → 3)", width="stretch", disabled=not raw_ok,
                           help=f"Persiapan data, EDA, lalu semua analisis kausal (bootstrap={C.BOOT})")
    if PKL.exists():
        st.download_button("⬇️ NARASI lengkap (.md)", narasi.semua(data()).encode("utf-8"), "NARASI.md",
                           mime="text/markdown", width="stretch", help="Rangkuman proses & narasi seluruh menu")
    st.divider()
    st.markdown("**📄 Laporan Word**  \nBaseline, N1, N2, N3: hasil, perbandingan, uji galat, tabel, grafik, narasi")
    panel_laporan("lengkap")
    with st.expander("Laporan sebagian (pilih menu/analisis)"):
        lap_bag = st.multiselect("Menu", list(laporan.BAGIAN), list(laporan.BAGIAN),
                                 format_func=laporan.BAGIAN.get, key="lap_bag")
        lap_an = st.multiselect("Analisis", list(C.ANALISIS), list(C.ANALISIS), key="lap_an")
        if st.button("🛠️ Buat laporan sebagian", width="stretch", disabled=not (lap_bag and lap_an)):
            with st.spinner("Menyusun dokumen..."):
                urut = [b for b in laporan.BAGIAN if b in lap_bag]
                st.session_state["lap_docx"] = (laporan.buat(urut, lap_an), laporan.nama_sebagian(urut, lap_an))
        if "lap_docx" in st.session_state:
            isi, nm = st.session_state["lap_docx"]
            st.download_button(f"⬇️ {nm}", isi, nm, width="stretch", mime=DOCX_MIME)
    ring = C.OUT / "RINGKASAN.txt"
    if ring.exists():
        st.divider()
        st.download_button("⬇️ RINGKASAN.txt", ring.read_bytes(), "RINGKASAN.txt", width="stretch")

if semua_klik:
    st.header("Jalankan semua")
    bar = st.progress(0.0, text="Menyiapkan...")
    ok = (proses("1. Persiapan data", prep.run)
          and proses("2. EDA", lambda: eda.run(prep.load()))
          and proses(f"3. Inferensi kausal (semua, bootstrap={C.BOOT})",
                     lambda: causal.run(prep.load(), None,
                                        progress=lambda n, i, b: bar.progress(i / b, text=f"{n}: bootstrap {i}/{b}"))))
    bar.empty()
    load_data.clear()
    if ok:
        st.success("Semua langkah selesai. Pilih menu di kiri untuk melihat hasil tiap tahap.")
    st.stop()

# ------------------------------------------------------------------ 1. Persiapan data
if halaman == "Persiapan Data":
    kiri, kanan = st.columns([3, 1])
    kiri.header("1. Persiapan Data")
    with kanan:
        panel_laporan("prep")
    st.write("IDBR71 (kelahiran) + IDHR71 (rumah tangga) + konteks provinsi → `cache/analisis.pkl` "
             "dan `hasil/dataset_analisis.csv`.")
    if not raw_ok:
        st.error(f"Taruh IDBR71DT.zip dan IDHR71DT.zip di folder `{C.RAW}`.")
    if st.button("▶️ Jalankan persiapan data", type="primary", disabled=not raw_ok):
        if proses("Persiapan data", prep.run):
            load_data.clear()

    df = data()
    if df is None:
        st.info("Dataset belum dibuat. Klik tombol di atas.")
    else:
        c = st.columns(4)
        c[0].metric("Kelahiran", f"{len(df):,}".replace(",", "."))
        c[1].metric("Variabel", df.shape[1])
        c[2].metric("Klaster", df.klaster.nunique())
        c[3].metric("Provinsi", df.kode_prov_v024.nunique())
        tampil_narasi("1. Persiapan Data", narasi.prep(df), "narasi_1_persiapan.md")
        t1, t2, t3 = st.tabs(["Pratinjau data", "Kelengkapan variabel", "Kamus variabel"])
        with t1:
            st.dataframe(df.head(200), width="stretch", height=420)
        with t2:
            m = df.isna().mean().sort_values(ascending=False).rename("proporsi kosong").to_frame()
            st.dataframe(m.style.format("{:.1%}").background_gradient(cmap="Reds", vmin=0, vmax=1),
                         width="stretch", height=420)
        with t3:
            kamus = pd.DataFrame({"tipe": df.dtypes.astype(str), "n terisi": df.notna().sum(),
                                  "unik": df.nunique()})
            kamus["kelompok"] = [("Treatment" if k.startswith("T_") else "Outcome" if k.startswith("Y_")
                                  else "Mediator" if k.startswith("M_") else "Kovariat") for k in kamus.index]
            st.dataframe(kamus, width="stretch", height=420)
        p = C.OUT / "dataset_analisis.csv"
        if p.exists():
            st.download_button("⬇️ Unduh dataset_analisis.csv", p.read_bytes(), p.name)

# ------------------------------------------------------------------ 2. EDA
elif halaman == "EDA":
    kiri, kanan = st.columns([3, 1])
    kiri.header("2. Eksplorasi Data (berbobot survei)")
    with kanan:
        panel_laporan("eda")
    st.write("Deskriptif berbobot + SE desain (strata, PSU), SMD kovariat per treatment, "
             "sebaran per kuintil kekayaan dan provinsi.")
    if st.button("▶️ Jalankan EDA", type="primary"):
        proses("EDA", lambda: eda.run(prep.load()))
        load_data.clear()

    desk = csv(EDA_OUT / "02_deskriptif_svy.csv")
    if desk is None:
        st.info("Hasil EDA belum ada. Klik tombol di atas.")
    else:
        tampil_narasi("2. Eksplorasi Data", narasi.eda(), "narasi_2_eda.md")
        t1, t2, t3, t4, t5 = st.tabs(["Deskriptif", "Per kuintil", "Per provinsi", "Keseimbangan (SMD)", "Data kosong"])
        with t1:
            st.dataframe(desk.style.format({"rerata": "{:.3f}", "se": "{:.4f}", "ci_bawah": "{:.3f}",
                                            "ci_atas": "{:.3f}"}), width="stretch", hide_index=True)
            st.image(str(EDA_OUT / "07_korelasi.png"), caption="Korelasi antar variabel utama")
        with t2:
            st.dataframe(csv(EDA_OUT / "03_per_kuintil.csv", index_col=0).style.format("{:.3f}"), width="stretch")
            st.image(str(EDA_OUT / "06_kuintil.png"), caption="Treatment & diare per kuintil kekayaan non-WASH")
        with t3:
            prov = csv(EDA_OUT / "04_per_provinsi.csv", index_col=0)
            st.dataframe(prov.style.format("{:.3f}").background_gradient(cmap="Blues"), width="stretch", height=500)
            kol = st.selectbox("Grafik per provinsi untuk:", prov.columns)
            st.bar_chart(prov[kol].sort_values(), horizontal=True, height=700)
        with t4:
            bal = csv(EDA_OUT / "05_smd_per_treatment.csv", index_col=0)
            st.caption("|SMD| > 0,1 menandakan ketidakseimbangan kovariat antara kelompok treatment.")
            st.dataframe(bal.style.format("{:+.3f}").map(
                lambda v: "background-color: #f8d7da" if abs(v) > 0.1 else ""), width="stretch", height=500)
        with t5:
            st.dataframe(csv(EDA_OUT / "01_missing.csv", index_col=0).style.format("{:.1%}"),
                         width="stretch", height=500)

# ------------------------------------------------------------------ 3. Inferensi kausal
elif halaman == "Inferensi Kausal":
    kiri, kanan = st.columns([3, 1])
    kiri.header("3. Inferensi Kausal")
    with kanan:
        panel_laporan("kausal")
    st.write("DAG → adjustment set (kriteria backdoor) → g-komputasi, IPW, AIPW + bootstrap PSU + E-value.")
    nama = st.selectbox("Analisis", list(C.ANALISIS),
                        format_func=lambda n: f"{n}  ({C.ANALISIS[n]['T']} → {C.ANALISIS[n]['Y']})")
    spec = C.ANALISIS[nama]
    c = st.columns([1, 1, 2])
    boot = c[0].number_input("Jumlah bootstrap", 10, 5000, C.BOOT, step=50,
                             help="200 untuk eksplorasi, 1000 untuk hasil final disertasi")
    semua = c[1].checkbox("Semua analisis", help="Jalankan keempat analisis sekaligus")
    b1, b2 = st.columns(2)
    cek = b1.button("🔎 Cek DAG & identifikasi (cepat)", width="stretch")
    est = b2.button("▶️ Jalankan estimasi", type="primary", width="stretch")
    target = None if semua else nama

    if cek:
        proses("Cek DAG", lambda: causal.cek_dag(target))
    if est:
        C.BOOT = int(boot)
        bar = st.progress(0.0, text="Menyiapkan...")
        def prog(n, i, b):
            bar.progress(i / b, text=f"{n}: bootstrap {i}/{b}")
        proses(f"Estimasi kausal ({'semua' if semua else nama}, bootstrap={C.BOOT})",
               lambda: causal.run(prep.load(), target, progress=prog))
        bar.empty()

    # ---- hasil analisis terpilih
    out = C.OUT / "kausal" / nama
    st.subheader(f"Hasil: {nama}")
    with st.expander("Spesifikasi DAG (dari config.py)"):
        st.markdown(f"**Treatment:** `{spec['T']}` | **Outcome:** `{spec['Y']}` | "
                    f"**Filter:** `{spec['filter'] or '-'}` | **Laten:** `{', '.join(spec['laten']) or '-'}`")
        st.code("\n".join(e.format(T=spec['T'], Y=spec['Y']) for e in spec['edges']), language=None)

    if not (out / "dag.png").exists():
        st.info("Belum ada hasil. Klik **Cek DAG** atau **Jalankan estimasi**.")
    else:
        tampil_narasi(f"3. Inferensi Kausal — {nama}", narasi.kausal(nama), f"narasi_3_{nama}.md")
        t1, t2, t3, t4 = st.tabs(["DAG & identifikasi", "Estimasi", "Keseimbangan", "Overlap"])
        with t1:
            if (out / "adjustment.txt").exists():
                txt = (out / "adjustment.txt").read_text(encoding="utf-8")
                (st.success if "backdoor): True" in txt else st.warning)(
                    "Efek teridentifikasi (kriteria backdoor terpenuhi)" if "backdoor): True" in txt
                    else "Efek TIDAK teridentifikasi: ada confounder laten. Laporkan E-value.")
                st.code(txt, language=None)
            else:
                Z, ok, med = causal.adjustment(causal.build_dag(spec), spec['T'], spec['Y'], spec['laten'])
                (st.success if ok else st.warning)(f"Teridentifikasi: {'YA' if ok else 'TIDAK (ada laten)'}")
                st.code(f"Dikontrol ({len(Z)}): {', '.join(Z)}\nMediator: {', '.join(med) or '-'}", language=None)
            st.image(str(out / "dag.png"))
        tab = csv(out / "estimasi.csv", index_col=0)
        if tab is None:
            for t in (t2, t3, t4):
                t.info("Estimasi belum dijalankan untuk analisis ini.")
        else:
            with t2:
                r = tab.loc
                c = st.columns(3)
                c[0].metric("AIPW Risk Difference", f"{r['aipw_RD', 'estimasi']:+.4f}",
                            help=f"CI 95%: [{r['aipw_RD', 'ci_bawah']:+.4f}, {r['aipw_RD', 'ci_atas']:+.4f}]")
                c[1].metric("AIPW Risk Ratio", f"{r['aipw_RR', 'estimasi']:.2f}",
                            help=f"CI 95%: [{r['aipw_RR', 'ci_bawah']:.2f}, {r['aipw_RR', 'ci_atas']:.2f}]")
                c[2].metric("E-value (titik)", f"{causal.evalue(r['aipw_RR', 'estimasi']):.2f}")
                st.caption(f"CI 95% RD: [{r['aipw_RD', 'ci_bawah']:+.4f}, {r['aipw_RD', 'ci_atas']:+.4f}] · "
                           f"CI 95% RR: [{r['aipw_RR', 'ci_bawah']:.2f}, {r['aipw_RR', 'ci_atas']:.2f}] · "
                           "AIPW = estimator utama; g-komputasi & IPW = pembanding.")
                st.dataframe(tab.style.format("{:.4f}"), width="stretch")
            with t3:
                bal = csv(out / "keseimbangan.csv", index_col=0)
                mx = bal.smd_ipw.abs().max()
                (st.success if mx < 0.1 else st.warning)(f"|SMD| maksimum setelah IPW = {mx:.3f} (target < 0,1)")
                st.dataframe(bal.style.format("{:+.3f}").map(
                    lambda v: "background-color: #f8d7da" if abs(v) > 0.1 else ""), width="stretch")
                st.bar_chart(bal.abs(), horizontal=True, stack=False, height=450)
            with t4:
                st.image(str(out / "overlap.png"), caption="Sebaran propensity score per kelompok treatment")

# ------------------------------------------------------------------ 4. Baseline
elif halaman == "Baseline (B1–B3)":
    P = C.BASELINE
    kiri, kanan = st.columns([3, 1])
    kiri.header("4. Baseline Kausal Grafis (pembanding SOL-DAG)")
    with kanan:
        panel_laporan("baseline")
    st.write("**B1** DAG pakar + SEM · **B2** PC-stable + tier + IDA · **B3** Bayesian Network berbasis skor + "
             "inferensi do. Ketiganya memakai variabel, data (kasus lengkap), tier, dan langkah estimasi yang sama: "
             "adjustment set backdoor → g-komputasi berbobot survei → bootstrap PSU. Penemuan graf B2/B3 "
             "tidak memakai desain survei (sesuai rumusan baseline).")
    nama = st.selectbox("Analisis", list(C.ANALISIS), key="base_nama",
                        format_func=lambda n: f"{n}  ({C.ANALISIS[n]['T']} → {C.ANALISIS[n]['Y']})")
    spec = C.ANALISIS[nama]
    c = st.columns([2, 1, 1])
    metode = c[0].multiselect("Metode", ["B1", "B2", "B3"], default=["B1", "B2", "B3"])
    boot = c[1].number_input("Bootstrap PSU", 0, 2000, P['boot'], step=50, help="0 = tanpa CI; 100 cukup untuk eksplorasi")
    semua = c[2].checkbox("Semua analisis", key="base_semua")
    with st.expander("Pengaturan metode"):
        k = st.columns(3)
        k[0].markdown("**B1 SEM**")
        deff = k[0].number_input("Design effect (n efektif χ²/RMSEA)", 1.0, 10.0, P['deff'], 0.01)
        exo = k[0].checkbox("Kovarians variabel eksogen bebas", P['sem_exo_bebas'])
        k[1].markdown("**B2 PC + tier + IDA**")
        alpha = k[1].select_slider("α uji independensi", [0.001, 0.005, 0.01, 0.05, 0.1], P['alpha'])
        maks_k = k[1].number_input("Ukuran maks. himpunan kondisi", 0, 8, P['maks_kondisi'])
        uji = k[1].radio("Uji", ["campuran", "fisher"], ["campuran", "fisher"].index(P['uji']), horizontal=True,
                         help="campuran = G² jika semua variabel uji diskret, selain itu Fisher z")
        k[2].markdown("**B3 BN skor**")
        skor = k[2].radio("Skor", ["bic", "bdeu", "gauss"], ["bic", "bdeu", "gauss"].index(P['skor']), horizontal=True)
        awal = k[2].radio("Graf awal", ["kosong", "pakar"], ["kosong", "pakar"].index(P['awal']), horizontal=True)
        maks_i = k[2].number_input("Induk maks. per node", 1, 10, P['maks_induk'])
        nbin = k[2].number_input("Kuantil untuk variabel kontinu", 2, 10, P['bin'], disabled=skor == "gauss")
    if st.button("▶️ Jalankan baseline", type="primary", disabled=not metode):
        P.update(boot=int(boot), deff=deff, sem_exo_bebas=exo, alpha=alpha, maks_kondisi=int(maks_k), uji=uji,
                 skor=skor, awal=awal, maks_induk=int(maks_i), bin=int(nbin))
        teks = st.empty()
        proses(f"Baseline {'+'.join(metode)} ({'semua' if semua else nama}, bootstrap={P['boot']})",
               lambda: baseline.run(prep.load(), None if semua else nama, metode,
                                    progress=lambda t: teks.caption(f"⏳ {t}")))
        teks.empty()

    out = C.OUT / "baseline" / nama
    st.subheader(f"Hasil: {nama}")
    tab = csv(out / "perbandingan.csv")
    kv = lambda f: csv(out / f, index_col=0)
    if tab is None:
        st.info("Belum ada hasil baseline untuk analisis ini. Klik **Jalankan baseline**.")
    else:
        tampil_narasi(f"4. Baseline — {nama}", narasi.baseline(nama), f"narasi_4_{nama}.md")
        tr, t0, t1, t2, t3, t4 = st.tabs(["🏆 Rangkuman", "Perbandingan", "B1 SEM", "B2 PC + IDA", "B3 BN skor",
                                          "Tier & asumsi"])
        with tr:
            rk = csv(out / "rangkuman.csv")
            if rk is None:
                st.info("Rangkuman belum dibuat.")
                if st.button("🧮 Hitung rangkuman dari hasil yang ada"):
                    proses("Rangkuman baseline", lambda: baseline.rangkum_ulang(prep.load()))
                    st.rerun()
            else:
                b = rk[rk.terbaik].iloc[0]
                nk = {"BIC_SEM": "BIC-SEM", "CFI": "CFI", "lebar_CI": "lebar CI"}
                unggul = [nk[k] for k in baseline.KRITERIA if b[f"rank_{k}"] == 1]
                st.success(f"**Metode terbaik untuk {nama}: {b.metode}** · peringkat rata-rata "
                           f"{b.peringkat_rata2:.2f} · unggul pada {', '.join(unggul) or '-'} · "
                           f"RD = {b.RD:+.4f} [{b.RD_lo:+.4f}, {b.RD_hi:+.4f}]")
                if b.lebar_CI != b.lebar_CI:   # NaN
                    st.warning("Metode terbaik tidak punya CI yang bermakna (efek 0 karena graf tanpa jalur T→Y "
                               "atau bootstrap = 0); perhatikan kolom catatan.")
                kol = ["metode", "sisi", "BIC_SEM", "CFI", "RMSEA", "SRMR", "RD", "lebar_CI",
                       "rank_BIC_SEM", "rank_CFI", "rank_lebar_CI", "peringkat_rata2", "catatan"]
                st.dataframe(rk.set_index("kode")[kol].style.format(
                    {"BIC_SEM": "{:.1f}", "CFI": "{:.3f}", "RMSEA": "{:.3f}", "SRMR": "{:.3f}", "RD": "{:+.4f}",
                     "lebar_CI": "{:.4f}", "rank_BIC_SEM": "{:.0f}", "rank_CFI": "{:.0f}",
                     "rank_lebar_CI": "{:.0f}", "peringkat_rata2": "{:.2f}"}, na_rep="-").apply(
                    lambda r: ["background-color: #d4edda" if rk.set_index("kode").terbaik[r.name] else ""] * len(r),
                    axis=1), width="stretch")
                st.markdown(
                    "**Cara menilai** (tanpa ground truth, *terbaik* = paling sesuai data dan paling presisi, "
                    "bukan jaminan paling benar secara kausal):\n"
                    "1. **BIC-SEM** (↓): graf tiap metode dinilai dengan SEM linear berbobot survei yang sama "
                    "(n efektif = n/deff); menyeimbangkan kecocokan dan jumlah sisi. CPDAG B2 diperluas menjadi DAG.\n"
                    "2. **CFI** (↑) pada SEM yang sama.\n"
                    "3. **Lebar CI 95% RD** (↓) dari bootstrap PSU: presisi estimasi efek.\n\n"
                    "Peringkat tiap kriteria dirata-rata; terkecil = terbaik. Catatan: B2 memakai uji Fisher z "
                    "(linear-Gaussian) sehingga sedikit diuntungkan oleh penilaian SEM linear; B3 dioptimalkan "
                    "pada skor diskret, bukan SEM.")
            # ringkasan lintas analisis
            semua_rk = {n: csv(C.OUT / "baseline" / n / "rangkuman.csv") for n in C.ANALISIS}
            semua_rk = {n: r for n, r in semua_rk.items() if r is not None}
            if len(semua_rk) > 1:
                st.markdown("**Metode terbaik per analisis**")
                lintas = pd.DataFrame([dict(analisis=n, terbaik=r[r.terbaik].metode.iloc[0],
                                            **{f"peringkat {k}": v for k, v in
                                               r.set_index("kode").peringkat_rata2.items()})
                                       for n, r in semua_rk.items()])
                st.dataframe(lintas.style.format(precision=2, na_rep="-"), width="stretch", hide_index=True)
                juara = lintas.terbaik.value_counts()
                st.info(f"Secara keseluruhan: **{juara.index[0]}** terbaik pada {juara.iloc[0]} dari "
                        f"{len(lintas)} analisis.")
        with t0:
            st.dataframe(tab.drop(columns="kode").style.format(
                {"RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}", "RR": "{:.2f}", "RR_lo": "{:.2f}",
                 "RR_hi": "{:.2f}", "detik": "{:.1f}"}, na_rep="-"), width="stretch", hide_index=True)
            ref = csv(C.OUT / "kausal" / nama / "estimasi.csv", index_col=0)
            if ref is not None:
                st.caption(f"Rujukan menu 3 (DAG pakar, AIPW): RD = {ref.loc['aipw_RD', 'estimasi']:+.4f} "
                           f"[{ref.loc['aipw_RD', 'ci_bawah']:+.4f}, {ref.loc['aipw_RD', 'ci_atas']:+.4f}]")
            st.caption("SHD = selisih struktur terhadap DAG pakar (sisi tambahan + hilang + arah beda). "
                       "DAG pakar bukan kebenaran, hanya rujukan.")
            if (out / "perbandingan.png").exists():
                st.image(str(out / "perbandingan.png"))
        with t1:
            fit = kv("b1_kecocokan.csv")
            if fit is None:
                st.info("B1 belum dijalankan.")
            else:
                f = fit.nilai
                m = st.columns(4)
                m[0].metric("RMSEA", f"{f['RMSEA']:.3f}", help="baik < 0,06")
                m[1].metric("CFI", f"{f['CFI']:.3f}", help="baik > 0,95")
                m[2].metric("SRMR", f"{f['SRMR']:.3f}", help="baik < 0,08")
                m[3].metric("χ² (df)", f"{f['chi2']:.0f} ({f['df']:.0f})", help=f"n efektif = {f['n_eff']:.0f}")
                st.markdown("**Dekomposisi efek T → Y** (baris linear = skala koefisien/LPM; baris probit = "
                            "g-komputasi skala probabilitas)")
                st.dataframe(csv(out / "b1_dekomposisi.csv").style.format(precision=4, na_rep="-"),
                             width="stretch", hide_index=True)
                st.markdown("**Koefisien jalur**")
                st.dataframe(csv(out / "b1_koefisien.csv").style.format(precision=4, na_rep="-"),
                             width="stretch", hide_index=True, height=350)
                st.dataframe(kv("b1_info.csv"), width="stretch")
                st.image(str(out / "b1_graf.png"))
        with t2:
            inf = kv("b2_info.csv")
            if inf is None:
                st.info("B2 belum dijalankan.")
            else:
                i = inf.nilai
                m = st.columns(4)
                m[0].metric("Jumlah uji CI", i['jumlah_uji'])
                m[1].metric("Sisi berarah", i['sisi_berarah'])
                m[2].metric("Sisi tak berarah", i['sisi_tak_berarah'])
                m[3].metric("SHD vs pakar", i['SHD'])
                st.markdown("**IDA**: efek untuk setiap himpunan induk T yang konsisten dengan CPDAG")
                st.dataframe(csv(out / "b2_ida.csv").style.format(precision=4, na_rep="-"),
                             width="stretch", hide_index=True)
                st.image(str(out / "b2_graf.png"))
                a, b = st.columns(2)
                a.dataframe(csv(out / "b2_cpdag.csv"), width="stretch", hide_index=True, height=350)
                b.dataframe(inf, width="stretch", height=350)
        with t3:
            inf = kv("b3_info.csv")
            if inf is None:
                st.info("B3 belum dijalankan.")
            else:
                i = inf.nilai
                m = st.columns(4)
                m[0].metric("Skor akhir", f"{float(i['skor_akhir']):,.1f}")
                m[1].metric("Skor DAG pakar", f"{float(i['skor_DAG_pakar']):,.1f}")
                m[2].metric("Langkah Hill-Climbing", i['langkah'])
                m[3].metric("SHD vs pakar", i['SHD'])
                if i['catatan'] != '-':
                    st.warning(i['catatan'])
                st.image(str(out / "b3_graf.png"))
                a, b = st.columns(2)
                a.line_chart(csv(out / "b3_jejak.csv").set_index("langkah").skor, height=300)
                b.dataframe(inf, width="stretch", height=300)
                st.dataframe(csv(out / "b3_jejak.csv"), width="stretch", hide_index=True, height=300)
        with t4:
            V = [v for v in causal.build_dag(spec) if v not in spec['laten']]
            st.dataframe(pd.DataFrame({"variabel": V, "tier": [C.TIER.get(v) for v in V],
                                       "nama tier": [C.TIER_NAMA[C.TIER[v]] if v in C.TIER else "BELUM ADA"
                                                     for v in V]}).sort_values("tier"),
                         width="stretch", hide_index=True)
            st.markdown("Panah *i → j* dilarang jika τ(i) > τ(j). Ubah tier di `config.TIER`.\n\n"
                        "**Asumsi bersama:** kondisi Markov kausal, faithfulness, kecukupan kausal "
                        "(variabel laten di DAG pakar diabaikan oleh B2/B3), positivitas.")

# ------------------------------------------------------------------ N1-N3. Novelty
elif halaman in NOVELTY_MENU:
    kode = NOVELTY_MENU[halaman]
    M, Pn = novelty.METODE[kode], C.NOVELTY
    pre = {"sd_hybrid": "sd", "to_dag": "to", "mlc_dag": "mlc"}[kode]
    kiri, kanan = st.columns([3, 1])
    kiri.header(f"{M['kode']}. {M['nama']} — {M['judul']}")
    with kanan:
        panel_laporan(kode)
    st.write({
        "sd_hybrid": "Mengganti uji independensi dan skor struktur yang mengasumsikan sampel iid dengan versi yang "
                     "konsisten desain survei: **Rao-Scott** (kategorik) atau **t-desain** (kontinu/campuran) untuk "
                     "skeleton, lalu **skor pseudo-likelihood berbobot** dengan penalti log n_eff untuk orientasi. "
                     "Sasaran: akurasi (mengendalikan galat tipe I yang menghasilkan sisi palsu).",
        "to_dag": "Mencari **urutan topologis di dalam setiap tier** alih-alih menjelajah ruang DAG. Untuk urutan "
                  "tetap, setiap node memilih induk terbaik dari pendahulunya (grow-shrink), sehingga DAG selalu "
                  "asiklik. Sasaran: kecepatan, konvergensi, dan memori.",
        "mlc_dag": "Memisahkan **lapis pengukuran** (indikator → konstruk dimensi kemiskinan) dari **lapis "
                   "struktural** (DAG antar-konstruk dan variabel teramati kunci). Struktur dipelajari dari kovarians "
                   "konstruk yang dikoreksi galat ukur. Sasaran: graf lebih kecil, cepat, dan hemat memori.",
    }[kode])
    st.caption("⚠️ Kandidat kebaruan adalah hipotesis desain yang belum teruji. Perbandingan pada data nyata tanpa "
               "ground truth bukan bukti keunggulan; klaim harus dibuktikan pada evaluasi semi-sintetik.")
    if kode == "sd_hybrid":
        st.warning("**Klaim dicabut (benchmark v3, H8c):** uji t-desain setara uji Wald dengan SE sandwich terklaster "
                   "CR1 (keputusan identik pada 99,9% pernyataan H0), jadi bukan uji baru. Yang terbukti: koreksi Kish "
                   "dan deff-global salah kalibrasi (H8b). Lihat CATATAN_DEVIASI.md.")
    elif kode in ("to_dag", "mlc_dag"):
        st.warning("**Klaim dicabut (benchmark v1, H2/H3):** SOL-DAG dan komponennya tidak terbukti lebih cepat atau "
                   "lebih hemat secara umum; keunggulan waktu/memori hanya tampak terhadap metode pada indikator mentah. "
                   "Lihat CATATAN_DEVIASI.md.")
    nama = st.selectbox("Analisis", list(C.ANALISIS), key=f"{kode}_nama",
                        format_func=lambda n: f"{n}  ({C.ANALISIS[n]['T']} → {C.ANALISIS[n]['Y']})")
    c = st.columns([1, 1, 2])
    boot = c[0].number_input("Bootstrap PSU", 0, 2000, Pn['boot'], step=50, key=f"{kode}_boot",
                             help="0 = tanpa CI; 100 cukup untuk eksplorasi")
    semua = c[1].checkbox("Semua analisis", key=f"{kode}_semua")
    sim = False
    with st.expander("Pengaturan metode"):
        k = st.columns(3)
        if kode == "sd_hybrid":
            sd_uji = k[0].radio("Uji", ["desain", "t"], ["desain", "t"].index(Pn['sd_uji']), horizontal=True,
                                help="desain = Rao-Scott bila semua variabel uji diskret, selain itu t-desain")
            sd_alpha = k[0].select_slider("α", [0.001, 0.005, 0.01, 0.05, 0.1], Pn['sd_alpha'])
            sd_mk = k[1].number_input("Ukuran maks. himpunan kondisi", 0, 8, Pn['sd_maks_kondisi'])
            sd_skor = k[1].radio("Skor s_w", ["bic", "gauss"], ["bic", "gauss"].index(Pn['sd_skor']), horizontal=True)
            sd_mi = k[1].number_input("Induk maks. per node", 1, 10, Pn['sd_maks_induk'], key="sd_mi")
            sd_orde = k[0].radio("Koreksi Rao-Scott", [1, 2], [1, 2].index(Pn['sd_rs_orde']), horizontal=True,
                                 format_func=lambda x: f"orde {x}",
                                 help="orde 2 juga menyesuaikan derajat bebas dengan variasi eigenvalue design effect")
            sd_skala = k[1].radio("Skala likelihood skor", ["n_eff", "n"], ["n_eff", "n"].index(Pn['sd_skala']),
                                  horizontal=True, help="n_eff = fit dan penalti pada skala sampel efektif yang sama")
            sim = k[2].checkbox("Jalankan simulasi galat tipe I dan daya uji", True)
            sim_rep = k[2].number_input("Replikasi simulasi", 20, 2000, Pn['sim_rep'], step=20)
            sim_icc = k[2].slider("ICC variabel simulasi", 0.05, 0.8, Pn['sim_icc'], 0.05)
            ubah = dict(sd_uji=sd_uji, sd_alpha=sd_alpha, sd_maks_kondisi=int(sd_mk), sd_skor=sd_skor,
                        sd_maks_induk=int(sd_mi), sim_rep=int(sim_rep), sim_icc=sim_icc, sd_rs_orde=int(sd_orde),
                        sd_skala=sd_skala)
        elif kode == "to_dag":
            to_skor = k[0].radio("Skor", ["bic", "bdeu", "gauss"], ["bic", "bdeu", "gauss"].index(Pn['to_skor']),
                                 horizontal=True)
            to_bb = k[0].checkbox("Skor berbobot survei (penalti log n_eff)", Pn['to_berbobot'])
            to_mi = k[1].number_input("Induk maks. per node (m)", 1, 10, Pn['to_maks_induk'], key="to_mi")
            to_ek = k[2].number_input("Tier ≤ sekian variabel dicari eksak", 1, 14, Pn['to_eksak_maks'],
                                      help="tier lebih besar memakai pencarian pindah-posisi")
            ubah = dict(to_skor=to_skor, to_berbobot=to_bb, to_maks_induk=int(to_mi), to_eksak_maks=int(to_ek))
        else:
            ml_pen = k[0].radio("Penemuan struktur pada Σ̂_V", ["todag", "pc"],
                                ["todag", "pc"].index(Pn['mlc_penemuan']), horizontal=True)
            ml_alpha = k[0].select_slider("α (bila PC)", [0.001, 0.005, 0.01, 0.05, 0.1], Pn['mlc_alpha'])
            ml_mu = k[1].slider("Muatan minimum", 0.1, 0.6, Pn['mlc_muatan_min'], 0.05)
            ml_te = k[2].slider("Rerata |tetrad| maks. (dalam konstruk)", 0.01, 0.2, Pn['mlc_tetrad_maks'], 0.01)
            ml_li = k[2].slider("Rerata |tetrad| maks. (lintas konstruk)", 0.01, 0.2, Pn['mlc_lintas_maks'], 0.01)
            ubah = dict(mlc_penemuan=ml_pen, mlc_alpha=ml_alpha, mlc_muatan_min=ml_mu, mlc_tetrad_maks=ml_te,
                        mlc_lintas_maks=ml_li)
            st.caption("Konstruk dan indikatornya diatur di `config.MLC_KONSTRUK`.")
    if st.button(f"▶️ Jalankan {M['nama']}", type="primary"):
        Pn.update(boot=int(boot), **ubah)
        teks = st.empty()
        proses(f"{M['nama']} ({'semua' if semua else nama}, bootstrap={Pn['boot']})",
               lambda: novelty.run(prep.load(), kode, None if semua else nama,
                                   progress=lambda t: teks.caption(f"⏳ {t}"), simulasi=sim))
        teks.empty()

    out = C.OUT / "novelty" / kode / nama
    st.subheader(f"Hasil: {nama}")
    inf = csv(out / f"{pre}_info.csv", index_col=0)
    if inf is None:
        st.info(f"Belum ada hasil {M['nama']} untuk analisis ini. Klik **Jalankan {M['nama']}**.")
    else:
        i = inf.nilai
        tampil_narasi(f"{M['kode']} {M['nama']} — {nama}", narasi.novelty(kode, nama), f"narasi_{kode}_{nama}.md")
        khusus = {"sd_hybrid": "🎯 Uji galat tipe I & design effect", "to_dag": "🔁 Ruang pencarian & konvergensi",
                  "mlc_dag": "📐 Model pengukuran"}[kode]
        th, tb, tk = st.tabs([f"Hasil {M['nama']}", "⚖️ Perbandingan dengan baseline", khusus])
        with th:
            m = st.columns(4)
            m[0].metric("Sisi graf", i['sisi'])
            m[1].metric("Waktu penemuan", f"{float(i['detik_penemuan']):.2f} dtk")
            m[2].metric("Memori puncak", f"{float(i['memori_MB']):.1f} MB")
            if kode == "mlc_dag":
                m[3].metric("Node struktural", f"{i['node_tanpa_konstruk']} → {i['node_struktural']}")
            else:
                m[3].metric("SHD vs pakar", i['SHD'])
            if i['catatan'] != '-':
                st.warning(i['catatan'])
            st.image(str(out / f"{pre}_graf.png"))
            a, b = st.columns(2)
            a.dataframe(csv(out / f"{pre}_dag.csv"), width="stretch", hide_index=True, height=350)
            b.dataframe(inf, width="stretch", height=350)
        with tb:
            bd = csv(out / "banding.csv")
            if bd is None or not bd.kode.isin(["B1", "B2", "B3"]).any():
                st.warning("Hasil baseline belum ada untuk analisis ini. Jalankan menu **Baseline (B1–B3)** dulu, "
                           f"lalu jalankan ulang {M['nama']}.")
            if bd is not None:
                t = bd[bd.terbaik].iloc[0]
                kr = list(M['kriteria'])
                st.success(f"**Terbaik menurut {', '.join(narasi.NK.get(x, x) for x in kr)}: {t.metode}** · "
                           f"peringkat rata-rata {t.peringkat_rata2:.2f}")
                kol = [x for x in ["metode", "sisi", "node", "SHD", "detik_penemuan", "memori_MB", "BIC_SEM", "CFI",
                                   "RD", "RD_lo", "RD_hi", "lebar_CI"] if x in bd]
                kol += [f"rank_{x}" for x in kr] + ["peringkat_rata2"]
                fm = {"detik_penemuan": "{:.3f}", "memori_MB": "{:.2f}", "BIC_SEM": "{:.1f}", "CFI": "{:.3f}",
                      "RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}", "lebar_CI": "{:.4f}",
                      "peringkat_rata2": "{:.2f}", "sisi": "{:.0f}", "node": "{:.0f}", "SHD": "{:.0f}",
                      **{f"rank_{x}": "{:.0f}" for x in kr}}

                def warna(r):
                    if bd.terbaik[r.name]:
                        return ["background-color: #d4edda"] * len(r)
                    return ["background-color: #e7f1ff" if str(bd.kode[r.name]).startswith("N") else ""] * len(r)
                st.dataframe(bd[kol].style.format({k2: v for k2, v in fm.items() if k2 in kol}, na_rep="-")
                             .apply(warna, axis=1), width="stretch", hide_index=True)
                st.caption("Hijau = terbaik, biru = kandidat kebaruan. Kriteria mengikuti sasaran kandidat di dokumen "
                           "Tahap 3. B1 tidak menemukan graf, sehingga tidak diperingkat pada waktu dan memori. "
                           "BIC-SEM dan CFI: graf dinilai dengan SEM berbobot survei yang sama; waktu dan memori hanya "
                           "tahap penemuan graf (tanpa bootstrap).")
                if (out / "banding.png").exists():
                    st.image(str(out / "banding.png"))
        with tk:
            if kode == "sd_hybrid":
                s1 = csv(out / "sd_tipe1.csv")
                if s1 is None:
                    st.info("Simulasi belum dijalankan. Centang **Jalankan simulasi galat tipe I** di pengaturan.")
                else:
                    st.markdown("**Laju galat tipe I** (proporsi menolak H0 yang benar; ideal = taraf nominal)")
                    st.dataframe(s1.style.format({"naif (B2)": "{:.1%}", "terkoreksi desain (N1)": "{:.1%}",
                                                  "nominal": "{:.0%}"}), width="stretch", hide_index=True)
                    st.bar_chart(s1.set_index("uji")[["naif (B2)", "terkoreksi desain (N1)"]], stack=False,
                                 horizontal=True, height=300)
                    st.caption("Data sintetik di bawah H0 dengan bobot, PSU, dan strata IDHS nyata; setiap variabel = "
                               "√ICC·u_PSU + √(1−ICC)·e. Design effect uji independensi ≈ 1 + (m̄−1)·ICC_x·ICC_y.")
                su = csv(out / "sd_uji.csv")
                if su is not None:
                    st.markdown("**Galat tipe I dan daya uji** (efek = korelasi laten X–Y; *naif disesuaikan ukuran* = "
                                "daya uji naif bila ambangnya dikalibrasi agar galat tipe I tepat nominal)")
                    kol_p = ["naif (B2)", "naif disesuaikan ukuran", "terkoreksi orde 1", "terkoreksi orde 2"]
                    st.dataframe(su.style.format({**{c: "{:.1%}" for c in kol_p}, "nominal": "{:.0%}", "efek": "{:.2f}"}),
                                 width="stretch", hide_index=True)
                    dy = su[su.efek > 0].assign(kasus=lambda x: x.uji + " · efek " + x.efek.astype(str))
                    st.bar_chart(dy.set_index("kasus")[kol_p[1:]], stack=False, horizontal=True, height=380)
                m = st.columns(4)
                m[0].metric("δ̄ (deff umum)", i['delta_bar'])
                m[1].metric("n_Kish", i['n_Kish'])
                m[2].metric("n_eff = n_Kish/δ̄", i['n_eff'])
                m[3].metric("Skeleton: terkoreksi vs naif", f"{i['sisi_skeleton']} vs {i['sisi_skeleton_B2_naif']}")
                st.markdown("**Design effect klaster per variabel**")
                st.bar_chart(csv(out / "sd_deff.csv", index_col=0).deff.sort_values(), horizontal=True, height=350)
            elif kode == "to_dag":
                m = st.columns(4)
                m[0].metric("Ruang DAG (Robinson)", i['ruang_DAG'])
                m[1].metric("Urutan tanpa tier", i['ruang_urutan_tanpa_tier'])
                m[2].metric("Urutan patuh tier |Π_τ|", i['ruang_urutan_tier'])
                m[3].metric("Diperiksa (terurai per tier)", i['ruang_setelah_dekomposisi'])
                st.caption(f"Ukuran tier: {i['ukuran_tier']}. Pendahulu node tier t = semua tier sebelumnya + "
                           "pendahulu di dalam tier t, sehingga F(π) terurai per tier dan tiap tier dioptimalkan terpisah.")
                m = st.columns(3)
                m[0].metric("Skor TO-DAG", f"{float(i['skor_TO_DAG']):,.1f}")
                m[1].metric("Graf B3, skor yang sama", f"{float(i['skor_B3_pada_skor_sama']):,.1f}")
                m[2].metric("DAG pakar, skor yang sama", f"{float(i['skor_pakar_pada_skor_sama']):,.1f}")
                a, b = st.columns(2)
                a.markdown("**Jejak konvergensi per tier**")
                a.dataframe(csv(out / "to_jejak.csv"), width="stretch", hide_index=True)
                b.markdown("**Urutan topologis terpilih**")
                b.dataframe(csv(out / "to_urutan.csv"), width="stretch", hide_index=True, height=400)
            else:
                if i['konstruk_bermasalah'] != '-':
                    st.warning(f"Konstruk bermasalah (muatan di bawah batas setelah purifikasi): {i['konstruk_bermasalah']}")
                if 'konstruk_reflektif' in i:
                    m = st.columns(3)
                    m[0].metric("Reflektif (ω ≥ " + str(i['omega_min']).replace('.', ',') + ")", i['konstruk_reflektif'])
                    m[1].metric("Komposit (formatif)", i['konstruk_komposit'])
                    m[2].metric("Dipecah jadi indikator", i['konstruk_dipecah'])
                st.markdown(f"**Reliabilitas (omega) / jenis:** {i['reliabilitas_omega']}")
                a, b = st.columns(2)
                a.markdown("**Muatan faktor (setelah purifikasi)**")
                a.dataframe(csv(out / "mlc_muatan.csv").style.format(precision=3).background_gradient(
                    subset=["muatan"], cmap="RdYlGn", vmin=-1, vmax=1), width="stretch", hide_index=True, height=450)
                b.markdown("**Log purifikasi (indikator dibuang)**")
                pl = csv(out / "mlc_purifikasi.csv")
                if pl is not None and len(pl):
                    b.dataframe(pl.style.format(precision=3), width="stretch", hide_index=True)
                else:
                    b.caption("Tidak ada indikator yang dibuang.")
                b.markdown("**Rincian waktu (detik)**")
                b.dataframe(pd.Series({x: i[x] for x in ["detik_korelasi", "detik_model_ukur", "detik_struktur",
                                                         "detik_struktur_tanpa_konstruk"]}, name="detik"),
                            width="stretch")
                st.markdown("**Σ̂_V: korelasi konstruk (terkoreksi galat ukur) dan variabel teramati**")
                st.dataframe(csv(out / "mlc_sigma.csv", index_col=0).style.format("{:.2f}").background_gradient(
                    cmap="RdBu_r", vmin=-1, vmax=1), width="stretch")

# ------------------------------------------------------------------ SOL-DAG
elif halaman == "SOL-DAG":
    Ps = C.SOL
    kiri, kanan = st.columns([3, 1])
    kiri.header("SOL-DAG — integrasi MLC → SD-Hybrid → TO-DAG → AIPW")
    with kanan:
        panel_laporan("sol")
    st.write("**Langkah 1** MLC v2 (komposit formatif + konstruk reflektif ω ≥ 0,70) → Σ̂_V · **Langkah 2** skeleton "
             "dengan uji terkoreksi desain (Rao-Scott orde 2 / t-desain) · **Langkah 3** TO-DAG dengan skor Gauss "
             "berskala n_eff, induk dibatasi skeleton · **Langkah 4** pemisahan sampel per PSU di dalam strata: graf "
             "ditemukan di separuh A, AIPW berbobot survei di separuh B. Empat ablasi mematikan satu komponen.")
    st.caption("⚠️ Hasil pada data nyata tidak memiliki ground truth; uji hipotesis H1–H5 ada di menu Benchmark (H1–H5).")
    st.warning("**Klaim dicabut:** SOL-DAG tidak terbukti lebih cepat/hemat (v1 H2 3/8, H3 6/8) dan uji desainnya bukan "
               "uji baru (v3 H8c). SOL v1 menolkan efek (v1 H1); gunakan SOL v2. Lihat CATATAN_DEVIASI.md.")
    nama = st.selectbox("Analisis", list(C.ANALISIS), key="sol_nama",
                        format_func=lambda n: f"{n}  ({C.ANALISIS[n]['T']} → {C.ANALISIS[n]['Y']})")
    c = st.columns([1, 1, 2])
    boot = c[0].number_input("Bootstrap PSU (separuh B)", 0, 2000, Ps['boot'], step=50, key="sol_boot")
    semua = c[1].checkbox("Semua analisis", key="sol_semua")
    var = c[2].multiselect("Varian", list(sol_dag.VARIAN), list(sol_dag.VARIAN), key="sol_var")
    with st.expander("Pengaturan"):
        k = st.columns(3)
        s_alpha = k[0].select_slider("α uji", [0.001, 0.005, 0.01, 0.05, 0.1], Ps['alpha'], key="sol_alpha")
        s_mk = k[0].number_input("Ukuran maks. himpunan kondisi", 0, 8, Ps['maks_kondisi'], key="sol_mk")
        s_orde = k[1].radio("Rao-Scott", [1, 2], [1, 2].index(Ps['rs_orde']), horizontal=True,
                            format_func=lambda x: f"orde {x}", key="sol_orde")
        s_mi = k[1].number_input("Induk maks. per node", 1, 10, Ps['maks_induk'], key="sol_mi")
        s_ek = k[2].number_input("Tier ≤ sekian variabel dicari eksak", 1, 14, Ps['eksak_maks'], key="sol_ek")
    if st.button("▶️ Jalankan SOL-DAG", type="primary", disabled=not var):
        Ps.update(boot=int(boot), alpha=s_alpha, maks_kondisi=int(s_mk), rs_orde=int(s_orde), maks_induk=int(s_mi),
                  eksak_maks=int(s_ek))
        teks = st.empty()
        proses(f"SOL-DAG ({'semua' if semua else nama}, bootstrap={Ps['boot']})",
               lambda: sol_dag.run(prep.load(), None if semua else nama, [v for v in sol_dag.VARIAN if v in var],
                                   progress=lambda t: teks.caption(f"⏳ {t}")))
        teks.empty()
    if st.button("▶️ Jalankan SOL v2 (pra-registrasi)",
                 help="Graf hanya memilih himpunan penyesuaian; efek selalu diestimasi dengan AIPW cross-fitting"):
        teks = st.empty()
        proses(f"SOL v2 ({'semua' if semua else nama})",
               lambda: sol_dag.run_v2(prep.load(), None if semua else nama, progress=lambda t: teks.caption(f"⏳ {t}")))
        teks.empty()
    out = C.OUT / "sol_dag" / nama
    st.subheader(f"Hasil: {nama}")
    v2 = csv(out / "sol_v2.csv")
    if v2 is not None:
        with st.container(border=True):
            st.markdown("**SOL v2 (pra-registrasi)** — PC-stable + tier dengan uji-t desain (α = "
                        f"{str(C.SOL_V2['alpha']).replace('.', ',')}); graf hanya memilih himpunan penyesuaian (induk T, "
                        f"ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU (K = {C.SOL_V2['K']}), SE fungsi "
                        "pengaruh + linearisasi desain.")
            st.dataframe(v2.style.format({"RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}", "RD_min": "{:+.4f}",
                                          "RD_max": "{:+.4f}", "detik": "{:.1f}", "memori_MB": "{:.1f}"}),
                         width="stretch", hide_index=True)
            pemb = []
            est = csv(C.OUT / "kausal" / nama / "estimasi.csv", index_col=0)
            if est is not None:
                pemb.append(f"AIPW menu 3 (DAG pakar) RD {est.loc['aipw_RD', 'estimasi']:+.4f} "
                            f"[{est.loc['aipw_RD', 'ci_bawah']:+.4f}; {est.loc['aipw_RD', 'ci_atas']:+.4f}]")
            v1 = csv(out / "sol_varian.csv")
            if v1 is not None and (v1.varian == "SOL-DAG").any():
                pemb.append(f"SOL v1 RD {v1[v1.varian == 'SOL-DAG'].RD.iloc[0]:+.4f}")
            if pemb:
                st.caption("Pembanding: " + " · ".join(pemb))
            if (out / "sol_v2_graf.png").exists():
                with st.expander("Graf SOL v2 (desain)"):
                    st.image(str(out / "sol_v2_graf.png"))
    vr = csv(out / "sol_varian.csv")
    if vr is None:
        st.info("Belum ada hasil SOL-DAG untuk analisis ini. Klik **Jalankan SOL-DAG**.")
    else:
        tampil_narasi(f"SOL-DAG — {nama}", narasi.sol(nama), f"narasi_sol_{nama}.md")
        t1, t2, t3 = st.tabs(["Varian & ablasi", "⚖️ Perbandingan dengan baseline & kandidat", "Graf SOL-DAG"])
        with t1:
            s0 = vr[vr.varian == "SOL-DAG"]
            if len(s0):
                s0 = s0.iloc[0]
                m = st.columns(4)
                m[0].metric("Node struktural", int(s0.node))
                m[1].metric("Sisi (skeleton)", f"{int(s0.sisi)} ({int(s0.sisi_skeleton)})")
                m[2].metric("n_eff", f"{s0.n_eff:,.0f}".replace(",", "."))
                m[3].metric("RD AIPW (separuh B)", f"{s0.RD:+.4f}", help=f"CI 95%: [{s0.RD_lo:+.4f}, {s0.RD_hi:+.4f}]")
                if s0.catatan != "-":
                    st.warning(s0.catatan)
            kol = ["varian", "node", "sisi", "sisi_skeleton", "jumlah_uji", "n_eff", "n_A", "n_B", "RD", "RD_lo", "RD_hi",
                   "detik_penemuan", "memori_MB", "adjustment", "catatan"]
            st.dataframe(vr[kol].style.format({"n_eff": "{:,.0f}", "RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}",
                                               "detik_penemuan": "{:.2f}", "memori_MB": "{:.2f}"}, na_rep="-"),
                         width="stretch", hide_index=True)
            st.caption("Ablasi mematikan satu komponen: tanpa MLC (variabel DAG apa adanya), tanpa koreksi desain "
                       "(uji naif + skor iid), tanpa tier (satu urutan bebas), tanpa pemisahan sampel (penemuan dan "
                       "estimasi pada data yang sama).")
        with t2:
            bd = csv(out / "sol_banding.csv")
            if bd is not None:
                st.dataframe(bd.style.format({"RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}", "sisi": "{:.0f}",
                                              "node": "{:.0f}", "detik_penemuan": "{:.3f}", "memori_MB": "{:.2f}"},
                                             na_rep="-"), width="stretch", hide_index=True)
                st.image(str(out / "sol_banding.png"))
        with t3:
            if (out / "sol_graf.png").exists():
                st.image(str(out / "sol_graf.png"))
                st.dataframe(csv(out / "sol_dag.csv"), width="stretch", hide_index=True, height=350)

# ------------------------------------------------------------------ Benchmark v4 (penampil; dijalankan lewat bench_v4.py)
elif halaman == MENU_V4:
    import json

    kiri, kanan = st.columns([3, 1])
    kiri.header("Benchmark v4 — pemilihan confounder M0–M6 (H10–H13)")
    with kanan:
        panel_laporan("benchmark_v4")
    st.write("Simulasi utama naskah: graf acak patuh tier dengan efek benar yang diketahui, desain sintetis setara IDHS "
             "(67 strata × 29 PSU × 9 unit), dan satu estimator untuk semua metode (AIPW cross-fitting per PSU, SE "
             "linearisasi desain). **M0** semua kovariat pra-treatment · **M1** induk T di DAG pakar yang 30% keliru · "
             "**M2** PC naif · **M3** PC + uji desain · **M4** M3 dengan α longgar untuk pasangan yang melibatkan T/Y · "
             "**M5** induk T dari M3 ∪ M1 · **M6** induk T atau induk Y dari graf M3.")
    sumber = {"Hasil terbaru (hasil/benchmark_v4)": C.OUT, "Data beku naskah (naskah/data)": C.ROOT / "naskah" / "data"}
    sumber = {k: v for k, v in sumber.items() if (v / "benchmark_v4" / "per_rep.csv").exists()}
    if not sumber:
        st.info("Hasil benchmark v4 belum ada. Jalankan di terminal: `python -u bench_v4.py --rep 2` (pilot), lalu "
                "`python -u bench_v4.py` (200 replikasi × 24 sel, ±14 jam dengan 4 pekerja; bisa dilanjutkan bila terputus).")
        st.stop()
    dasar = sumber[st.radio("Sumber", list(sumber), horizontal=True, key="v4_sumber",
                            help="Data beku = salinan yang dipakai naskah (naskah_bekukan.py); tidak berubah walau "
                                 "benchmark dijalankan ulang.")]
    out = dasar / "benchmark_v4"
    d4 = narasi.data_v4(dasar)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8")) if (out / "meta.json").exists() else {}
    gagal = (out / "gagal.txt").read_text(encoding="utf-8").strip().splitlines() if (out / "gagal.txt").exists() else []
    n_sel, n_rep = d4.sel.nunique(), d4.groupby(['sel', 'rep']).ngroups
    c = st.columns(4)
    c[0].metric("Survei simulasi", f"{n_rep:,}".replace(",", ".")); c[1].metric("Sel", n_sel)
    c[2].metric("Replikasi per sel", int(n_rep / n_sel)); c[3].metric("Replikasi gagal", len(gagal))
    st.caption(f"Dijalankan {meta.get('mulai', '?')} dengan {meta.get('pekerja', '?')} pekerja. Rencana analisis dikunci "
               "sebelum simulasi penuh: RENCANA_ANALISIS_v4.md (tag git rencana-v4). Menjalankan ulang: "
               "`python -u bench_v4.py` di terminal; kolom waktu komputasi tidak dipakai naskah. Laporan Word selalu "
               "dibuat dari hasil terbaru (hasil/).")
    tampil_narasi("Benchmark v4 — pemilihan confounder M0–M6", narasi.benchmark_v4(dasar), "narasi_benchmark_v4.md")
    t1, t2, t3, t4, t5 = st.tabs(["🏁 Putusan H10–H13", "📊 Kinerja per metode", "🔍 Per faktor", "🌏 M0–M6 pada IDHS",
                                  "📄 Ringkasan per sel"])
    with t1:
        hp = csv(out / "hipotesis.csv")
        if hp is not None:
            wp = {"diterima": "#d4edda", "ditolak": "#f8d7da"}
            st.dataframe(hp.style.apply(lambda r: [f"background-color: {wp.get(r.putusan, '#fff3cd')}"] * len(r), axis=1),
                         width="stretch", hide_index=True)
            st.caption("Semua hipotesis diuji pada sel ICC heterogen. Metode terbaik = validitas tertinggi di antara M4 utama "
                       "(α_T = 0,10), M5, dan M6. H10 ditolak → skenario B: naskah dibingkai sebagai studi peringatan.")
    with t2:
        pil = st.radio("ICC", ["heterogen", "0.15", "semua sel"], horizontal=True, key="v4_icc")
        dd = d4 if pil == "semua sel" else d4[d4.icc == "heterogen"] if pil == "heterogen" else d4[d4.icc != "heterogen"]
        k4 = narasi.kinerja_v4(dd)
        st.dataframe(k4.style.format({"replikasi": "{:.0f}", "valid": "{:.1%}", "valid_lo": "{:.1%}", "valid_hi": "{:.1%}",
                                      "bias": "{:+.4f}", "RMSE": "{:.4f}", "cakupan": "{:.1%}",
                                      "n_Z": "{:.1f}", "FDR": "{:.1%}", "recall": "{:.1%}", "lebar_CI": "{:.4f}"}, na_rep="-"),
                     width="stretch", hide_index=True)
        a, b = st.columns(2)
        a.markdown("**Himpunan penyesuaian valid** (↑, target H10 = 90%)")
        a.bar_chart(k4.set_index("metode").valid, horizontal=True, height=340)
        b.markdown("**FDR skeleton** (↓; hanya metode yang menemukan graf sendiri)")
        b.bar_chart(k4.dropna(subset=["FDR"]).set_index("metode").FDR, horizontal=True, height=340)
        a.markdown("**RMSE risk difference** (↓)"); a.bar_chart(k4.set_index("metode").RMSE, horizontal=True, height=340)
        b.markdown("**Cakupan CI 95%** (target H13 = 92%)"); b.bar_chart(k4.set_index("metode").cakupan, horizontal=True, height=340)
        st.caption("valid = himpunan penyesuaian memenuhi kriteria adjustment di graf benar. M5 dan M6 memakai graf M3, "
                   "jadi tidak punya FDR sendiri.")
    with t3:
        ukur = st.radio("Ukuran", ["valid", "cakup", "RMSE"], horizontal=True, key="v4_ukur",
                        format_func={"valid": "Himpunan valid", "cakup": "Cakupan CI 95%", "RMSE": "RMSE"}.get)
        nama_f = {"kuat": "Kekuatan confounder", "p": "Jumlah node p", "beta_ty": "Efek T→Y (laten probit)", "icc": "ICC"}
        kol = st.columns(2)
        for i, (f, judul) in enumerate(nama_f.items()):
            if ukur == "RMSE":
                pv = d4.assign(g2=d4.galat ** 2).pivot_table(index="metode", columns=f, values="g2").pow(0.5)
                kol[i % 2].markdown(f"**{judul}**"); kol[i % 2].dataframe(pv.style.format("{:.4f}"), width="stretch")
            else:
                pv = d4.pivot_table(index="metode", columns=f, values=ukur)
                kol[i % 2].markdown(f"**{judul}**"); kol[i % 2].dataframe(pv.style.format("{:.1%}"), width="stretch")
        st.caption("Semua sel digabung. Kerugian koreksi desain (M3 vs M2) terkonsentrasi pada confounder lemah.")
    with t4:
        ada_idhs = False
        for an in ("sanitasi_diare", "pbi_diare"):
            rd = csv(dasar / "idhs_m0m6" / an / "rd.csv")
            if rd is None:
                continue
            ada_idhs = True
            st.markdown(f"**{an}** ({C.ANALISIS[an]['T']} → {C.ANALISIS[an]['Y']}, n = {int(rd.n.iloc[0]):,})".replace(",", "."))
            a, b = st.columns([3, 2])
            a.dataframe(rd[['metode', 'n_Z', 'RD', 'RD_lo', 'RD_hi', 'Z']].style.format(
                {"RD": "{:+.4f}", "RD_lo": "{:+.4f}", "RD_hi": "{:+.4f}"}), width="stretch", hide_index=True)
            if (dasar / "idhs_m0m6" / an / "forest.png").exists():
                b.image(str(dasar / "idhs_m0m6" / an / "forest.png"))
        if ada_idhs:
            st.caption("Efek benar tidak diketahui pada data nyata: yang dibaca adalah konsistensi RD antar-himpunan, bukan "
                       "peringkat metode. Definisi M0, M1, M6 untuk data nyata ada di kepala idhs_m0m6.py.")
        else:
            st.info("Belum ada hasil. Jalankan di terminal: `python idhs_m0m6.py`.")
    with t5:
        rk = csv(out / "ringkasan.csv")
        if rk is not None:
            st.dataframe(rk.style.format({"valid": "{:.1%}", "bias": "{:+.4f}", "RMSE": "{:.4f}", "cakupan": "{:.1%}",
                                          "lebar_CI": "{:.4f}", "n_Z": "{:.1f}", "FDR": "{:.1%}", "recall": "{:.1%}",
                                          "detik_penemuan": "{:.1f}"}, na_rep="-"), width="stretch", hide_index=True, height=520)
            st.download_button("⬇️ ringkasan.csv", (out / "ringkasan.csv").read_bytes(), "benchmark_v4_ringkasan.csv")

# ------------------------------------------------------------------ Benchmark
else:
    Pb = C.BENCH
    kiri, kanan = st.columns([3, 1])
    kiri.header("Benchmark semi-sintetik — uji H1–H5")
    with kanan:
        panel_laporan("benchmark")
    st.write("Data dibangkitkan dari SCM yang dicocokkan pada IDHS dengan **graf benar yang diketahui**, memakai ulang "
             "bobot, PSU, strata, dan ukuran klaster asli (efek acak PSU). **Skenario A**: variabel teramati; graf "
             "benar = DAG pakar diperturbasi (B1 tetap memakai DAG pakar asli). **Skenario B**: konstruk laten dan "
             "komposit dengan indikatornya. Setiap replikasi menjalankan semua metode; H1–H5 diuji dengan uji "
             "Wilcoxon berpasangan satu sisi (koreksi Holm) dan interval Wilson.")
    nama = st.selectbox("Analisis", list(C.ANALISIS), key="bm_nama",
                        format_func=lambda n: f"{n}  ({C.ANALISIS[n]['T']} → {C.ANALISIS[n]['Y']})")
    out = C.OUT / "benchmark" / nama
    c = st.columns(4)
    b_rep = c[0].number_input("Replikasi", 5, 1000, Pb['rep'], step=5, help="minimal 100 untuk hasil final")
    b_pek = c[1].number_input("Proses paralel", 1, 8, Pb['pekerja'])
    b_per = c[2].slider("Perturbasi graf pakar", 0.0, 0.6, Pb['perturbasi'], 0.05)
    b_boot = c[3].number_input("Bootstrap cakupan CI", 0, 200, Pb['boot'], step=5)

    import json, os, subprocess, sys

    def berjalan():
        """Berjalan hanya bila PID di pid.txt hidup sebagai python DAN progres belum selesai
        (nomor PID bisa dipakai ulang Windows untuk proses lain setelah benchmark berhenti)."""
        f = out / "pid.txt"
        if not f.exists():
            return False
        try:
            pg = out / "progres.json"
            if pg.exists():
                q = json.loads(pg.read_text(encoding="utf-8"))
                if q['selesai'] >= q['total']:
                    return False
            pid = int(f.read_text())
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FI", "IMAGENAME eq python.exe", "/NH"],
                               capture_output=True, text=True)
            return str(pid) in r.stdout
        except (ValueError, OSError, KeyError, json.JSONDecodeError):
            return False

    jalan = berjalan()
    ada = (out / "per_rep.csv").exists()
    timpa = st.checkbox("Timpa hasil benchmark sebelumnya (±3–4 jam untuk 100 replikasi)", key="bm_timpa") if ada else True
    if jalan:
        st.caption("⏳ Tombol nonaktif: benchmark untuk analisis ini sedang berjalan.")
    elif not timpa:
        st.caption("🔒 Tombol nonaktif karena hasil benchmark sudah ada. Centang **Timpa hasil benchmark sebelumnya** "
                   "untuk menjalankan ulang (hasil lama akan dihapus).")
    if st.button("▶️ Jalankan benchmark (latar belakang)", type="primary", disabled=jalan or not timpa,
                 help="Hasil yang ada akan dihapus dan diganti" if ada else None):
        env = {**os.environ, "BENCH_REP": str(b_rep), "BENCH_PEKERJA": str(b_pek), "BENCH_PERTURBASI": str(b_per),
               "BENCH_BOOT": str(b_boot), "PYTHONIOENCODING": "utf-8"}
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "log.txt", "w", encoding="utf-8") as lg:
            subprocess.Popen([sys.executable, str(C.ROOT / "main.py"), "benchmark", nama], cwd=C.ROOT, env=env,
                             stdout=lg, stderr=subprocess.STDOUT,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        st.success("Benchmark dimulai di latar belakang. Halaman ini memperbarui progres otomatis.")
        time.sleep(3); st.rerun()

    @st.fragment(run_every=15 if jalan else None)
    def progres():
        f = out / "progres.json"
        if f.exists():
            pg = json.loads(f.read_text(encoding="utf-8"))
            if pg['selesai'] < pg['total'] or berjalan():
                st.progress(pg['selesai'] / pg['total'],
                            text=f"⏳ {pg['selesai']}/{pg['total']} tugas · {pg['detik'] / 60:.0f} menit berjalan")
                if pg.get('galat'):
                    st.warning("Replikasi gagal: " + "; ".join(pg['galat']))
    progres()

    with st.expander("🧪 Benchmark v2 (pra-registrasi): DAG acak patuh tier, grid ICC × efek", expanded=True):
        sel_v2, hp_v2 = benchmark.evaluasi_v2()
        if hp_v2.empty:
            lg = C.ROOT / "v2" / "log_bench_v2.txt"
            st.info("Hasil benchmark v2 belum ada." + (" Sedang berjalan (`v2/run_bench.py 200`)." if lg.exists() else
                                                       " Jalankan `python run_bench.py 200 3` di folder v2."))
        else:
            wp = {"diterima": "#d4edda", "gagal": "#f8d7da"}
            st.dataframe(hp_v2.style.apply(lambda r: [f"background-color: {wp.get(r.putusan, '#fff3cd')}"] * len(r),
                                           axis=1), width="stretch", hide_index=True)
            st.dataframe(sel_v2.style.format({"SHD": "{:.2f}", "RMSE": "{:.4f}", "cakupan": "{:.1%}", "efek_nol": "{:.1%}",
                                              "detik": "{:.2f}", "MB": "{:.1f}", "t1_naif": "{:.1%}", "t1_desain": "{:.1%}",
                                              "daya_naif": "{:.1%}", "daya_desain": "{:.1%}"}, na_rep="-"),
                         width="stretch", hide_index=True)
            st.caption("Kriteria persis PRAREGISTRASI_v2.md. H3v2–H6v2 digabung antar-sel ICC 0,4 (H5v2: semua sel); n "
                       "pernyataan uji diasumsikan 20 × replikasi per sel. Hash kode: v2/HASH_KODE_v2.txt.")
    with st.expander("🧪 Benchmark v3 (pra-registrasi S6–S10): lima uji CI, ICC heterogen vs homogen", expanded=True):
        kal3, hil3, hp3 = benchmark.evaluasi_v3()
        dr = C.ROOT / "v3" / "RINGKASAN_deff_real.txt"
        if dr.exists():
            st.caption("S6 — " + dr.read_text(encoding="utf-8").splitlines()[0])
        if hp3.empty:
            st.info("Hasil v3 belum ada. Jalankan di folder v3: `python run_s8.py 200` dan `python run_downstream.py 100 15`.")
        else:
            wp = {"diterima": "#d4edda", "gagal": "#f8d7da"}
            st.dataframe(hp3.style.apply(lambda r: [f"background-color: {wp.get(r.putusan.split(' ')[0], '#fff3cd')}"]
                                                   * len(r), axis=1), width="stretch", hide_index=True)
            st.caption(benchmark.TAFSIR_V3)
            if len(kal3):
                st.markdown("**S8 — kalibrasi lima uji** (galat tipe I pada H0 yang dijamin benar; daya pada H1)")
                st.dataframe(kal3.style.format({"tipeI": "{:.1%}", "wilson_lo": "{:.1%}", "wilson_hi": "{:.1%}",
                                                "daya": "{:.1%}"}), width="stretch", hide_index=True)
            if len(hil3):
                st.markdown("**S7 + S9 — dampak hilir (p = 15)**")
                st.dataframe(hil3.style.format(precision=3), width="stretch", hide_index=True)
    pt = csv(out / "putusan.csv")
    if pt is None:
        st.info("Belum ada hasil benchmark untuk analisis ini." + (" Sedang berjalan…" if jalan else ""))
    else:
        tampil_narasi(f"Benchmark semi-sintetik — {nama}", narasi.benchmark(nama), f"narasi_benchmark_{nama}.md")
        meta = json.loads((out / "meta.json").read_text(encoding="utf-8")) if (out / "meta.json").exists() else {}
        t1, t2, t3, t4, t5 = st.tabs(["🏁 Putusan H1–H5", "📊 Metrik per metode", "🎯 H5: galat uji & cakupan CI",
                                      "🧭 Graf benar", "📄 Data per replikasi"])
        warna_p = {"didukung": "#d4edda", "didukung sebagian": "#fff3cd", "tidak didukung": "#f8d7da"}
        with t1:
            st.dataframe(pt.style.apply(lambda r: [f"background-color: {warna_p.get(r.putusan, '')}"] * len(r), axis=1),
                         width="stretch", hide_index=True)
            hp = csv(out / "hipotesis.csv")
            if hp is not None:
                st.markdown("**Rincian uji berpasangan** (SOL-DAG vs pembanding; Wilcoxon satu sisi, p Holm per hipotesis)")
                sk = st.radio("Skenario", sorted(hp.skenario.unique()), horizontal=True, key="bm_sk")
                st.dataframe(hp[hp.skenario == sk].drop(columns="skenario").style.format(
                    {"SOL": "{:.4g}", "lawan": "{:.4g}", "median_selisih": "{:+.4g}", "p": "{:.4f}", "p_holm": "{:.4f}"})
                    .apply(lambda r: ["background-color: #d4edda" if r.keputusan == "SOL lebih baik" else
                                      "background-color: #f8d7da" if r.keputusan == "SOL tidak lebih baik" else ""]
                           * len(r), axis=1), width="stretch", hide_index=True, height=420)
        with t2:
            rk = csv(out / "ringkasan.csv")
            if rk is not None:
                sk = st.radio("Skenario", sorted(rk.skenario.unique()), horizontal=True, key="bm_sk2")
                r_ = rk[rk.skenario == sk].drop(columns="skenario")
                st.dataframe(r_.style.format(precision=4, na_rep="-"), width="stretch", hide_index=True)
                a, b = st.columns(2)
                a.markdown("**SHD rata-rata** (↓)"); a.bar_chart(r_.set_index("metode").SHD, horizontal=True, height=320)
                b.markdown("**RMSE efek** (↓)"); b.bar_chart(r_.set_index("metode").RMSE, horizontal=True, height=320)
                a.markdown("**Waktu penemuan (detik)** (↓)"); a.bar_chart(r_.set_index("metode").detik, horizontal=True, height=320)
                b.markdown("**Stabilitas: SHD antar-replikasi** (↓)")
                b.bar_chart(r_.set_index("metode").stabilitas_SHD, horizontal=True, height=320)
        with t3:
            h5 = csv(out / "hipotesis_H5.csv")
            if h5 is not None:
                st.dataframe(h5.style.format({"nilai": "{:.1%}", "ci_lo": "{:.1%}", "ci_hi": "{:.1%}", "target": "{:.0%}"},
                                             na_rep="-").apply(
                    lambda r: ["background-color: #d4edda" if r.sesuai_target is True else
                               "background-color: #f8d7da" if r.sesuai_target is False and r.target == r.target else ""]
                    * len(r), axis=1), width="stretch", hide_index=True)
                st.caption("Galat tipe I dan daya uji dihitung pada pernyataan independensi/dependensi yang benar di graf "
                           "benar (skenario A). Cakupan = proporsi CI 95% bootstrap PSU yang memuat efek benar. Hijau = "
                           "interval Wilson memuat target.")
        with t4:
            for s in ("A", "B"):
                if s in meta:
                    st.markdown(f"**Skenario {s}**: " + ", ".join(f"{k} = {v:.4f}" if isinstance(v, float) else f"{k} = {v}"
                                                                   for k, v in meta[s].items()))
                    if (out / f"graf_benar_{s}.png").exists():
                        st.image(str(out / f"graf_benar_{s}.png"))
        with t5:
            pr = csv(out / "per_rep.csv")
            if pr is not None:
                st.dataframe(pr.drop(columns="tepi"), width="stretch", height=420)
                st.download_button("⬇️ per_rep.csv", (out / "per_rep.csv").read_bytes(), f"benchmark_{nama}_per_rep.csv")
