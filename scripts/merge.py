import os
import glob
import pandas as pd

RAW_DIR = os.path.join("data", "raw")
MERGED_DIR = os.path.join("data", "merged")
os.makedirs(MERGED_DIR, exist_ok=True)

KOLOM = ["destinasi", "review_id", "bintang", "ulasan", "tanggal", "teks_asli"]
TARGET = {
    "jatimpark1": 2000,
    "jatimpark2": 3000,
    "jatimpark3": 2500,
    "museum_angkut": 3000,
    "bns": 2500,
    "museum_tubuh": 2000,
}


def merge():
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
    if not files:
        print("Tidak ada file CSV di data/raw/")
        return

    df_list = []
    for f in files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        nama = os.path.basename(f)
        if list(df.columns) != KOLOM:
            print(f"PERINGATAN {nama}: kolom berbeda -> {list(df.columns)}")
            continue
        print(f"{nama}: {len(df)} baris")
        df_list.append(df)

    merged = pd.concat(df_list, ignore_index=True)

    # Duplikat berdasarkan review_id (lintas file)
    before = len(merged)
    merged = merged.drop_duplicates(subset="review_id", keep="first")
    print(f"\nDuplikat review_id dihapus: {before - len(merged)} baris")

    out_path = os.path.join(MERGED_DIR, "dataset_gabungan.csv")
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Total: {len(merged)} ulasan")

    print("\nJumlah per destinasi (terhadap target):")
    jml = merged["destinasi"].value_counts()
    for d in sorted(set(jml.index) | set(TARGET)):
        n = int(jml.get(d, 0))
        t = TARGET.get(d)
        ket = f"/ {t} ({n / t:.0%})" if t else ""
        print(f"  {d}: {n} {ket}")

    print("\nDistribusi bintang per destinasi:")
    print(pd.crosstab(merged["destinasi"], merged["bintang"]).to_string())

    print(f"\nFile tersimpan ke {out_path}")


if __name__ == "__main__":
    merge()