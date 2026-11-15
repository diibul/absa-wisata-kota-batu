"""Eksperimen 2: Pendekatan Deep Learning (BiLSTM) untuk klasifikasi sentimen dan aspek.
Menguji dua kondisi:
1. Data Asli (tanpa augmentasi pada data latih)
2. Data Augmentasi (data latih diseimbangkan dengan EDA dan Back-translation)
Data uji pada kedua kondisi selalu 100% data asli (Stratified Group K-Fold, 5 Folds).
Jalankan dari folder utama proyek:  python scripts/eksperimen_deep_learning.py
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
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

warnings.filterwarnings("ignore")

# Direktori input dan output
GOLD_PATH = os.path.join("data", "ABSA", "04_gold_standard", "gold_standard_gabungan.csv")
BT_PATH = os.path.join("data", "ABSA", "04_gold_standard", "aug_backtranslation.csv")
OUT_DIR = os.path.join("hasil", "eksperimen_deep_learning")
os.makedirs(OUT_DIR, exist_ok=True)

SEEDS = [42, 43, 44, 45, 46]
N_FOLDS = 5
MAX_LEN = 60
EMBED_DIM = 100
HIDDEN_DIM = 64
BATCH_SIZE = 32
EPOCHS = 15
LR = 0.001

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


def normalisasi(teks):
    teks = re.sub(r"[^a-z0-9\s]", " ", str(teks).lower())
    return re.sub(r"\s+", " ", teks).strip()


def muat_bt():
    if not os.path.exists(BT_PATH):
        return {}
    d = pd.read_csv(BT_PATH, encoding="utf-8-sig").dropna(subset=["teks", "hasil"])
    peta = {}
    for _, r in d.iterrows():
        asli, hasil = normalisasi(r["teks"]), normalisasi(r["hasil"])
        if hasil and hasil != asli:
            peta.setdefault(asli, [])
            if hasil not in peta[asli]:
                peta[asli].append(hasil)
    return peta


def target_ukuran(hitung):
    urut = sorted(hitung.values(), reverse=True)
    return urut[1] if len(urut) > 1 else urut[0]


def eda_satu(kata, kosa, rng):
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


def augment_gabungan(X, y, rng, peta):
    """Kombinasi Back-translation dan EDA untuk menaikkan kelas minoritas hingga sebesar target."""
    hitung = Counter(y)
    target = target_ukuran(hitung)
    Xb, yb = list(X), list(y)
    for kelas, n in hitung.items():
        if n >= target:
            continue
        butuh = target - n
        kandidat_bt = [(X[i], v) for i, lab in enumerate(y) if lab == kelas for v in peta.get(X[i], [])]
        rng.shuffle(kandidat_bt)
        pakai_bt = []
        ada = set(X)
        for _, v in kandidat_bt:
            if v not in ada:
                pakai_bt.append(v)
                ada.add(v)
            if len(pakai_bt) >= butuh:
                break
        Xb += pakai_bt
        yb += [kelas] * len(pakai_bt)

        sisa_butuh = butuh - len(pakai_bt)
        if sisa_butuh > 0:
            idx = [i for i, v in enumerate(y) if v == kelas]
            kosa = sorted({w for i in idx for w in X[i].split()})
            baru_eda = {}
            coba = 0
            while len(baru_eda) < sisa_butuh and coba < sisa_butuh * 40:
                i = rng.choice(idx)
                s = eda_satu(X[i].split(), kosa, rng)
                coba += 1
                if s != X[i] and s not in ada and s not in baru_eda:
                    baru_eda[s] = True
            Xb += list(baru_eda.keys())
            yb += [kelas] * len(baru_eda)
    return Xb, yb


# ---------- Pemrosesan Teks Sekuensial ----------
class Kosakata:
    def __init__(self):
        self.w2i = {"<PAD>": 0, "<UNK>": 1}
        self.i2w = {0: "<PAD>", 1: "<UNK>"}

    def bangun(self, texts, min_freq=1):
        freq = Counter(w for t in texts for w in t.split())
        for w, c in freq.items():
            if c >= min_freq and w not in self.w2i:
                idx = len(self.w2i)
                self.w2i[w] = idx
                self.i2w[idx] = w

    def encode(self, text, max_len=MAX_LEN):
        tokens = [self.w2i.get(w, 1) for w in text.split()][:max_len]
        if len(tokens) < max_len:
            tokens += [0] * (max_len - len(tokens))
        return tokens

    def __len__(self):
        return len(self.w2i)


class TeksDataset(Dataset):
    def __init__(self, texts, labels, vocab, label_to_idx):
        self.X = [vocab.encode(t) for t in texts]
        self.y = [label_to_idx[l] for l in labels]

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return torch.tensor(self.X[idx], dtype=torch.long), torch.tensor(self.y[idx], dtype=torch.long)


# ---------- Model PyTorch BiLSTM ----------
class BiLSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_classes, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        emb = self.dropout(self.embedding(x))
        _, (h_n, _) = self.lstm(emb)
        # h_n shape: (2, batch_size, hidden_dim)
        h_cat = torch.cat((h_n[-2, :, :], h_n[-1, :, :]), dim=1)
        out = self.fc(self.dropout(h_cat))
        return out


def latih_dan_prediksi(train_texts, train_labels, test_texts, test_labels, num_classes, label_to_idx, seed):
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    vocab = Kosakata()
    vocab.bangun(train_texts)

    train_ds = TeksDataset(train_texts, train_labels, vocab, label_to_idx)
    test_ds = TeksDataset(test_texts, test_labels, vocab, label_to_idx)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = BiLSTMClassifier(len(vocab), EMBED_DIM, HIDDEN_DIM, num_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    model.train()
    for epoch in range(EPOCHS):
        for bx, by in train_loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()

    model.eval()
    preds = []
    with torch.no_grad():
        for bx, _ in test_loader:
            out = model(bx)
            p = torch.argmax(out, dim=1).cpu().numpy()
            preds.extend(p)

    idx_to_label = {v: k for k, v in label_to_idx.items()}
    return [idx_to_label[i] for i in preds]


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
        print(f"File tidak ditemukan: {GOLD_PATH}")
        return

    gold = pd.read_csv(GOLD_PATH, encoding="utf-8-sig")
    gold["teks"] = gold["teks_aspek"].apply(normalisasi)
    peta_bt = muat_bt()
    print(f"Dataset ABSA Gold: {len(gold)} baris ulasan dari {gold['review_id'].nunique()} ulasan unik.")

    hasil = []
    laporan_txt = []

    skenario_dl = [
        ("Data Asli", False),
        ("Data Augmentasi", True)
    ]

    for tugas in ["sentimen", "aspek"]:
        X = gold["teks"].values
        y = gold[tugas].values
        groups = gold["review_id"].values
        label_list = sorted(list(set(y)))
        label_to_idx = {l: i for i, l in enumerate(label_list)}
        num_classes = len(label_list)

        for nama_skenario, pake_aug in skenario_dl:
            print(f"\n--- Memulai {tugas.upper()} | {nama_skenario} ---")
            akurasi_list, macro_f1_list, f1_netral_list = [], [], []
            laporan_seed0, cm_seed0 = None, None

            for seed_idx, seed in enumerate(SEEDS):
                cv = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
                pred_oof = np.empty(len(y), dtype=object)

                for fold_idx, (idx_latih, idx_uji) in enumerate(cv.split(X, y, groups)):
                    X_tr, y_tr = list(X[idx_latih]), list(y[idx_latih])
                    X_te, y_te = list(X[idx_uji]), list(y[idx_uji])

                    if pake_aug:
                        rng = random.Random(seed + fold_idx)
                        X_tr, y_tr = augment_gabungan(X_tr, y_tr, rng, peta_bt)

                    pred_fold = latih_dan_prediksi(
                        X_tr, y_tr, X_te, y_te, num_classes, label_to_idx, seed + fold_idx
                    )
                    pred_oof[idx_uji] = pred_fold

                acc = accuracy_score(y, pred_oof)
                mf1 = f1_score(y, pred_oof, average="macro", zero_division=0)
                akurasi_list.append(acc)
                macro_f1_list.append(mf1)

                if tugas == "sentimen":
                    f1_n = f1_score(y, pred_oof, labels=["Netral"], average="macro", zero_division=0)
                    f1_netral_list.append(f1_n)

                if seed_idx == 0:
                    laporan_seed0 = classification_report(y, pred_oof, labels=label_list, zero_division=0)
                    cm_seed0 = confusion_matrix(y, pred_oof, labels=label_list)

                print(f"  Seed {seed}: Akurasi = {acc:.3f}, Macro F1 = {mf1:.3f}")

            baris = {
                "tugas": tugas,
                "skenario": nama_skenario,
                "model": "BiLSTM",
                "embedding": f"Dense ({EMBED_DIM}d)",
                "akurasi": np.mean(akurasi_list),
                "akurasi_std": np.std(akurasi_list),
                "macro_f1": np.mean(macro_f1_list),
                "macro_f1_std": np.std(macro_f1_list),
            }
            if tugas == "sentimen":
                baris["f1_netral"] = np.mean(f1_netral_list)
            hasil.append(baris)

            # Simpan laporan teks dan visualisasi CM untuk seed pertama
            nama_file_cm = f"cm_{tugas}_dl_{'aug' if pake_aug else 'asli'}.png"
            path_cm = os.path.join(OUT_DIR, nama_file_cm)
            gambar_cm(cm_seed0, label_list, f"BiLSTM | {tugas.capitalize()} | {nama_skenario}", path_cm)

            header_lap = f"=== BiLSTM | {tugas.upper()} | {nama_skenario} (Seed {SEEDS[0]}) ==="
            laporan_txt.append(f"{header_lap}\n{laporan_seed0}\n{pd.DataFrame(cm_seed0, index=label_list, columns=label_list)}\n\n")

    df_hasil = pd.DataFrame(hasil).round(3)
    df_hasil.to_csv(os.path.join(OUT_DIR, "ringkasan_deep_learning.csv"), index=False, encoding="utf-8-sig")

    with open(os.path.join(OUT_DIR, "classification_report_dl.txt"), "w", encoding="utf-8") as f:
        f.writelines(laporan_txt)

    print("\n================ RINGKASAN EKSPERIMEN 2 (BiLSTM) ================")
    print(df_hasil.to_string(index=False))
    print(f"\nSeluruh berkas berhasil disimpan di {OUT_DIR}")


if __name__ == "__main__":
    jalankan()

