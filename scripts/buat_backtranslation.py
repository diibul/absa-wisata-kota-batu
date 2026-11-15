"""Membuat data augmentasi back-translation: Indonesia -> bahasa lain -> Indonesia.
Butuh internet dan library deep-translator:  pip install deep-translator
Jalankan dari folder utama proyek:  python scripts/buat_backtranslation.py
Bisa dihentikan kapan saja (Ctrl+C) dan dilanjutkan lagi, hasil yang sudah ada tidak diulang.
"""
import argparse
import os
import re
import time

import pandas as pd

GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard", "gold_standard_gabungan.csv")
OUT_PATH = os.path.join("data", "ABSA", "04_gold_standard", "aug_backtranslation.csv")


def normalisasi(teks):
    teks = re.sub(r"[^a-z0-9\s]", " ", str(teks).lower())
    return re.sub(r"\s+", " ", teks).strip()


def terjemah(teks, asal, tujuan):
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source=asal, target=tujuan).translate(teks)


def teks_perlu_augmentasi():
    """Potongan teks dari kelas yang lebih kecil dari kelas terbesar kedua (sentimen dan aspek)."""
    g = pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
    g["teks"] = g["teks_aspek"].apply(normalisasi)
    kumpul = set()
    for tugas in ["sentimen", "aspek"]:
        hitung = g[tugas].value_counts()
        target = hitung.iloc[1]
        kecil = hitung[hitung < target].index
        kumpul |= set(g.loc[g[tugas].isin(kecil), "teks"])
    return sorted(t for t in kumpul if t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bahasa", nargs="+", default=["ja", "zh-CN", "ru", "vi"],
                    help="kode bahasa perantara (ja=Jepang, zh-CN=China, ru=Rusia, vi=Vietnam)")
    a = ap.parse_args()
    teks_list = teks_perlu_augmentasi()
    print(f"{len(teks_list)} potongan teks akan diterjemahkan lewat {len(a.bahasa)} bahasa.")
    ada = pd.read_csv(OUT_PATH, encoding="utf-8-sig") if os.path.exists(OUT_PATH) else pd.DataFrame(columns=["teks", "bahasa", "hasil"])
    selesai = set(zip(ada["teks"], ada["bahasa"]))
    baris = ada.to_dict("records")
    for bahasa in a.bahasa:
        baru = 0
        for t in teks_list:
            if (t, bahasa) in selesai:
                continue
            hasil = None
            for percobaan in range(3):
                try:
                    antara = terjemah(t, "id", bahasa)
                    hasil = terjemah(antara, bahasa, "id")
                    break
                except Exception as e:
                    time.sleep(2 + percobaan * 3)
            if hasil:
                baris.append({"teks": t, "bahasa": bahasa, "hasil": hasil})
                selesai.add((t, bahasa)); baru += 1
                if baru % 25 == 0:
                    pd.DataFrame(baris).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
                    print(f"  {bahasa}: {baru} selesai")
            time.sleep(0.2)
        pd.DataFrame(baris).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
        print(f"Bahasa {bahasa} selesai ({baru} baru). Total baris: {len(baris)}")
    print(f"Tersimpan di {OUT_PATH}")


if __name__ == "__main__":
    main()
