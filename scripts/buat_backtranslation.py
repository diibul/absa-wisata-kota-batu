"""Membuat data augmentasi back-translation: Indonesia -> bahasa perantara -> Indonesia.
Menggunakan ThreadPoolExecutor untuk kecepatan dan penyimpanan berkala per batch.
Jalankan dari folder utama proyek:  python scripts/buat_backtranslation.py
"""
import argparse
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from deep_translator import MyMemoryTranslator

GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard", "gold_standard_gabungan.csv")
OUT_PATH = os.path.join("data", "ABSA", "04_gold_standard", "aug_backtranslation.csv")

lock = threading.Lock()


def normalisasi(teks):
    teks = re.sub(r"[^a-z0-9\s]", " ", str(teks).lower())
    return re.sub(r"\s+", " ", teks).strip()


def teks_perlu_augmentasi():
    """Mengambil potongan teks dari kelas minoritas pada sentimen dan aspek."""
    g = pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
    g["teks"] = g["teks_aspek"].apply(normalisasi)
    kumpul = set()
    for tugas in ["sentimen", "aspek"]:
        hitung = g[tugas].value_counts()
        target = hitung.iloc[1]
        kecil = hitung[hitung < target].index
        kumpul |= set(g.loc[g[tugas].isin(kecil), "teks"])
    return sorted(t for t in kumpul if t)


def proses_satu(t, bahasa):
    t_id_ke_en = MyMemoryTranslator(source="id-ID", target=bahasa)
    t_en_ke_id = MyMemoryTranslator(source=bahasa, target="id-ID")
    for percobaan in range(3):
        try:
            en = t_id_ke_en.translate(t)
            if en:
                id_back = t_en_ke_id.translate(en)
                hasil = normalisasi(id_back)
                if hasil and hasil != t:
                    return (t, bahasa, hasil)
        except Exception:
            time.sleep(1.0 + percobaan * 2.0)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bahasa", default="en-GB", help="Bahasa perantara (default: en-GB)")
    ap.add_argument("--workers", type=int, default=5, help="Jumlah thread paralel")
    a = ap.parse_args()

    teks_list = teks_perlu_augmentasi()
    print(f"Total {len(teks_list)} teks unik yang membutuhkan augmentasi.", flush=True)

    if os.path.exists(OUT_PATH):
        ada = pd.read_csv(OUT_PATH, encoding="utf-8-sig")
    else:
        ada = pd.DataFrame(columns=["teks", "bahasa", "hasil"])

    selesai = set(zip(ada["teks"], ada["bahasa"]))
    baris = ada.to_dict("records")
    print(f"Data tersimpan sebelumnya: {len(baris)} baris.", flush=True)

    sisa_teks = [t for t in teks_list if (t, a.bahasa) not in selesai]
    print(f"Sisa yang perlu diproses: {len(sisa_teks)} teks dengan {a.workers} thread.", flush=True)

    berhasil_baru = 0
    with ThreadPoolExecutor(max_workers=a.workers) as executor:
        futures = {executor.submit(proses_satu, t, a.bahasa): t for t in sisa_teks}
        for f in as_completed(futures):
            res = f.result()
            if res:
                t, bahasa, hasil = res
                with lock:
                    baris.append({"teks": t, "bahasa": bahasa, "hasil": hasil})
                    berhasil_baru += 1
                    if berhasil_baru % 10 == 0:
                        pd.DataFrame(baris).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
                        print(f"Progress: {len(baris)}/{len(teks_list)} selesai ({berhasil_baru} baru)", flush=True)

    pd.DataFrame(baris).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\nSelesai. Total data augmentasi: {len(baris)} baris.", flush=True)
    print(f"File tersimpan di: {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
