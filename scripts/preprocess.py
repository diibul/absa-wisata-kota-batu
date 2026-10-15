import os
import re
import pandas as pd

IN_PATH = os.path.join("data", "merged", "dataset_gabungan.csv")
OUT_DIR = os.path.join("data", "processed")
OUT_PATH = os.path.join(OUT_DIR, "dataset_bersih.csv")
os.makedirs(OUT_DIR, exist_ok=True)

GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard",
                         "absa_gold_standard_200_review_v2.csv")

URL_RE = re.compile(r"https?://\S+|www\.\S+")
TRANSLATED_RE = re.compile(r"\(Translated by Google\)|\(Original\)")


def bersihkan_teks(teks):
    """Pembersihan ringan: baris baru dan tab menjadi spasi, spasi ganda dirapikan.
    Huruf kapital, emoji, dan tanda baca dipertahankan agar teks tetap sesuai
    ulasan asli saat anotasi manual."""
    teks = re.sub(r"[\r\n\t]+", " ", str(teks))
    teks = re.sub(r" {2,}", " ", teks)
    return teks.strip()


def _rapikan(teks):
    return re.sub(r"\s+", " ", str(teks)).strip()


def _tanpa_elipsis(teks):
    return re.sub(r"\s*(\u2026|\.\.\.)\s*$", "", teks)


def perbaiki_terpotong(df):
    """Ganti ulasan yang terpotong dengan versi lengkapnya dari gold standard.
    Syarat: teks gold lebih panjang dan diawali teks dataset (tanpa elipsis akhir).
    Kolom 'ulasan' asli tidak diubah. Teks hasil perbaikan dipakai untuk 'ulasan_bersih'."""
    sumber = df["ulasan"].copy()
    df["ulasan_diperbaiki"] = False
    if not os.path.exists(GOLD_PATH):
        print(f"Gold standard tidak ditemukan di {GOLD_PATH}. Perbaikan teks dilewati.")
        return sumber, df
    gold = (pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
            .drop_duplicates("review_id").set_index("review_id")["ulasan"])
    posisi = {rid: i for i, rid in zip(df.index, df["review_id"])}
    for rid, teks_gold in gold.items():
        if rid not in posisi:
            continue
        i = posisi[rid]
        a, b = _rapikan(sumber.at[i]), _rapikan(teks_gold)
        if len(b) > len(a) and b.startswith(_tanpa_elipsis(a)):
            sumber.at[i] = teks_gold
            df.at[i, "ulasan_diperbaiki"] = True
    return sumber, df


def parse_tanggal(teks):
    """Ubah tanggal relatif Google Maps menjadi perkiraan usia ulasan (bulan)
    dan penanda ulasan diedit. Hanya perkiraan kasar, karena tanggal scraping
    tidak tercatat di data."""
    t = str(teks).strip().lower()
    diedit = t.startswith("diedit")
    t = t.replace("diedit", "").strip()
    if t == "setahun lalu":
        bulan = 12.0
    elif t == "sebulan lalu":
        bulan = 1.0
    else:
        m = re.match(r"(\d+)\s+(tahun|bulan|minggu|hari)\s+lalu", t)
        if not m:
            return pd.Series([None, diedit])
        n, satuan = int(m.group(1)), m.group(2)
        bulan = {"tahun": n * 12.0, "bulan": float(n),
                 "minggu": n / 4.0, "hari": n / 30.0}[satuan]
    return pd.Series([bulan, diedit])


def preprocess():
    df = pd.read_csv(IN_PATH, encoding="utf-8-sig")
    n_awal = len(df)

    sumber, df = perbaiki_terpotong(df)
    df["ulasan_bersih"] = sumber.apply(bersihkan_teks)

    # Buang baris yang kosong setelah dibersihkan
    df = df[df["ulasan_bersih"] != ""].copy()
    n_kosong = n_awal - len(df)

    df[["usia_bulan", "diedit"]] = df["tanggal"].apply(parse_tanggal)

    df["jumlah_karakter"] = df["ulasan_bersih"].str.len()
    df["jumlah_kata"] = df["ulasan_bersih"].str.split().str.len()
    df["ada_url"] = df["ulasan_bersih"].str.contains(URL_RE)
    df["ada_terjemahan"] = df["ulasan_bersih"].str.contains(TRANSLATED_RE)
    df["diduga_terpotong"] = df["ulasan_bersih"].str.endswith(("…", "..."))
    df["teks_duplikat"] = df.duplicated(subset="ulasan_bersih", keep=False)

    kolom = ["destinasi", "review_id", "bintang", "ulasan", "ulasan_bersih",
             "tanggal", "usia_bulan", "diedit", "teks_asli", "jumlah_karakter",
             "jumlah_kata", "ada_url", "ada_terjemahan", "diduga_terpotong",
             "ulasan_diperbaiki", "teks_duplikat"]
    df = df[kolom]
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Baris awal: {n_awal}")
    print(f"Baris kosong dibuang: {n_kosong}")
    print(f"Baris akhir: {len(df)}")
    print(f"\nTanggal tidak terbaca: {df['usia_bulan'].isna().sum()}")
    print(f"Ulasan diedit: {int(df['diedit'].sum())}")
    print(f"Ulasan mengandung URL: {int(df['ada_url'].sum())}")
    print(f"Ulasan mengandung penanda terjemahan: {int(df['ada_terjemahan'].sum())}")
    print(f"Ulasan dengan teks identik: {int(df['teks_duplikat'].sum())}")
    print(f"Ulasan terpotong diperbaiki dari gold standard: {int(df['ulasan_diperbaiki'].sum())}")
    print(f"Ulasan diduga terpotong (berakhir elipsis): {int(df['diduga_terpotong'].sum())} ({df['diduga_terpotong'].mean():.1%})")
    print(df.groupby("destinasi")["diduga_terpotong"].agg(["sum", "mean"]).round(3).to_string())
    print("\nPanjang ulasan (jumlah kata) per destinasi:")
    print(df.groupby("destinasi")["jumlah_kata"].describe()[["count", "mean", "50%", "max"]].round(1).to_string())
    print(f"\nFile tersimpan ke {OUT_PATH}")


if __name__ == "__main__":
    preprocess()
