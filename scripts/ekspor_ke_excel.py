"""Kompilasi rekapitulasi seluruh eksperimen ke dalam berkas Excel (3 Sheet):
Sheet 1: Eksperimen 1_Klasik (DT)
Sheet 2: Eksperimen 2_Deep Learning (LSTM)
Sheet 3: Eksperimen 3_Transfer Learning (Template untuk rekan kelompok)
Jalankan dari folder utama proyek:  python scripts/ekspor_ke_excel.py
"""
import os
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

CSV_EXP1 = os.path.join("hasil", "eksperimen_skenario", "ringkasan_skenario.csv")
CSV_EXP2 = os.path.join("hasil", "eksperimen_deep_learning", "ringkasan_deep_learning.csv")
EXCEL_OUT = os.path.join("hasil", "rekapitulasi_eksperimen_absa.xlsx")


def format_sheet(ws, judul_sheet):
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    for col_idx, col in enumerate(ws.columns, 1):
        cell_header = ws.cell(row=1, column=col_idx)
        cell_header.fill = header_fill
        cell_header.font = header_font
        cell_header.alignment = align_center

        max_len = len(str(cell_header.value or ""))
        for cell in col:
            cell.border = thin_border
            if cell.row > 1:
                if isinstance(cell.value, float):
                    cell.number_format = "0.000"
                    cell.alignment = align_center
                elif isinstance(cell.value, int):
                    cell.alignment = align_center
                else:
                    cell.alignment = align_left
                max_len = max(max_len, len(str(cell.value or "")))
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)


def main():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Hapus default sheet kosong

    # ----- Sheet 1: Eksperimen 1 Klasik -----
    if os.path.exists(CSV_EXP1):
        df1 = pd.read_csv(CSV_EXP1, encoding="utf-8-sig")
        df1 = df1.rename(columns={
            "tugas": "Tugas",
            "skenario": "Skenario Data",
            "model": "Model",
            "fitur": "Ekstraksi Fitur",
            "akurasi": "Akurasi",
            "akurasi_std": "Std Akurasi",
            "macro_f1": "Macro F1",
            "macro_f1_std": "Std Macro F1",
            "f1_netral": "F1-Score Netral"
        })
        ws1 = wb.create_sheet(title="Eksperimen 1_Klasik (DT)")
        ws1.append(list(df1.columns))
        for row in df1.itertuples(index=False):
            ws1.append(list(row))
        format_sheet(ws1, "Eksperimen 1_Klasik (DT)")
        print("Sheet 1 (Klasik) berhasil disusun.")
    else:
        print(f"Peringatan: {CSV_EXP1} belum ditemukan.")

    # ----- Sheet 2: Eksperimen 2 Deep Learning -----
    if os.path.exists(CSV_EXP2):
        df2 = pd.read_csv(CSV_EXP2, encoding="utf-8-sig")
        df2 = df2.rename(columns={
            "tugas": "Tugas",
            "skenario": "Skenario Data",
            "model": "Model",
            "embedding": "Embedding",
            "akurasi": "Akurasi",
            "akurasi_std": "Std Akurasi",
            "macro_f1": "Macro F1",
            "macro_f1_std": "Std Macro F1",
            "f1_netral": "F1-Score Netral"
        })
        ws2 = wb.create_sheet(title="Eksperimen 2_Deep Learning")
        ws2.append(list(df2.columns))
        for row in df2.itertuples(index=False):
            ws2.append(list(row))
        format_sheet(ws2, "Eksperimen 2_Deep Learning")
        print("Sheet 2 (Deep Learning) berhasil disusun.")
    else:
        print(f"Peringatan: {CSV_EXP2} belum ditemukan.")

    # ----- Sheet 3: Eksperimen 3 Transfer Learning (Template) -----
    template_cols = [
        "Tugas", "Skenario Data", "Model", "Pre-trained Backbone",
        "Akurasi", "Std Akurasi", "Macro F1", "Std Macro F1", "F1-Score Netral", "Catatan Evaluasi"
    ]
    template_rows = [
        ["sentimen", "Data Asli", "BERT / IndoBERT", "indobenchmark/indobert-base-punc", "", "", "", "", "", "Diisi rekan kelompok"],
        ["sentimen", "Data Augmentasi", "BERT / IndoBERT", "indobenchmark/indobert-base-punc", "", "", "", "", "", "Diisi rekan kelompok"],
        ["aspek", "Data Asli", "BERT / IndoBERT", "indobenchmark/indobert-base-punc", "", "", "", "", "", "Diisi rekan kelompok"],
        ["aspek", "Data Augmentasi", "BERT / IndoBERT", "indobenchmark/indobert-base-punc", "", "", "", "", "", "Diisi rekan kelompok"]
    ]
    ws3 = wb.create_sheet(title="Eksperimen 3_Transfer Learning")
    ws3.append(template_cols)
    for r in template_rows:
        ws3.append(r)
    format_sheet(ws3, "Eksperimen 3_Transfer Learning")
    print("Sheet 3 (Transfer Learning Template) berhasil disusun.")

    wb.save(EXCEL_OUT)
    print(f"\nBerkas Excel rekapitulasi berhasil disimpan di: {EXCEL_OUT}")


if __name__ == "__main__":
    main()

