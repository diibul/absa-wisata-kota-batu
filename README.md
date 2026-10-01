# ABSA Wisata Kota Batu

Project Machine Learning untuk menganalisis ulasan pengunjung destinasi wisata di Kota Batu menggunakan **Aspect-Based Sentiment Analysis (ABSA)**.

Data diperoleh dari ulasan Google Maps pada enam destinasi wisata di Kota Batu. Berbeda dari sentiment analysis umum, project ini menganalisis aspek yang dibicarakan oleh pengunjung beserta sentimennya.

## Destinasi

Project ini menggunakan enam destinasi wisata:

1. Jatim Park 1
2. Jatim Park 2
3. Jatim Park 3
4. Museum Angkut
5. BNS (Batu Night Spectacular)
6. Museum Tubuh

## Aspek ABSA

Aspek yang digunakan dalam analisis:

1. Daya Tarik Wisata
2. Fasilitas
3. Harga & Tiket
4. Edukasi
5. Pelayanan
6. Kuliner

Satu ulasan dapat memiliki lebih dari satu aspek.

---

# Alur Project

```text
Google Maps Reviews
        ↓
     Scraping
        ↓
     Raw Data
        ↓
 Merge & Deduplication
        ↓
   Final Dataset
        ↓
    Preprocessing
        ↓
   ABSA Annotation
        ↓
    Gold Standard
        ↓
      Modeling
        ↓
     Evaluation
        ↓
      Analysis
```

Secara umum, proses project dilakukan melalui tahapan:

**Scraping → Raw Data → Merge → Final Dataset → Preprocessing → ABSA Annotation → Gold Standard → Modeling → Evaluation → Analysis**

---

# Struktur Project

```text
absa-wisata-kota-batu/
│
├── .gitignore
├── README.md
├── requirements.txt
│
├── scripts/
│   ├── scraper.py
│   ├── merge.py
│   └── preprocess.py
│
├── data/
│   ├── raw/
│   ├── merged/
│   ├── final/
│   └── ABSA/
│       ├── 01_raw/
│       ├── 02_annotation/
│       ├── 03_audit/
│       └── 04_gold_standard/
│
├── notebooks/
│
└── browser_profile/
```

> Folder `data/`, `browser_profile/`, dan environment lokal tidak disimpan di repository GitHub.

---

# Instalasi

## Prasyarat

Pastikan sudah terpasang:

* Python
* Git
* Firefox

## 1. Clone Repository

```bash
git clone https://github.com/diibul/absa-wisata-kota-batu.git
```

Masuk ke folder project:

```bash
cd absa-wisata-kota-batu
```

## 2. Membuat Virtual Environment

Pada Windows PowerShell:

```powershell
python -m venv venv
```

Aktifkan virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Jika berhasil, akan muncul `(venv)` pada awal baris terminal.

## 3. Install Dependency

```powershell
pip install -r requirements.txt
```

## 4. Install Browser Playwright

```powershell
python -m playwright install firefox
```

Setelah seluruh langkah selesai, environment siap digunakan.

---

# Penggunaan Scraper

Scraper berada pada:

```text
scripts/scraper.py
```

---

## 1. Login Google Maps

```powershell
python scripts\scraper.py login
```

Firefox akan terbuka. Login menggunakan akun Google masing-masing. Setelah login selesai, kembali ke terminal dan lanjutkan sesuai instruksi yang ditampilkan.

Session browser akan disimpan secara lokal pada:

```text
browser_profile/
```

> Folder `browser_profile/` bersifat pribadi. Jangan mengunggah atau membagikan folder tersebut. Setiap anggota tim harus melakukan login menggunakan akun Google masing-masing.

---

## 2. Menjalankan Scraper

Scraper dijalankan berdasarkan nama destinasi.

```powershell
python scripts\scraper.py jatimpark1
python scripts\scraper.py jatimpark2
python scripts\scraper.py jatimpark3
python scripts\scraper.py museum_angkut
python scripts\scraper.py bns
python scripts\scraper.py museum_tubuh
```

Nama destinasi yang tersedia:

```text
jatimpark1
jatimpark2
jatimpark3
museum_angkut
bns
museum_tubuh
```

---

## 3. Lokasi Output

Hasil scraping akan disimpan pada:

```text
data/raw/
```

Contoh:

```text
data/raw/jatimpark1.csv
data/raw/jatimpark2.csv
data/raw/jatimpark3.csv
data/raw/museum_angkut.csv
data/raw/bns.csv
data/raw/museum_tubuh.csv
```

---

## 4. Scraping Beberapa Sesi

Scraper saat ini belum memiliki mekanisme resume otomatis. Mode per-destinasi memiliki batas maksimal sekitar **1.000 review per sesi**.

Karena target project lebih besar, pengumpulan data dilakukan melalui beberapa sesi. Sebelum menjalankan sesi berikutnya, hasil sesi sebelumnya harus diamankan agar tidak tertimpa.

Contoh:

```text
data/raw/jatimpark1.csv
```

ubah menjadi:

```text
data/raw/jatimpark1_sesi1.csv
```

Kemudian jalankan kembali scraper untuk sesi berikutnya.

Data dari seluruh sesi akan digabungkan pada tahap merge dan dilakukan deduplikasi berdasarkan `review_id`.

---

# Target Pengumpulan Data

Target utama project adalah sekitar **15.000 review baru**.

| Destinasi     | Target     |
| ------------- | ---------: |
| Jatim Park 1  |      2.000 |
| Jatim Park 2  |      3.000 |
| Jatim Park 3  |      2.500 |
| Museum Angkut |      3.000 |
| BNS           |      2.500 |
| Museum Tubuh  |      2.000 |
| **Total**     | **15.000** |

Target minimum yang ditetapkan adalah sekitar **12.000 review**.

Data lama sebanyak **3.260 review** disimpan sebagai backup dan akan dimanfaatkan pada tahap penggabungan dataset.

---

# Pembagian Scraping

Pembagian pengumpulan data dilakukan secara seimbang, masing-masing dengan target **7.500 review**.

## Anggota A

| Destinasi    | Target    |
| ------------ | --------: |
| Jatim Park 1 |     2.000 |
| Jatim Park 2 |     3.000 |
| BNS          |     2.500 |
| **Total**    | **7.500** |

## Anggota B

| Destinasi     | Target    |
| ------------- | --------: |
| Jatim Park 3  |     2.500 |
| Museum Angkut |     3.000 |
| Museum Tubuh  |     2.000 |
| **Total**     | **7.500** |

Setiap anggota menjalankan scraper menggunakan environment dan akun Google masing-masing.

---

# Pengolahan Data

Setelah proses scraping selesai, seluruh hasil akan melalui tahapan:

```text
Raw Reviews
     ↓
Merge
     ↓
Deduplication
     ↓
Final Dataset
     ↓
Preprocessing
     ↓
ABSA Annotation
     ↓
Gold Standard
     ↓
Modeling
     ↓
Evaluation
     ↓
Analysis
```

Script pengolahan data yang tersedia:

```text
scripts/merge.py
scripts/preprocess.py
```

Penggunaan kedua script akan mengikuti konfigurasi pipeline yang digunakan pada tahap pengolahan data.

---

# Keamanan Repository

Beberapa file dan folder sengaja tidak dimasukkan ke GitHub:

```text
venv/
data/
browser_profile/
.ipynb_checkpoints/
__pycache__/
*.pyc
*.html
struktur_folder.txt
```

Dataset, backup dataset, dan session browser tetap disimpan secara lokal.

---

# Catatan

Repository ini berisi kode dan konfigurasi yang digunakan dalam pengembangan project.

Data hasil scraping tidak disimpan di repository GitHub dan dikelola secara terpisah pada environment lokal masing-masing anggota.

Setiap anggota bertanggung jawab menjaga session Google dan data lokalnya masing-masing.