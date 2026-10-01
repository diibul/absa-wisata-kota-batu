import pandas as pd
import os
import glob

RAW_DIR    = os.path.join("data", "raw")
MERGED_DIR = os.path.join("data", "merged")
os.makedirs(MERGED_DIR, exist_ok=True)

def merge():
    files = glob.glob(os.path.join(RAW_DIR, "*.csv"))

    if not files:
        print("Tidak ada file CSV di data/raw/")
        return

    print(f"File ditemukan: {len(files)}")
    for f in files:
        print(f"  {os.path.basename(f)}")

    df_list = []
    for f in files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        print(f"  {os.path.basename(f)}: {len(df)} baris")
        df_list.append(df)

    merged = pd.concat(df_list, ignore_index=True)

    # Hapus duplikat jika ada
    before = len(merged)
    merged = merged.drop_duplicates()
    after = len(merged)
    if before != after:
        print(f"Duplikat dihapus: {before - after} baris")

    out_path = os.path.join(MERGED_DIR, "dataset_gabungan.csv")
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\nTotal: {len(merged)} ulasan")
    print(f"Distribusi bintang:")
    print(merged["bintang"].value_counts().sort_index().to_string())
    print(f"\nFile tersimpan ke {out_path}")

if __name__ == "__main__":
    merge()