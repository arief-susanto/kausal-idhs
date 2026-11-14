"""E10: cocokkan atestasi Bitcoin di bukti OpenTimestamps dengan header blok dari dua penjelajah blok independen.

Merkle root setiap atestasi dibaca dari log `ots info` (tabel/E10_opentimestamps/log_info.txt), lalu dibandingkan dengan
merkle root dan waktu header blok dari blockchain.info dan api.blockcypher.com. Yang terbukti tanpa memercayai server
kalender adalah: manifest sudah ada sebelum waktu header blok atestasi paling awal.
Catatan jaringan: sebagian penjelajah (mis. blockstream.info, mempool.space) dapat diblokir penyaring DNS penyedia
internet; kedua sumber di sini dipilih karena dapat diakses dan saling independen. Node Bitcoin sendiri (`ots verify`)
adalah alternatif tanpa pihak ketiga.

Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/verifikasi_blok_ots.py
Keluaran: naskah/03_reproduksibilitas/tabel/E10_verifikasi_blok.csv
"""
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "tabel/E10_opentimestamps/log_info.txt"
balik = lambda h: bytes.fromhex(h)[::-1].hex()
ambil = lambda u: json.load(urllib.request.urlopen(u, timeout=30))

teks = LOG.read_text(encoding="utf-8")
atestasi = dict(re.findall(r"BitcoinBlockHeaderAttestation\((\d+)\)\s*\n\s*# Bitcoin block merkle root ([0-9a-f]{64})", teks))
baris = []
for tinggi, merkle in sorted(atestasi.items()):
    a = ambil(f"https://blockchain.info/block-height/{tinggi}?format=json")["blocks"][0]
    b = ambil(f"https://api.blockcypher.com/v1/btc/main/blocks/{tinggi}?txstart=0&limit=1")
    baris.append(dict(blok=int(tinggi), merkle_ots=merkle,
                      waktu_blockchain_info=dt.datetime.fromtimestamp(a["time"], dt.timezone.utc).isoformat(),
                      waktu_blockcypher=b["time"],
                      merkle_cocok_blockchain_info=merkle in (a["mrkl_root"], balik(a["mrkl_root"])),
                      merkle_cocok_blockcypher=merkle in (b["mrkl_root"], balik(b["mrkl_root"])),
                      hash_blok=a["hash"]))
E = pd.DataFrame(baris)
assert E.merkle_cocok_blockchain_info.all() and E.merkle_cocok_blockcypher.all(), "merkle root tidak cocok"
assert all(x[:19] == y[:19] for x, y in zip(E.waktu_blockchain_info, E.waktu_blockcypher)), "waktu header berbeda"
E.to_csv(ROOT / "tabel/E10_verifikasi_blok.csv", index=False)
print(E[["blok", "waktu_blockchain_info", "merkle_cocok_blockchain_info", "merkle_cocok_blockcypher"]].to_string(index=False))
