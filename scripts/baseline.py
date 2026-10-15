import os
import re
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")

GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard",
                         "absa_gold_standard_200_review_v2.csv")
OUT_DIR = os.path.join("hasil", "baseline")
os.makedirs(OUT_DIR, exist_ok=True)

SEEDS = [42, 43, 44, 45, 46]   # seed pertama dipakai untuk laporan dan confusion matrix
N_FOLDS = 5

FITUR = {
    "BoW": lambda: CountVectorizer(),
    "TF-IDF": lambda: TfidfVectorizer(),
    "N-gram (1-2)": lambda: TfidfVectorizer(ngram_range=(1, 2)),
}


def normalisasi(teks):
    """Huruf kecil, buang tanda baca, emoji, dan penanda '...' pada teks_aspek."""
    teks = re.sub(r"[^a-z0-9\s]", " ", str(teks).lower())
    return re.sub(r"\s+", " ", teks).strip()


def buat_model(nama_model, seed):
    if nama_model == "Majority (pembanding)":
        return DummyClassifier(strategy="most_frequent")
    return DecisionTreeClassifier(random_state=seed, class_weight="balanced")


def prediksi_cv(X, y, groups, nama_fitur, nama_model, seed):
    """Prediksi out-of-fold. Pembagian per review_id agar potongan dari review
    yang sama tidak masuk ke data latih dan data uji sekaligus."""
    cv = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    pred = np.empty(len(y), dtype=object)
    for idx_latih, idx_uji in cv.split(X, y, groups):
        model = make_pipeline(FITUR[nama_fitur](), buat_model(nama_model, seed))
        model.fit(X.iloc[idx_latih], y.iloc[idx_latih])
        pred[idx_uji] = model.predict(X.iloc[idx_uji])
    return pred


def gambar_cm(cm, label, judul, path):
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(label)), labels=label, rotation=35, ha="right")
    ax.set_yticks(range(len(label)), labels=label)
    ax.set_xlabel("Prediksi")
    ax.set_ylabel("Label sebenarnya")
    ax.set_title(judul)
    batas = cm.max() / 2
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > batas else "black")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def jalankan():
    if not os.path.exists(GOLD_PATH):
        print(f"File gold standard tidak ditemukan: {GOLD_PATH}")
        return

    gold = pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
    gold["teks"] = gold["teks_aspek"].apply(normalisasi)

    tugas = {
        "aspek": gold.copy(),
        "sentimen": gold[gold["sentimen"] != "Netral"].copy(),
    }
    kolom_label = {"aspek": "aspek", "sentimen": "sentimen"}

    print(f"Gold standard: {len(gold)} pasangan dari {gold['review_id'].nunique()} review")
    print(f"Tugas sentimen memakai Positif dan Negatif saja "
          f"({len(tugas['sentimen'])} pasangan, {len(gold) - len(tugas['sentimen'])} Netral dikeluarkan)")

    baris, laporan = [], []
    for nama_tugas, df in tugas.items():
        df = df.reset_index(drop=True)
        X, y, groups = df["teks"], df[kolom_label[nama_tugas]], df["review_id"]
        label = sorted(y.unique())
        for nama_fitur in FITUR:
            for nama_model in ["Decision Tree", "Majority (pembanding)"]:
                if nama_model.startswith("Majority") and nama_fitur != "BoW":
                    continue  # pembanding cukup satu kali per tugas
                akurasi, makro = [], []
                for k, seed in enumerate(SEEDS):
                    pred = prediksi_cv(X, y, groups, nama_fitur, nama_model, seed)
                    akurasi.append(accuracy_score(y, pred))
                    makro.append(f1_score(y, pred, average="macro", zero_division=0))
                    if k == 0 and nama_model == "Decision Tree":
                        laporan.append((nama_tugas, nama_fitur,
                                        classification_report(y, pred, labels=label, zero_division=0),
                                        confusion_matrix(y, pred, labels=label), label))
                baris.append({
                    "tugas": nama_tugas,
                    "fitur": nama_fitur if nama_model == "Decision Tree" else "-",
                    "model": nama_model,
                    "akurasi_rata": np.mean(akurasi), "akurasi_std": np.std(akurasi),
                    "macro_f1_rata": np.mean(makro), "macro_f1_std": np.std(makro),
                })

    ringkasan = pd.DataFrame(baris).round(3)
    ringkasan.to_csv(os.path.join(OUT_DIR, "ringkasan_baseline.csv"),
                     index=False, encoding="utf-8-sig")

    with open(os.path.join(OUT_DIR, "classification_report.txt"), "w", encoding="utf-8") as f:
        for nama_tugas, nama_fitur, teks, cm, label in laporan:
            f.write(f"=== Tugas: {nama_tugas} | Fitur: {nama_fitur} | Decision Tree (seed {SEEDS[0]}) ===\n")
            f.write(teks + "\n")
            f.write("Confusion matrix (baris = sebenarnya, kolom = prediksi)\n")
            f.write(pd.DataFrame(cm, index=label, columns=label).to_string() + "\n\n")
            nama_berkas = f"confusion_matrix_{nama_tugas}_{nama_fitur.split()[0].lower()}.png"
            gambar_cm(cm, label, f"{nama_tugas} | {nama_fitur}", os.path.join(OUT_DIR, nama_berkas))

    print("\nRINGKASAN (rata-rata dan simpangan baku dari 5 kali pengacakan)")
    print(ringkasan.to_string(index=False))

    for nama_tugas in tugas:
        sub = ringkasan[(ringkasan["tugas"] == nama_tugas) & (ringkasan["model"] == "Decision Tree")]
        terbaik = sub.sort_values("macro_f1_rata", ascending=False).iloc[0]["fitur"]
        for t, f_, teks, cm, label in laporan:
            if t == nama_tugas and f_ == terbaik:
                print(f"\n--- Laporan klasifikasi: {t} | {f_} (macro F1 tertinggi) ---")
                print(teks)
                print(pd.DataFrame(cm, index=label, columns=label).to_string())

    print(f"\nHasil tersimpan di folder {OUT_DIR}")


if __name__ == "__main__":
    jalankan()
