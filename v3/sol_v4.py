"""SOL v4 — S12–S14 di atas sol_v3 (sol_v3.py TIDAK diubah; hash pra-registrasi v3 tetap berlaku).
S12 himpunan penyesuaian cadangan: pa(T) ∪ (pa(Y) \\ de(T)) dari graf yang dipelajari; sah bila salah satu sumber lengkap.
S13 alokasi α sadar-query: α = 0,05 untuk seluruh graf, α_q lebih longgar untuk uji yang melibatkan T atau Y.
S14 bias akibat himpunan: selisih efek dari himpunan dipelajari vs himpunan orakel pa(T) di graf acuan (data sama);
    'material' = himpunan tidak sah DAN |selisih| > SE orakel."""
import time
import numpy as np, networkx as nx
from sol_v3 import TESTS, discover_v3, cand_sets, valid_adjust, effect_s9, edge_metrics

def query_aware(test, T, Y, alpha=.05, alpha_q=.20):
    """S13: p' = p·α/α_q untuk uji yang melibatkan T/Y, sehingga p' > α ⇔ p > α_q (discover_v3 tetap memakai α)."""
    q, s = {T, Y}, alpha / alpha_q
    return lambda D, x, y, S: test(D, x, y, S) * (s if x in q or y in q else 1.0)

def backup_set(Gh, Un, T, Y):
    """S12: induk T ∪ induk Y yang bukan keturunan T (tanpa T, Y), di graf yang dipelajari."""
    de = nx.descendants(Gh, T)
    return sorted((set(Gh.predecessors(T)) | (set(Gh.predecessors(Y)) - de)) - {T, Y})

def local_metrics(G, Gh, Un, T, Y):
    """Presisi/recall sisi yang bersinggungan dengan T atau Y (target S13)."""
    q = {T, Y}; loc = lambda E: {frozenset(e) for e in E if set(e) & q}
    t = loc(G.edges); h = loc(Gh.edges) | loc(Un); tp = len(t & h)
    return dict(recall_TY=tp / max(len(t), 1), FDR_TY=len(h - t) / max(len(h), 1))

VARIANTS = {nm: (nm, None) for nm in TESTS} | {f'desain_S13_a{int(a*100)}': ('desain_usulan', a) for a in (.10, .20, .30)}

def downstream_v4(D, G, tiers, T, Y, true, R=5, seed=0, max_k=2):
    Zo = sorted(G.predecessors(T)); o, olo, ohi, *_ = effect_s9(D, T, Y, [Zo], R=R, seed=seed); ose = (ohi - olo) / 3.92
    out = []
    for nm, (base, aq) in VARIANTS.items():
        test = TESTS[base] if aq is None else query_aware(TESTS[base], T, Y, alpha_q=aq)
        t0 = time.time(); Gh, Un, nt = discover_v3(D, tiers, test, max_k=max_k); sec = time.time() - t0
        r = dict(uji=nm, **edge_metrics(G, Gh, Un), **local_metrics(G, Gh, Un, T, Y), detik=sec, n_uji=nt, est_orakel=o)
        for tag, sets in (('', cand_sets(Gh, Un, T, Y)), ('_S12', [backup_set(Gh, Un, T, Y)])):
            rd, lo, hi, ulo, uhi = effect_s9(D, T, Y, sets, R=R, seed=seed)
            v = float(np.mean([valid_adjust(G, T, Y, Z) for Z in sets])); b = rd - o
            r |= {f'adj_valid{tag}': v, f'err{tag}': rd - true, f'cover{tag}': lo <= true <= hi,
                  f'cover_union{tag}': ulo <= true <= uhi, f'bias_set{tag}': b,
                  f'material{tag}': (v < 1) and abs(b) > ose, f'k_set{tag}': np.mean([len(Z) for Z in sets])}
        out.append(r)
    return out
