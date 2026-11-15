"""Eksperimen skenario augmentasi untuk klasifikasi aspek dan sentimen.
Model: Decision Tree (dengan tiga fitur) dan model pembanding.
Skenario 1: tanpa augmentasi. Skenario 2: augmentasi EDA. Skenario 3: augmentasi back-translation.
Augmentasi hanya dilakukan pada data latih di setiap lipatan. Data uji selalu asli.
Jalankan dari folder utama proyek:  python scripts/eksperimen_skenario.py
"""
import os
import random
import re
import warnings
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")

GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard", "gold_standard_gabungan.csv")
BT_PATH = os.path.join("data", "ABSA", "04_gold_standard", "aug_backtranslation.csv")
OUT_DIR = os.path.join("hasil", "eksperimen_skenario")
os.makedirs(OUT_DIR, exist_ok=True)

SEEDS = [42, 43, 44, 45, 46]
N_FOLDS = 5

FITUR = {
    "BoW": lambda: CountVectorizer(),
    "TF-IDF": lambda: TfidfVectorizer(),
    "N-gram (1-2)": lambda: TfidfVectorizer(ngram_range=(1, 2)),
}
MODEL = {
    "Decision Tree": lambda seed: DecisionTreeClassifier(random_state=seed, class_weight="balanced"),
}


def normalisasi(teks):
    teks = re.sub(r"[^a-z0-9\s]", " ", str(teks).lower())
    return re.sub(r"\s+", " ", teks).strip()


# ---------- augmentasi ----------
SINONIM_KAMUS = {
    "bagus": ["baik", "mantap", "keren", "apik", "cantik", "indah"],
    "indah": ["cantik", "menawan", "bagus", "elok", "pesona"],
    "mahal": ["tinggi", "menguras", "berlebih"],
    "murah": ["terjangkau", "ekonomis", "merakyat", "hemat"],
    "ramah": ["sopan", "baik", "hangat", "menyenangkan"],
    "bersih": ["rapi", "higienis", "terawat", "apik"],
    "kotor": ["kumuh", "jorok", "terbengkalai", "berdebu"],
    "nyaman": ["enak", "adem", "betah", "tentram"],
    "senang": ["gembira", "puas", "bahagia", "suka"],
    "kecewa": ["sesal", "kurang", "sedih", "kesal"],
    "puas": ["senang", "mantap", "bersyukur"],
    "wahana": ["atraksi", "permainan", "fasilitas", "hiburan"],
    "tempat": ["lokasi", "area", "kawasan", "objek"],
    "tiket": ["karcis", "biaya", "tarif"],
    "harga": ["biaya", "tarif", "ongkos", "nilai"],
    "makanan": ["kuliner", "hidangan", "santapan", "menu"],
    "minuman": ["minum", "kuliner"],
    "petugas": ["staf", "pegawai", "karyawan", "pelayan"],
    "luas": ["lebar", "lapang", "lega", "besar"],
    "sempit": ["sesak", "padat", "ramai"],
    "ramai": ["padat", "sesak", "banyak"],
    "sepi": ["lengang", "tenang", "sunyi"],
    "antre": ["antri", "menunggu"],
    "banyak": ["berlimpah", "beragam", "aneka"],
    "sedikit": ["minim", "kurang", "terbatas"],
    "cocok": ["pas", "sesuai", "tepat"],
    "anak": ["anak-anak", "bocah", "balita", "keluarga"],
    "edukasi": ["pembelajaran", "edukatif", "pendidikan", "wawasan"],
    "belajar": ["edukasi", "mengetahui", "mengenal"],
    "koleksi": ["pameran", "artefak", "barang", "pajangan"],
    "spot": ["titik", "lokasi", "sudut", "area"],
    "foto": ["gambar", "swafoto", "potret"],
    "parkir": ["parkiran", "lahan", "tempat"],
    "toilet": ["kamar mandi", "wc", "fasilitas"],
    "mushola": ["tempat ibadah", "surau", "masjid"],
}


def target_ukuran(hitung):
    """Kelas yang lebih kecil dinaikkan sampai sebesar kelas terbesar kedua."""
    urut = sorted(hitung.values(), reverse=True)
    return urut[1] if len(urut) > 1 else urut[0]


def eda_satu(kata, kosa, rng):
    """Satu variasi EDA:
    - Semantic replacement: mengganti kata dengan sinonim
    - Semantic insertion: menyisipkan sinonim kata yang ada
    - Random swap: menukar posisi dua kata
    - Random deletion: menghapus kata
    - Random insertion: menyisipkan kata dari kosakata kelas
    """
    k = list(kata)
    op = rng.choice(["sinonim_ganti", "sinonim_sisip", "tukar", "hapus", "sisip"])

    if op == "sinonim_ganti":
        kandidat = [i for i, w in enumerate(k) if w in SINONIM_KAMUS]
        if kandidat:
            i = rng.choice(kandidat)
            k[i] = rng.choice(SINONIM_KAMUS[k[i]])
            return " ".join(k)
        op = "tukar"

    if op == "sinonim_sisip":
        kandidat = [w for w in k if w in SINONIM_KAMUS]
        if kandidat:
            w = rng.choice(kandidat)
            sinonim = rng.choice(SINONIM_KAMUS[w])
            k.insert(rng.randrange(len(k) + 1), sinonim)
            return " ".join(k)
        op = "sisip"

    if op == "tukar" and len(k) >= 2:
        i, j = rng.sample(range(len(k)), 2)
        k[i], k[j] = k[j], k[i]
    elif op == "hapus" and len(k) >= 3:
        sisa = [w for w in k if rng.random() > 0.12]
        k = sisa if len(sisa) >= 2 else k
    else:
        k.insert(rng.randrange(len(k) + 1), rng.choice(kosa))
    return " ".join(k)


def augment_eda(X, y, rng):
    hitung = Counter(y)
    target = target_ukuran(hitung)
    Xb, yb, contoh = list(X), list(y), []
    for kelas, n in hitung.items():
        if n >= target:
            continue
        idx = [i for i, v in enumerate(y) if v == kelas]
        kosa = sorted({w for i in idx for w in X[i].split()})
        butuh, baru, coba = target - n, {}, 0
        while len(baru) < butuh and coba < butuh * 40:
            i = rng.choice(idx)
            s = eda_satu(X[i].split(), kosa, rng)
            coba += 1
            if s != X[i] and s not in baru:
                baru[s] = X[i]
        Xb += list(baru.keys())
        yb += [kelas] * len(baru)
        contoh += [(kelas, asli, s, "EDA") for s, asli in list(baru.items())[:8]]
    return Xb, yb, contoh


def muat_bt():
    if not os.path.exists(BT_PATH):
        return None
    d = pd.read_csv(BT_PATH, encoding="utf-8-sig").dropna(subset=["teks", "hasil"])
    peta = {}
    for _, r in d.iterrows():
        asli, hasil = normalisasi(r["teks"]), normalisasi(r["hasil"])
        if hasil and hasil != asli:
            peta.setdefault(asli, [])
            if hasil not in peta[asli]:
                peta[asli].append(hasil)
    return peta


def augment_bt(X, y, rng, peta):
    hitung = Counter(y)
    target = target_ukuran(hitung)
    Xb, yb, contoh = list(X), list(y), []
    for kelas, n in hitung.items():
        if n >= target:
            continue
        kandidat = [(X[i], v) for i, lab in enumerate(y) if lab == kelas for v in peta.get(X[i], [])]
        rng.shuffle(kandidat)
        pakai, ada = [], set(X)
        for asli, v in kandidat:
            if v not in ada:
                pakai.append((asli, v)); ada.add(v)
            if len(pakai) >= target - n:
                break
        Xb += [v for _, v in pakai]
        yb += [kelas] * len(pakai)
        contoh += [(kelas, a, v, "Back-translation") for a, v in pakai[:8]]
    return Xb, yb, contoh


SKENARIO = {"1 Tanpa augmentasi": None, "2 EDA": "eda", "3 Back-translation": "bt"}


def gambar_cm(cm, label, judul, path):
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(label)), labels=label, rotation=35, ha="right")
    ax.set_yticks(range(len(label)), labels=label)
    ax.set_xlabel("Prediksi"); ax.set_ylabel("Label sebenarnya"); ax.set_title(judul)
    batas = cm.max() / 2
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="white" if cm[i, j] > batas else "black")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def cv_prediksi(X, y, groups, nama_fitur, nama_model, seed, mode, peta, catat=None):
    cv = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
    pred = np.empty(len(y), dtype=object)
    rng = random.Random(seed)
    for k, (tr, te) in enumerate(cv.split(X, y, groups)):
        Xt, yt = list(X.iloc[tr]), list(y.iloc[tr])
        sebelum = Counter(yt)
        contoh = []
        if mode == "eda":
            Xt, yt, contoh = augment_eda(Xt, yt, rng)
        elif mode == "bt":
            Xt, yt, contoh = augment_bt(Xt, yt, rng, peta)
        if catat is not None and k == 0:
            catat["sebelum"], catat["sesudah"], catat["contoh"] = sebelum, Counter(yt), contoh
        if nama_model == "Pembanding (kelas terbanyak)":
            model = make_pipeline(CountVectorizer(), DummyClassifier(strategy="most_frequent"))
        else:
            model = make_pipeline(FITUR[nama_fitur](), MODEL[nama_model](seed))
        model.fit(Xt, yt)
        pred[te] = model.predict(X.iloc[te])   # data uji selalu asli
    return pred


def jalankan():
    if not os.path.exists(GOLD_PATH):
        print(f"File tidak ditemukan: {GOLD_PATH}"); return
    gold = pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
    gold["teks"] = gold["teks_aspek"].apply(normalisasi)
    peta = muat_bt()
    skenario = {k: v for k, v in SKENARIO.items() if v != "bt" or peta}
    if not peta:
        print("File back-translation belum ada, skenario 3 dilewati.")
    print(f"Gold standard: {len(gold)} pasangan dari {gold['review_id'].nunique()} review\n")

    hasil, distribusi, contoh_semua, laporan = [], [], [], {}
    for tugas in ["sentimen", "aspek"]:
        X, y, groups = gold["teks"], gold[tugas], gold["review_id"]
        label = sorted(y.unique())
        konfig = [("Pembanding (kelas terbanyak)", "-")] + [(m, f) for m in MODEL for f in FITUR]
        for nama_skenario, mode in skenario.items():
            for nama_model, nama_fitur in konfig:
                if nama_model.startswith("Pembanding") and mode is not None:
                    continue
                akurasi, makro, f1_netral = [], [], []
                for k, seed in enumerate(SEEDS):
                    catat = {} if k == 0 else None
                    pred = cv_prediksi(X, y, groups, nama_fitur, nama_model, seed, mode, peta, catat)
                    akurasi.append(accuracy_score(y, pred))
                    makro.append(f1_score(y, pred, average="macro", zero_division=0))
                    if tugas == "sentimen":
                        f1_netral.append(f1_score(y, pred, labels=["Netral"], average="macro", zero_division=0))
                    if k == 0:
                        laporan[(tugas, nama_skenario, nama_model, nama_fitur)] = (
                            classification_report(y, pred, labels=label, zero_division=0),
                            confusion_matrix(y, pred, labels=label), label)
                        if nama_model == "Decision Tree" and nama_fitur == "BoW" and mode:
                            for kls in label:
                                distribusi.append({"tugas": tugas, "skenario": nama_skenario, "kelas": kls,
                                                   "latih_sebelum": catat["sebelum"].get(kls, 0), "latih_sesudah": catat["sesudah"].get(kls, 0)})
                            contoh_semua += [(tugas, nama_skenario) + c for c in catat["contoh"]]
                baris = {"tugas": tugas, "skenario": nama_skenario, "model": nama_model, "fitur": nama_fitur,
                         "akurasi": np.mean(akurasi), "akurasi_std": np.std(akurasi),
                         "macro_f1": np.mean(makro), "macro_f1_std": np.std(makro)}
                if tugas == "sentimen":
                    baris["f1_netral"] = np.mean(f1_netral)
                hasil.append(baris)
            print(f"selesai: {tugas} | {nama_skenario}")

    ringkasan = pd.DataFrame(hasil).round(3)
    ringkasan.to_csv(os.path.join(OUT_DIR, "ringkasan_skenario.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(distribusi).to_csv(os.path.join(OUT_DIR, "distribusi_data_latih.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(contoh_semua, columns=["tugas", "skenario", "kelas", "teks_asli", "teks_augmentasi", "metode"]).to_csv(
        os.path.join(OUT_DIR, "contoh_augmentasi.csv"), index=False, encoding="utf-8-sig")

    print("\nRINGKASAN (rata-rata dari 5 kali pengacakan)")
    print(ringkasan.to_string(index=False))

    # laporan klasifikasi dan confusion matrix untuk konfigurasi terbaik tiap tugas dan skenario
    with open(os.path.join(OUT_DIR, "classification_report.txt"), "w", encoding="utf-8") as f:
        for tugas in ["sentimen", "aspek"]:
            for nama_skenario in skenario:
                sub = ringkasan[(ringkasan.tugas == tugas) & (ringkasan.skenario == nama_skenario) & (~ringkasan.model.str.startswith("Pembanding"))]
                if sub.empty:
                    continue
                b = sub.sort_values("macro_f1", ascending=False).iloc[0]
                teks, cm, label = laporan[(tugas, nama_skenario, b["model"], b["fitur"])]
                f.write(f"=== {tugas} | skenario {nama_skenario} | {b['model']} | {b['fitur']} (seed {SEEDS[0]}) ===\n{teks}\n")
                f.write(pd.DataFrame(cm, index=label, columns=label).to_string() + "\n\n")
                nama = f"cm_{tugas}_{nama_skenario[0]}.png"
                gambar_cm(cm, label, f"{tugas} | skenario {nama_skenario} | {b['model']} | {b['fitur']}", os.path.join(OUT_DIR, nama))
                print(f"\n--- {tugas} | skenario {nama_skenario} | {b['model']} | {b['fitur']} ---")
                print(teks)
    print(f"\nHasil tersimpan di folder {OUT_DIR}")


if __name__ == "__main__":
    jalankan()
