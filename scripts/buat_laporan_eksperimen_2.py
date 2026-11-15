"""Skrip pembuat dokumen laporan Word Eksperimen 2 (BiLSTM)
dengan tata letak, format tabel, dan gaya visual yang identik dengan laporan eksperimen 1.
"""
import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

OUT_PATH = r"e:\IQBAL\TUGAS KULIAH\SEMESTER 7\Machine Learning\(LAPORAN)-dataset-wisata-batu\laporan_eksperimen_2.docx"
IMG_DIR = os.path.join("hasil", "eksperimen_deep_learning")


def atur_format_paragraf(p, space_after=6, line_spacing=1.15):
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing


def atur_tabel(table, col_widths, align_right_cols=[]):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.width = col_widths[c_idx]
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.05
                if c_idx in align_right_cols and r_idx > 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif r_idx == 0:
                    for r in p.runs:
                        r.bold = True


def main():
    doc = docx.Document()
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Judul
    p0 = doc.add_paragraph()
    r0 = p0.add_run("Perbandingan Skenario Augmentasi pada Model Deep Learning (BiLSTM) Klasifikasi Aspek dan Sentimen Ulasan Wisata Kota Batu")
    r0.bold = True
    atur_format_paragraf(p0, space_after=8, line_spacing=1.15)

    # Tujuan Eksperimen
    p_tujuan_h = doc.add_paragraph()
    r_th = p_tujuan_h.add_run("Tujuan Eksperimen")
    r_th.bold = True
    atur_format_paragraf(p_tujuan_h, space_after=4)

    p_tujuan_b = doc.add_paragraph(
        "Eksperimen ini bertujuan untuk mengevaluasi kinerja model Deep Learning sekuensial berbasis "
        "Bidirectional Long Short-Term Memory (BiLSTM) dalam mengklasifikasikan aspek dan sentimen pada "
        "ulasan wisata Kota Batu dengan representasi dense word embedding. Selain itu, eksperimen ini "
        "menguji pengaruh penambahan data augmentasi (kombinasi EDA dan Back-translation) pada data latih "
        "untuk mengetahui sejauh mana penyeimbangan kelas minoritas mampu meningkatkan pengenalan model "
        "pada kelas yang minim sampel, dengan tetap mempertahankan keaslian data uji secara utuh."
    )
    atur_format_paragraf(p_tujuan_b, space_after=6)

    # Deskripsi Data & Metodologi
    p_data = doc.add_paragraph(
        "Data yang dipakai adalah gold standard gabungan: 1.521 pasangan aspek-sentimen dari 747 ulasan. "
        "Model yang digunakan adalah Bidirectional LSTM (BiLSTM) dengan dense word embedding 100 dimensi, "
        "64 hidden units, dropout 0,3, dan optimizer Adam (learning rate 0,001) yang dilatih selama 15 epoch. "
        "Evaluasi dilakukan menggunakan validasi silang 5 lipatan yang dikelompokkan per ulasan (Stratified Group K-Fold) "
        "dengan hasil dirata-ratakan dari 5 kali pengacakan (seeds 42, 43, 44, 45, 46). Kondisi 1 dilatih "
        "menggunakan data asli tanpa augmentasi. Kondisi 2 dilatih menggunakan data latih yang diseimbangkan "
        "dengan augmentasi gabungan EDA dan Back-translation khusus pada kelas minoritas. Pada kedua kondisi, "
        "data uji selalu 100% data ulasan asli."
    )
    atur_format_paragraf(p_data, space_after=6)

    # Tabel 1
    p_t1 = doc.add_paragraph()
    r_t1 = p_t1.add_run("Tabel 1. Jumlah data latih sebelum dan sesudah augmentasi (lipatan pertama, seed 42)")
    r_t1.bold = True
    atur_format_paragraf(p_t1, space_after=3)

    t1_data = [
        ["Tugas", "Kelas", "Sebelum", "Sesudah"],
        ["Sentimen", "Positif", "830", "830"],
        ["Sentimen", "Negatif", "304", "304"],
        ["Sentimen", "Netral", "81", "304"],
        ["Aspek", "Daya Tarik Wisata", "561", "561"],
        ["Aspek", "Harga & Tiket", "197", "197"],
        ["Aspek", "Edukasi", "150", "197"],
        ["Aspek", "Fasilitas", "135", "197"],
        ["Aspek", "Pelayanan", "90", "197"],
        ["Aspek", "Kuliner", "85", "197"],
    ]
    t1 = doc.add_table(rows=len(t1_data), cols=4)
    t1.style = "Table Grid"
    for r_idx, row in enumerate(t1_data):
        for c_idx, val in enumerate(row):
            t1.cell(r_idx, c_idx).text = val
    atur_tabel(t1, [Inches(1.5), Inches(2.2), Inches(1.2), Inches(1.2)], align_right_cols=[2, 3])

    # Tabel 2
    doc.add_paragraph()
    p_t2 = doc.add_paragraph()
    r_t2 = p_t2.add_run("Tabel 2. Hasil sentimen (rata-rata ± simpangan baku dari 5 kali pengacakan)")
    r_t2.bold = True
    atur_format_paragraf(p_t2, space_after=3)

    t2_data = [
        ["Model / Kondisi", "Akurasi", "Macro-F1", "F1 Netral"],
        ["BiLSTM (Data Asli)", "0,822 ± 0,005", "0,675 ± 0,006", "0,418"],
        ["BiLSTM (Data Augmentasi)", "0,806 ± 0,004", "0,674 ± 0,005", "0,449"],
        ["Kelas terbanyak (pembanding)", "0,683", "0,271", "0,000"],
    ]
    t2 = doc.add_table(rows=len(t2_data), cols=4)
    t2.style = "Table Grid"
    for r_idx, row in enumerate(t2_data):
        for c_idx, val in enumerate(row):
            t2.cell(r_idx, c_idx).text = val
    atur_tabel(t2, [Inches(2.5), Inches(1.4), Inches(1.4), Inches(1.2)], align_right_cols=[1, 2, 3])

    # Tabel 3
    doc.add_paragraph()
    p_t3 = doc.add_paragraph()
    r_t3 = p_t3.add_run("Tabel 3. Hasil aspek (rata-rata ± simpangan baku dari 5 kali pengacakan)")
    r_t3.bold = True
    atur_format_paragraf(p_t3, space_after=3)

    t3_data = [
        ["Model / Kondisi", "Akurasi", "Macro-F1"],
        ["BiLSTM (Data Asli)", "0,782 ± 0,006", "0,718 ± 0,007"],
        ["BiLSTM (Data Augmentasi)", "0,778 ± 0,009", "0,722 ± 0,010"],
        ["Kelas terbanyak (pembanding)", "0,461", "0,105"],
    ]
    t3 = doc.add_table(rows=len(t3_data), cols=3)
    t3.style = "Table Grid"
    for r_idx, row in enumerate(t3_data):
        for c_idx, val in enumerate(row):
            t3.cell(r_idx, c_idx).text = val
    atur_tabel(t3, [Inches(3.0), Inches(1.8), Inches(1.8)], align_right_cols=[1, 2])

    # Heading Classification Report
    doc.add_paragraph()
    p_cr = doc.add_paragraph()
    r_cr = p_cr.add_run("Classification report (BiLSTM, seed 42): data asli → data augmentasi")
    r_cr.bold = True
    atur_format_paragraf(p_cr, space_after=3)

    # Tabel 4
    p_t4 = doc.add_paragraph()
    r_t4 = p_t4.add_run("Tabel 4. Sentimen")
    r_t4.bold = True
    atur_format_paragraf(p_t4, space_after=3)

    t4_data = [
        ["Kelas", "Precision", "Recall", "F1-score", "Support"],
        ["Negatif", "0,75 → 0,82", "0,75 → 0,60", "0,75 → 0,69", "381"],
        ["Netral", "0,50 → 0,41", "0,33 → 0,48", "0,40 → 0,44", "101"],
        ["Positif", "0,88 → 0,85", "0,91 → 0,92", "0,89 → 0,88", "1.039"],
        ["Akurasi", "", "", "0,83 → 0,81", "1.521"],
        ["Macro avg", "0,71 → 0,69", "0,66 → 0,66", "0,68 → 0,67", "1.521"],
        ["Weighted avg", "0,82 → 0,81", "0,83 → 0,81", "0,82 → 0,81", "1.521"],
    ]
    t4 = doc.add_table(rows=len(t4_data), cols=5)
    t4.style = "Table Grid"
    for r_idx, row in enumerate(t4_data):
        for c_idx, val in enumerate(row):
            t4.cell(r_idx, c_idx).text = val
    atur_tabel(t4, [Inches(1.8), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.0)], align_right_cols=[4])

    # Tabel 5
    doc.add_paragraph()
    p_t5 = doc.add_paragraph()
    r_t5 = p_t5.add_run("Tabel 5. Aspek")
    r_t5.bold = True
    atur_format_paragraf(p_t5, space_after=3)

    t5_data = [
        ["Kelas", "Precision", "Recall", "F1-score", "Support"],
        ["Daya Tarik Wisata", "0,81 → 0,80", "0,88 → 0,88", "0,84 → 0,84", "701"],
        ["Edukasi", "0,80 → 0,79", "0,77 → 0,79", "0,78 → 0,79", "187"],
        ["Fasilitas", "0,65 → 0,68", "0,65 → 0,68", "0,65 → 0,68", "169"],
        ["Harga & Tiket", "0,84 → 0,87", "0,74 → 0,66", "0,79 → 0,75", "246"],
        ["Kuliner", "0,60 → 0,54", "0,60 → 0,69", "0,60 → 0,60", "106"],
        ["Pelayanan", "0,66 → 0,75", "0,49 → 0,51", "0,56 → 0,61", "112"],
        ["Akurasi", "", "", "0,77 → 0,77", "1.521"],
        ["Macro avg", "0,73 → 0,74", "0,69 → 0,70", "0,70 → 0,71", "1.521"],
        ["Weighted avg", "0,77 → 0,78", "0,77 → 0,77", "0,77 → 0,77", "1.521"],
    ]
    t5 = doc.add_table(rows=len(t5_data), cols=5)
    t5.style = "Table Grid"
    for r_idx, row in enumerate(t5_data):
        for c_idx, val in enumerate(row):
            t5.cell(r_idx, c_idx).text = val
    atur_tabel(t5, [Inches(1.8), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.0)], align_right_cols=[4])

    # Confusion matrix visual grid (Table 6)
    doc.add_paragraph()
    p_cm_h = doc.add_paragraph()
    r_cm_h = p_cm_h.add_run("Confusion matrix (BiLSTM, seed 42)")
    r_cm_h.bold = True
    atur_format_paragraf(p_cm_h, space_after=4)

    t6 = doc.add_table(rows=2, cols=2)
    t6.alignment = WD_TABLE_ALIGNMENT.CENTER
    matrix_info = [
        (0, 0, "cm_sentimen_dl_asli.png", "Gambar 1. Sentimen, data asli"),
        (0, 1, "cm_sentimen_dl_aug.png", "Gambar 2. Sentimen, data augmentasi"),
        (1, 0, "cm_aspek_dl_asli.png", "Gambar 3. Aspek, data asli"),
        (1, 1, "cm_aspek_dl_aug.png", "Gambar 4. Aspek, data augmentasi"),
    ]
    for row_idx, col_idx, filename, caption in matrix_info:
        cell = t6.cell(row_idx, col_idx)
        cell.width = Inches(3.2)
        p_img = cell.paragraphs[0]
        p_img.paragraph_format.space_after = Pt(2)
        img_path = os.path.join(IMG_DIR, filename)
        if os.path.exists(img_path):
            p_img.add_run().add_picture(img_path, width=Inches(3.125))
        p_cap = cell.add_paragraph(caption)
        p_cap.paragraph_format.space_after = Pt(4)

    # Pembahasan
    doc.add_paragraph()
    p_pem_h = doc.add_paragraph()
    r_pem_h = p_pem_h.add_run("Pembahasan")
    r_pem_h.bold = True
    atur_format_paragraf(p_pem_h, space_after=4)

    p_pem1 = doc.add_paragraph(
        "Model BiLSTM pada data asli menunjukkan performa dasar yang kuat dengan akurasi 0,822 pada sentimen "
        "dan 0,782 pada aspek, melampaui hasil model Decision Tree pada Eksperimen 1. Hal ini menunjukkan "
        "keunggulan arsitektur recurrent dalam menangkap dependensi sekuensial antarkata pada kalimat ulasan. "
        "Penerapan augmentasi data pada data latih memberikan pengaruh yang berbeda pada kedua tugas. "
        "Pada tugas sentimen, penambahan augmentasi menaikkan F1-score kelas Netral dari 0,418 menjadi 0,449 secara konsisten "
        "lintas 5 kali pengacakan, meskipun akurasi keseluruhan sedikit terkoreksi dari 0,822 ke 0,806 dan macro-F1 "
        "berada pada angka 0,674. Pada tugas aspek, augmentasi data berhasil menaikkan macro-F1 rata-rata dari 0,718 menjadi 0,722."
    )
    atur_format_paragraf(p_pem1, space_after=6)

    p_pem2 = doc.add_paragraph(
        "Berdasarkan laporan klasifikasi seed 42, dampak terbesar augmentasi pada sentimen terlihat pada lonjakan "
        "recall kelas Netral dari 0,33 menjadi 0,48, di mana model berhasil mengidentifikasi 48 data Netral (sebelumnya hanya 33 data). "
        "Namun, precision Netral sedikit turun dari 0,50 menjadi 0,41 akibat adanya data Positif dan Negatif yang salah diklasifikasikan "
        "sebagai Netral. Pada tugas aspek, peningkatan paling menonjol terjadi pada kelas Pelayanan (F1 naik dari 0,56 ke 0,61, "
        "dengan precision naik tajam dari 0,66 ke 0,75) dan Fasilitas (F1 naik dari 0,65 ke 0,68). Kelas Kuliner juga mencatat lonjakan "
        "recall dari 0,60 menjadi 0,69 (73 sampel terdeteksi benar dari 64 sebelumnya). Penurunan terjadi pada recall Harga & Tiket "
        "dari 0,74 ke 0,66 karena sebagian diprediksi ke kelas Daya Tarik Wisata. Secara keseluruhan, augmentasi data efektif meningkatkan "
        "kepekaan BiLSTM terhadap kelas-kelas minoritas."
    )
    atur_format_paragraf(p_pem2, space_after=6)

    # Kesimpulan
    p_kes_h = doc.add_paragraph()
    r_kes_h = p_kes_h.add_run("Kesimpulan")
    r_kes_h.bold = True
    atur_format_paragraf(p_kes_h, space_after=4)

    p_kes_b = doc.add_paragraph(
        "Model Deep Learning BiLSTM terbukti efektif untuk klasifikasi teks ulasan pariwisata karena mampu menangkap "
        "urutan konteks kalimat lebih baik daripada model berbasis frekuensi kata sederhana. Pengujian dua kondisi menunjukkan "
        "bahwa augmentasi data latih berhasil menjawab permasalahan ketimpangan kelas, terbukti dari meningkatnya sensitivitas deteksi "
        "(recall dan F1) pada kelas-kelas minoritas seperti Netral, Pelayanan, dan Fasilitas tanpa mengubah keaslian data uji. "
        "Keterbatasan yang ditemukan meliputi adanya pergeseran prediksi dari kelas mayoritas ke kelas minoritas yang menyebabkan "
        "sedikit penurunan pada akurasi agregat, serta kebutuhan penyesuaian hyperparameter (seperti penambahan bobot loss berimbang "
        "atau layer attention) untuk eksperimen lanjutan."
    )
    atur_format_paragraf(p_kes_b, space_after=6)

    doc.save(OUT_PATH)
    print("Dokumen laporan_eksperimen_2.docx berhasil disimpan di:", OUT_PATH)


if __name__ == "__main__":
    main()
