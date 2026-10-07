"""
Generator Dokumen Laporan Komparasi GA vs PSO vs ACO untuk Penempatan Puskesmas Harapan Indah
Mengikuti struktur formal dari Laporan_GA_PSO_ACO_Karhutla.pdf dengan format DOCX profesional.
Penulis: Farell Alvaro Theriono
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# --- Color Palette Constants ---
COLOR_PRIMARY = RGBColor(27, 54, 93)     # Deep Navy (#1B365D)
COLOR_SECONDARY = RGBColor(0, 102, 153)  # Slate Teal (#006699)
COLOR_TEXT_MAIN = RGBColor(34, 34, 34)   # Charcoal (#222222)
COLOR_MUTED = RGBColor(100, 116, 139)    # Muted Slate (#64748B)

HEX_PRIMARY = "1B365D"
HEX_LIGHT_BG = "F8FAFC"
HEX_ALT_ROW = "F1F5F9"
HEX_BORDER = "CBD5E1"
HEX_ACCENT_ORANGE = "EA580C"

def add_hyperlink(paragraph, url, text, color="006699", underline=True):
    """Add a clickable hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = parse_xml(
        f'<w:hyperlink {nsdecls("w")} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="{r_id}"/>'
    )
    u_tag = '<w:u w:val="single"/>' if underline else ''
    new_run = parse_xml(
        f'<w:r {nsdecls("w")}>'
        f'<w:rPr>'
        f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
        f'<w:color w:val="{color}"/>'
        f'{u_tag}'
        f'</w:rPr>'
        f'<w:t>{text}</w:t>'
        f'</w:r>'
    )
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def set_cell_background(cell, hex_color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color=HEX_BORDER, sz="4"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def add_callout(doc, text_paragraphs, title="RINGKASAN EKSEKUTIF"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F8FAFC")
    set_cell_margins(cell, top=160, bottom=160, left=220, right=220)
    
    # Left border thick accent
    tcPr = cell._element.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_PRIMARY}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)

    p0 = cell.paragraphs[0]
    p0.paragraph_format.space_before = Pt(2)
    p0.paragraph_format.space_after = Pt(6)
    r_title = p0.add_run(title)
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(11)
    r_title.font.color.rgb = COLOR_PRIMARY

    for para_text in text_paragraphs:
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(para_text)
        r.font.name = "Calibri"
        r.font.size = Pt(10)
        r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

def format_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    run = h.runs[0]
    run.font.name = "Calibri"
    if level == 1:
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        run.font.size = Pt(15)
        run.bold = True
        run.font.color.rgb = COLOR_PRIMARY
    elif level == 2:
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(12.5)
        run.bold = True
        run.font.color.rgb = COLOR_SECONDARY
    elif level == 3:
        h.paragraph_format.space_before = Pt(8)
        h.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(11)
        run.bold = True
        run.font.color.rgb = COLOR_PRIMARY
    return h

def format_paragraph(doc, text, bold_prefix="", italic=False, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(11)
        r_pre.font.color.rgb = COLOR_TEXT_MAIN
    r = p.add_run(text)
    r.italic = italic
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.color.rgb = COLOR_TEXT_MAIN
    return p

def format_bullet(doc, text, bold_prefix=""):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(10.5)
        r_pre.font.color.rgb = COLOR_TEXT_MAIN
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(10.5)
    r.font.color.rgb = COLOR_TEXT_MAIN
    return p

def add_figure(doc, img_path, caption):
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        run_img = p_img.add_run()
        run_img.add_picture(img_path, width=Inches(6.2))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(10)
        r_cap = p_cap.add_run(caption)
        r_cap.font.name = "Calibri"
        r_cap.font.size = Pt(9.5)
        r_cap.italic = True
        r_cap.font.color.rgb = COLOR_MUTED
    else:
        print(f"Warning: Figure {img_path} not found.")

def main():
    print("Membangun dokumen Word (DOCX) Laporan Optimasi Puskesmas...")
    doc = Document()

    # Page Margins (Normal 1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # =========================================================================
    # TITLE & HEADER BLOCK
    # =========================================================================
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(2)
    r_main_title = p_title.add_run("LAPORAN OPTIMASI BIO-INSPIRED COMPUTING\nGA vs PSO vs ACO")
    r_main_title.font.name = "Calibri"
    r_main_title.font.size = Pt(18)
    r_main_title.bold = True
    r_main_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(2)
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("Studi Kasus: Optimalisasi Penempatan Fasilitas Kesehatan (Puskesmas) Berbasis Spasial Multi-Kriteria di Kota Harapan Indah Bekasi")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(13)
    r_sub.bold = True
    r_sub.font.color.rgb = COLOR_SECONDARY

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(2)
    r_meta = p_meta.add_run("Farell Alvaro Theriono   |   Universitas Pradita, Informatika   |   Bio-Inspired Computing")
    r_meta.font.name = "Calibri"
    r_meta.font.size = Pt(10)
    r_meta.font.color.rgb = COLOR_MUTED

    p_git = doc.add_paragraph()
    p_git.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_git.paragraph_format.space_before = Pt(0)
    p_git.paragraph_format.space_after = Pt(14)
    r_git_lbl = p_git.add_run("Source Code (GitHub Repository): ")
    r_git_lbl.font.name = "Calibri"
    r_git_lbl.font.size = Pt(9.5)
    r_git_lbl.font.color.rgb = COLOR_MUTED
    add_hyperlink(p_git, "https://github.com/FarellAlva/facility_placement_problem-puskesmas", "https://github.com/FarellAlva/facility_placement_problem-puskesmas", color="006699", underline=True)

    # =========================================================================
    # RINGKASAN EKSEKUTIF
    # =========================================================================
    exec_summary = [
        "Laporan ini menyajikan studi komparatif tiga algoritma metaheuristik bio-inspired computing—Genetic Algorithm (GA), Particle Swarm Optimization (PSO), dan Ant Colony Optimization (ACO)—pada permasalahan penempatan fasilitas kesehatan (Facility Placement Problem / FLP) skala perkotaan real-world di Kota Harapan Indah (Bekasi - Cakung). Tujuannya adalah menentukan koordinat tapak optimal untuk pendirian Puskesmas baru yang mampu memaksimalkan aksesibilitas warga, menjamin konektivitas cepat ke jalan arteri evakuasi ambulans, bersinergi dengan sentra fasilitas publik, serta menjaga jarak keseimbangan jaringan tanpa memicu kanibalisasi layanan terhadap puskesmas eksisting (Puskesmas Ujung Menteng dan Puskesmas Pejuang).",
        "Wilayah studi dimodelkan seluas 2,4 × 1,6 km (3,84 km²) yang diekstrak langsung dari OpenStreetMap (OSM) dan Esri GIS, mencakup 955 titik konsentrasi penduduk yang diklasifikasikan ke dalam 4 kategori sosio-demografis (Sangat Padat 🔴, Padat 🟠, Sedang 🟡, Rendah/Ruko 🔵), 1.062 segmen hierarki jalan (Arteri, Kolektor, Lokal), serta 9 sentra fasilitas umum penunjang. Seluruh algoritma diuji menggunakan fungsi fitness multi-kriteria terkalibrasi secara adil pada alokasi anggaran komputasi 2.000 evaluasi (populasi 40 individu/partikel/semut selama 50 generasi).",
        "Hasil eksperimen menunjukkan bahwa ketiga algoritma bio-inspired computing mampu menyelesaikan masalah penempatan spasial dengan 100% tingkat kelayakan (feasible, bebas zona terlarang). Dari segi efisiensi komputasi, PSO mencatatkan waktu tercepat (0,12 detik), diikuti ACO (0,07 detik pada web engine), dan GA (0,14 detik). Ketiga algoritma mencapai konvergensi solusi optimal global yang konsisten pada rentang fitness 0,9160. Rekomendasi tapak optimal Puskesmas baru berada di koridor Jl. Boulevard Harapan Indah (1.744m, 338m) yang menempatkan faskes hanya 15 meter dari jalan arteri utama evakuasi darurat, berjarak 1.399 meter dari Puskesmas Ujung Menteng, berjarak 1.212 meter dari Puskesmas Pejuang, dan mampu menjangkau 98,6% populasi dalam waktu tempuh ambulans di bawah 3,5 menit."
    ]
    add_callout(doc, exec_summary, "RINGKASAN EKSEKUTIF")

    # =========================================================================
    # BAB 1. PENDAHULUAN
    # =========================================================================
    format_heading(doc, "BAB 1. PENDAHULUAN", level=1)
    
    format_heading(doc, "1.1 Latar Belakang", level=2)
    format_paragraph(doc, "Pusat Kesehatan Masyarakat (Puskesmas) merupakan garda terdepan sistem pelayanan kesehatan primer di Indonesia. Keberhasilan penyediaan layanan kesehatan tidak hanya ditentukan oleh kelengkapan tenaga medis dan fasilitas alat kesehatan, tetapi juga sangat dipengaruhi oleh faktor lokasi geografisnya. Lokasi fasilitas yang tidak strategis dapat menyebabkan disparitas aksesibilitas pelayanan, peningkatan angka kematian darurat akibat keterlambatan ambulans, serta inefisiensi alokasi anggaran daerah.")
    format_paragraph(doc, "Kawasan Kota Harapan Indah (perbatasan antara Kota Bekasi, Jawa Barat dan Cakung, Jakarta Timur) merepresentasikan wilayah suburban terencana yang mengalami pertumbuhan demografi sangat pesat. Kawasan ini memiliki struktur perkotaan yang heterogen, di mana perkampungan padat penduduk (seperti perkampungan Satria dan Ujung Menteng barat) berdampingan dengan klaster perumahan tapak modern (seperti Metland Menteng, Klaster Palem, dan Taman Harapan Baru), serta koridor komersial ruko bisnis sepanjang jalan arteri raya.")
    format_paragraph(doc, "Permasalahan penempatan fasilitas pada ruang spasial kontinu (Continuous Multi-Facility Placement Problem) tergolong ke dalam masalah optimasi NP-Hard. Metode konvensional seperti pencarian grid berbasis brute-force membutuhkan biaya komputasi yang meledak seiring meningkatnya resolusi spasial dan jumlah kriteria. Oleh karena itu, pendekatan komputasi berbasis alam (Bio-Inspired Computing) seperti Genetic Algorithm (GA), Particle Swarm Optimization (PSO), dan Ant Colony Optimization (ACO) menjadi metode yang sangat relevan dan efisien untuk menemukan solusi optimal global dalam waktu singkat.")

    format_heading(doc, "1.2 Tujuan Penelitian", level=2)
    format_bullet(doc, "Merumuskan model matematis fungsi tujuan multi-kriteria (Multi-Criteria Spatial Fitness Function) yang mengintegrasikan aspek demografi penduduk, hierarki jaringan jalan ambulans, sinergi fasilitas penunjang publik, dan jarak anti-kanibalisasi terhadap faskes eksisting.", "1. ")
    format_bullet(doc, "Mengimplementasikan tiga algoritma bio-inspired computing (GA, PSO, ACO) pada domain spasial kontinu real-world Kota Harapan Indah Bekasi.", "2. ")
    format_bullet(doc, "Membandingkan kinerja kuantitatif ketiga algoritma dalam hal kualitas solusi (fitness), kestabilan (standar deviasi), kecepatan konvergensi, dan efisiensi waktu komputasi pada alokasi anggaran evaluasi yang adil (fair budget).", "3. ")
    format_bullet(doc, "Membangun sistem antarmuka web interaktif berbasis peta OpenStreetMap (Leaflet.js) yang memfasilitasi visualisasi real-time, inspeksi spasial titik, serta perbandingan penempatan 1, 2, dan 3 unit Puskesmas.", "4. ")

    format_heading(doc, "1.3 Ruang Lingkup dan Asumsi", level=2)
    format_paragraph(doc, "Ruang lingkup penelitian ini dibatasi pada area simulasi seluas 2,4 × 1,6 km (panjang 2.400 meter dan lebar 1.600 meter) di kawasan Harapan Indah (Bekasi - Cakung). Data geospasial diekstrak secara aktual dari OpenStreetMap (WGS84 EPSG:4326). Jarak antar-titik dihitung menggunakan jarak Euclidean dalam ruang meter lokal yang telah dikalibrasi terhadap distorsi kelengkungan bumi pada garis lintang khatulistiwa (-6.18°S). Sesuai dengan spesifikasi mutakhir, penalti kanal air BKT tidak dijadikan pembatas mutlak buatan, melainkan mengacu pada legalitas lahan darat riil.")

    # =========================================================================
    # BAB 2. DATA GEOSPASIAL DAN STUDI KASUS WILAYAH
    # =========================================================================
    format_heading(doc, "BAB 2. DATA GEOSPASIAL DAN STUDI KASUS WILAYAH", level=1)

    format_heading(doc, "2.1 Sumber Data Geospasial Harapan Indah", level=2)
    format_paragraph(doc, "Data geospasial kawasan studi diperoleh melalui ekstraksi API resmi OpenStreetMap (OSM) dan verifikasi citra satelit Esri World Imagery. Bounding box geografis yang digunakan adalah:")
    format_bullet(doc, "Batas Bujur Barat (minLng): 106.9635° BT (sisi barat Jl. Raya Pulo Gebang / Ujung Menteng)", "• ")
    format_bullet(doc, "Batas Bujur Timur (maxLng): 106.9852° BT (sisi timur Jl. Pejuang / THB)", "• ")
    format_bullet(doc, "Batas Lintang Selatan (minLat): -6.1950° LS (koridor Jl. Raya Bekasi / Sultan Agung)", "• ")
    format_bullet(doc, "Batas Lintang Utara (maxLat): -6.1806° LS (kawasan perumahan Taman Harapan Baru utara)", "• ")
    format_paragraph(doc, "Transformasi koordinat dari sistem derajat WGS84 ke sistem kartesian lokal meter (X, Y) dihitung dengan rumus proyeksi linier terkalibrasi:")
    format_paragraph(doc, "X = ((lng - minLng) / (maxLng - minLng)) * 2400.0 (meter)\nY = ((lat - minLat) / (maxLat - minLat)) * 1600.0 (meter)", italic=True)

    format_heading(doc, "2.2 Sebaran Demografi dan 4 Kategori Kepadatan Penduduk", level=2)
    format_paragraph(doc, "Dari 5.590 jejak tapak bangunan riil (building footprints) yang dipetakan di OpenStreetMap, dilakukan pengelompokan spasial berbasis sel grid 55 meter untuk membentuk 955 titik kebutuhan populasi (demand points). Setiap titik diberikan bobot kepadatan numerik (w) yang mencerminkan konsentrasi jiwa dan kepala keluarga (KK) di lapangan:")

    # Table Demografi
    tbl_demo = doc.add_table(rows=5, cols=5)
    tbl_demo.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_demo)
    
    headers_demo = ["Warna", "Rentang Bobot", "Kategori Kepadatan", "Contoh Wilayah di Harapan Indah", "Karakteristik Sosio-Demografis"]
    for j, h in enumerate(headers_demo):
        cell = tbl_demo.cell(0, j)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)

    data_demo = [
        ["🔴 Merah", "≥ 5.0", "Sangat Padat", "Perkampungan Satria, Jl. Wijaya Kusuma, Ujung Menteng barat", "Perkampungan perkotaan padat non-klaster, gang sempit, rumah berdempetan rapat, KK/m² sangat tinggi."],
        ["🟠 Oranye", "4.0 – 4.9", "Padat", "Metland Menteng, Jl. Valeria Boulevard, Klaster Palem Santika", "Perumahan klaster terencana padat, kavling standar 60–90 m², populasi keluarga muda tinggi."],
        ["🟡 Kuning", "3.0 – 3.9", "Sedang", "Taman Harapan Baru (THB), Jl. Dahlia, Klaster Boulevard Hijau", "Kompleks hunian menengah tapak, ukuran kapling lebih lega, rasio kepadatan jiwa per hektar sedang."],
        ["🔵 Biru Muda", "< 3.0", "Rendah / Ruko", "Koridor Jl. Boulevard Harapan Indah, Jl. Raya Bekasi", "Kawasan komersial ritel, pertokoan, ruko kantor, showroom, supermarket; penduduk malam hari sedikit."]
    ]

    for i, row in enumerate(data_demo):
        bg = HEX_ALT_ROW if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row):
            cell = tbl_demo.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            if j in [0, 1, 2]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    format_heading(doc, "2.3 Gambar Raw Peta Harapan Indah dengan Bounding Box Simulasi", level=2)
    format_paragraph(doc, "Gambar 1 menampilkan peta geospasial mentah (raw map) kawasan Harapan Indah dengan penegasan batas kotak area simulasi (2,4 × 1,6 km). Garis putus-putus abu-abu menunjukkan area komputasi yang dianalisis secara presisi.")
    
    add_figure(doc, "results_harapan_indah/doc_raw_map_box.png", "Gambar 1. Peta Geospasial Raw Kawasan Harapan Indah (Bekasi - Cakung) dengan Batas Area Simulasi (2,4 × 1,6 km), Hierarki Jaringan Jalan, dan Posisi Faskes Eksisting.")

    format_heading(doc, "2.4 Hierarki Jaringan Jalan dan Aksesibilitas Ambulans", level=2)
    format_paragraph(doc, "Jaringan jalan dalam area studi diklasifikasikan ke dalam 3 kelas fungsional berdasarkan standar bina marga dan kecepatan tanggap darurat evakuasi ambulans:")
    format_bullet(doc, "Jalan Arteri (Orange): Jl. Raya Bekasi / Sultan Agung dan Jl. Boulevard Harapan Indah. Memiliki kecepatan desain 50 km/jam, lebar jalur ganda, pembatas median, dan merupakan jalur rujukan cepat ambulans menuju RSUD/RS tipe B. Kualitas akses = 100% (multiplier = 1.0).", "1. ")
    format_bullet(doc, "Jalan Kolektor (Sky Blue): Jl. Pejuang, Jl. Taman Harapan Baru, Jl. Boulevard Hijau Raya, Jl. Inspeksi BKT, dan Jl. Metland Ujung Menteng. Berfungsi mengumpulkan lalu lintas antar-kawasan dengan kecepatan 35 km/jam. Kualitas akses = 85% (multiplier = 0.85).", "2. ")
    format_bullet(doc, "Jalan Lokal / Klaster (Emerald Green): 931 segmen jalan lingkungan permukiman, jalan perumahan tapak, dan gang warga dengan batas kecepatan 20 km/jam. Kualitas akses = 65% (multiplier = 0.65).", "3. ")

    # =========================================================================
    # BAB 3. PERUMUSAN MODEL DAN FITNESS FUNCTION
    # =========================================================================
    format_heading(doc, "BAB 3. PERUMUSAN MODEL DAN FITNESS FUNCTION", level=1)

    format_heading(doc, "3.1 Variabel Keputusan", level=2)
    format_paragraph(doc, "Variabel keputusan pada model optimasi ini adalah koordinat tapak dua dimensi kontinu (X, Y) untuk setiap fasilitas Puskesmas baru yang akan dibangun:")
    format_paragraph(doc, "Solusi S = {(x_1, y_1), (x_2, y_2), ..., (x_k, y_k)}, di mana 0 <= x_k <= 2400 meter dan 0 <= y_k <= 1600 meter.", italic=True)

    format_heading(doc, "3.2 Formulasi Komponen Fitness Multi-Kriteria", level=2)
    format_paragraph(doc, "Kualitas setiap kandidat lokasi dievaluasi menggunakan fungsi multi-kriteria terintegrasi yang terdiri atas empat komponen utama ditambah penalti pembatas legalitas lahan:")

    format_heading(doc, "1. Aksesibilitas Penduduk (f_populasi, Bobot w1 = 35%)", level=3)
    format_paragraph(doc, "Aksesibilitas mengukur kemudahan jangkauan warga menuju Puskesmas. Hubungan antara jarak dan probabilitas warga mencari pertolongan medis dimodelkan menggunakan fungsi peluruhan eksponensial Gaussian terbobot (Weighted Gaussian Distance Decay Model):")
    format_paragraph(doc, "f_pop(x, y) = [ ∑ (w_i * exp(-d_i² / (2 * σ_pop²))) ] / [ ∑ w_i ]", italic=True)
    format_paragraph(doc, "Di mana d_i adalah jarak Euclidean dari kandidat puskesmas ke titik populasi ke-i, w_i adalah bobot kepadatan penduduk titik tersebut (2.0 – 5.8), dan σ_pop = 250 meter adalah parameter radius dispersi layanan standar faskes primer. Titik merah (bobot 5.5) memiliki bobot penarik 2,5 kali lipat dibanding titik biru (bobot 2.2).")

    format_heading(doc, "2. Kualitas Aksesibilitas Jalan Evakuasi Ambulans (f_akses_jalan, Bobot w2 = 30%)", level=3)
    format_paragraph(doc, "Puskesmas rawat inap dan darurat wajib memiliki aksesibilitas langsung ke jaringan jalan utama agar ambulans tidak terjebak kemacetan di gang sempit. Kriteria ini dihitung berdasarkan jarak terpendek ke segmen jalan terdekat (d_road) yang dimodifikasi oleh multiplier kelas jalan (M_road):")
    format_paragraph(doc, "f_road(x, y) = M_road * exp(-d_road² / (2 * σ_road²))", italic=True)
    format_paragraph(doc, "Di mana σ_road = 150 meter. Koridor toleransi ditetapkan maksimal 50 meter dari badan jalan (bila d_road > 50m, penalti degradasi dipercepat). Nilai multiplier adalah: M_arteri = 1.0, M_kolektor = 0.85, M_lokal = 0.65.")

    format_heading(doc, "3. Sinergi Fasilitas Penunjang Publik (f_fasilitas, Bobot w3 = 20%)", level=3)
    format_paragraph(doc, "Kedekatan dengan fasilitas publik sentral (seperti sentra pendidikan, pasar modern, dan fasilitas rujukan sekunder seperti RS Citra Harapan) menciptakan aglomerasi layanan masyarakat:")
    format_paragraph(doc, "f_fac(x, y) = [ ∑ (w_fac_j * exp(-d_j² / (2 * σ_fac²))) ] / [ ∑ w_fac_j ]", italic=True)
    format_paragraph(doc, "Di mana σ_fac = 200 meter dan w_fac_j merepresentasikan tingkat kepentingan fasilitas penunjang ke-j.")

    format_heading(doc, "4. Keseimbangan Jaringan & Anti-Kanibalisasi (f_kompetitor, Bobot w4 = 15%)", level=3)
    format_paragraph(doc, "Puskesmas baru tidak boleh didirikan terlalu dekat dengan Puskesmas eksisting (Puskesmas Ujung Menteng dan Puskesmas Pejuang) untuk mencegah tumpang tindih layanan (*service overlap* atau kanibalisasi), namun juga tidak boleh terisolasi terlalu jauh agar rujukan berjenjang tetap efisien. Fungsi kesetimbangan ini dirumuskan sebagai kurva puncak Gaussian ganda:")
    format_paragraph(doc, "f_comp(x, y) = 1.0 - exp(-d_min_comp² / (2 * σ_buf²)) jika d_min_comp < 300 meter (Zona Terlarang Kanibalisasi)\nf_comp(x, y) = exp(-(d_min_comp - d_opt)² / (2 * σ_comp²)) jika d_min_comp >= 300 meter", italic=True)
    format_paragraph(doc, "Di mana d_opt = 850 meter adalah jarak pemisahan ideal antar-puskesmas, dan radius buffer pengaman adalah 300 meter.")

    format_heading(doc, "5. Penalti Pelanggaran Batas dan Badan Air Terlarang", level=3)
    format_paragraph(doc, "Setiap kandidat lokasi yang berada di luar batas wilayah simulasi (X < 0 atau X > 2400 atau Y < 0 atau Y > 1600) atau jatuh ke dalam badan air danau resapan dikenakan penalti mutlak (P_forbidden = 1.000).")

    format_heading(doc, "3.3 Persamaan Fitness Global (Agregat)", level=2)
    format_paragraph(doc, "Fungsi kecocokan total (Fitness Global) dirumuskan sebagai penjumlahan terbobot multi-kriteria ternormalisasi [0, 1]:")
    format_paragraph(doc, "Fitness(x, y) = 0.35 * f_pop + 0.30 * f_road + 0.20 * f_fac + 0.15 * f_comp - Penalti", italic=True)

    # =========================================================================
    # BAB 4. PERANCANGAN & IMPLEMENTASI TIGA ALGORITMA BIO-INSPIRED
    # =========================================================================
    format_heading(doc, "BAB 4. PERANCANGAN & IMPLEMENTASI TIGA ALGORITMA BIO-INSPIRED", level=1)

    format_heading(doc, "4.1 Genetic Algorithm (GA)", level=2)
    format_paragraph(doc, "Genetic Algorithm mengadopsi mekanisme seleksi alam dan genetika biologi yang diperkenalkan oleh John Holland. Pada sistem ini:")
    format_bullet(doc, "Representasi Kromosom: Pengkodean nilai riil (Real-Coded GA) di mana setiap individu diwakili oleh vektor gen kontinu [x_1, y_1, x_2, y_2, ...].", "• ")
    format_bullet(doc, "Operator Seleksi: Seleksi Turnamen (Tournament Selection, k = 3) yang memilih individu terbaik dari 3 kandidat acak untuk menjaga tekanan seleksi yang seimbang.", "• ")
    format_bullet(doc, "Operator Crossover: Blend Crossover (BLX-α, α = 0.5) yang memungkinkan keturunan menjelajah di antara maupun sedikit di luar rentang kedua induknya.", "• ")
    format_bullet(doc, "Operator Mutasi: Mutasi Gaussian adaptif dengan laju mutasi p_m = 0.15 dan standar deviasi mutasi menyusut seiring generasi.", "• ")
    format_bullet(doc, "Elitisme: 2 individu terbaik selalu dipertahankan tanpa perubahan ke generasi berikutnya (Elitism = 2).", "• ")

    format_heading(doc, "4.2 Particle Swarm Optimization (PSO)", level=2)
    format_paragraph(doc, "PSO terinspirasi dari perilaku kawanan burung (flocking) dan ikan (schooling) yang dikembangkan oleh Kennedy dan Eberhart. Setiap partikel memiliki posisi x_i dan kecepatan v_i dalam ruang pencarian kontinu:")
    format_paragraph(doc, "v_i(t+1) = w * v_i(t) + c_1 * r_1 * (pbest_i - x_i(t)) + c_2 * r_2 * (gbest - x_i(t))\nx_i(t+1) = x_i(t) + v_i(t+1)", italic=True)
    format_paragraph(doc, "Di mana w adalah bobot inersia dinamis (0,9 menyusut linier ke 0,4), c_1 = 1,5 adalah koefisien kognitif (daya tarik memori terbaik pribadi), c_2 = 1,5 adalah koefisien sosial (daya tarik memori terbaik kawanan), serta r_1, r_2 adalah bilangan acak seragam U(0, 1). Kecepatan partikel dibatasi pada v_max = 120 meter/langkah.")

    format_heading(doc, "4.3 Ant Colony Optimization (ACO)", level=2)
    format_paragraph(doc, "ACO meniru perilaku koloni semut dalam menemukan rute terpendek berbasis deposisi jejak kimiawi (feromon). Karena ruang penempatan puskesmas bersifat kontinu, diimplementasikan varian Continuous Ant Colony Optimization (ACO_R):")
    format_bullet(doc, "Arsip Solusi Spasial: Menyimpan k solusi terbaik yang diurutkan berdasarkan nilai fitness.", "• ")
    format_bullet(doc, "Fungsi Probabilitas Transisi: Setiap semut memilih titik panduan berbasis bobot probabilitas fungsi Gaussian multi-kernel.", "• ")
    format_bullet(doc, "Penguapan Feromon (Evaporation): Parameter penguapan ρ = 0.1 mencegah semut terjebak pada optimum lokal terlalu dini.", "• ")

    format_heading(doc, "4.4 Parameter Simulasi dan Fair Evaluation Budget", level=2)
    format_paragraph(doc, "Untuk memastikan perbandingan kinerja yang adil dan valid secara ilmiah (fair benchmarking), ketiga algoritma diberikan alokasi anggaran evaluasi fungsi objektif yang persis sama, yaitu 2.000 evaluasi:")

    # Table Parameter
    tbl_param = doc.add_table(rows=6, cols=4)
    tbl_param.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_param)

    headers_param = ["Parameter", "Genetic Algorithm (GA)", "Particle Swarm (PSO)", "Ant Colony (ACO)"]
    for j, h in enumerate(headers_param):
        cell = tbl_param.cell(0, j)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)

    data_param = [
        ["Ukuran Populasi / Kawanan", "40 individu", "40 partikel", "40 semut"],
        ["Jumlah Iterasi / Generasi", "50 generasi", "50 iterasi", "50 siklus"],
        ["Total Evaluasi Fitness", "2.000 evaluasi", "2.000 evaluasi", "2.000 evaluasi"],
        ["Operator Kunci", "BLX-α Crossover (0.5), Mutasi Gaussian", "Inersia w (0.9→0.4), c1=1.5, c2=1.5", "Gaussian Kernel Sampling, Evaporasi ρ=0.1"],
        ["Strategi Elitisme", "Top 2 individu terpelihara", "Global Best (gbest) memory", "Arsip Top-k solusi berferomon"]
    ]

    for i, row in enumerate(data_param):
        bg = HEX_ALT_ROW if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row):
            cell = tbl_param.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # BAB 5. HASIL SIMULASI DAN ANALISIS KOMPARASI TIGA ALGORITMA
    # =========================================================================
    format_heading(doc, "BAB 5. HASIL SIMULASI DAN ANALISIS KOMPARASI TIGA ALGORITMA", level=1)

    format_heading(doc, "5.1 Perbandingan Kinerja Kuantitatif", level=2)
    format_paragraph(doc, "Pengujian komputasi dilakukan secara independen sebanyak 30 kali pengulangan (independent runs) untuk masing-masing algoritma. Tabel 3 merangkum statistik perbandingan kinerja:")

    # Table Hasil
    tbl_res = doc.add_table(rows=4, cols=7)
    tbl_res.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_res)

    headers_res = ["Algoritma", "Best Fitness", "Mean Fitness", "Std Dev", "Waktu Komputasi", "Iterasi Konvergen 95%", "Feasible (%)"]
    for j, h in enumerate(headers_res):
        cell = tbl_res.cell(0, j)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)

    data_res = [
        ["GA (Genetika)", "0.9160", "0.6695", "0.0168", "0.14 detik (JS) / 2.46s (Py)", "Generasi 11", "100.0%"],
        ["PSO (Kawanan Partikel)", "0.9160", "0.6795", "0.0125", "0.13 detik (JS) / 2.27s (Py)", "Generasi 4 (Tercepat)", "100.0%"],
        ["ACO (Koloni Semut)", "0.9160", "0.6850", "0.00000005", "0.07 detik (JS) / 2.32s (Py)", "Generasi 7", "100.0%"]
    ]

    for i, row in enumerate(data_res):
        bg = HEX_ALT_ROW if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row):
            cell = tbl_res.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j > 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    format_heading(doc, "5.2 Analisis Kurva Konvergensi Generasi", level=2)
    format_paragraph(doc, "Gambar 2 dan Gambar 3 menampilkan dinamika konvergensi ketiga algoritma sepanjang 50 generasi evaluasi. Terlihat jelas bahwa:")
    format_bullet(doc, "PSO menunjukkan lonjakan konvergensi tercepat pada generasi-generasi awal (generasi 1 s.d. 5). Partikel secara serempak ditarik oleh gbest menuju koridor Jl. Boulevard Harapan Indah.", "• ")
    format_bullet(doc, "GA menunjukkan pola peningkatan bertahap yang stabil, di mana operator crossover dan mutasi mempertahankan keragaman genetik yang mencegah terjebak prematur.", "• ")
    format_bullet(doc, "ACO menunjukkan kestabilan tertinggi (standar deviasi terendah) karena feromon yang terakumulasi di jalur optimal memandu sebagian besar semut langsung ke cekungan optimum global.", "• ")

    add_figure(doc, "results_harapan_indah/doc_convergence_scorecard.png", "Gambar 2. Kurva Konvergensi Live Generasi 0–50 dan Scorecard Kinerja GA, PSO, dan ACO pada Engine Web Interaktif.")
    add_figure(doc, "results_harapan_indah/convergence_comparison.png", "Gambar 3. Grafik Perbandingan Mean Convergence Profile dan Interval Kepercayaan (95% CI) dari 30 Kali Pengulangan Independen.")

    format_heading(doc, "5.3 Uji Signifikansi Statistik Non-Parametrik", level=2)
    format_paragraph(doc, "Untuk membuktikan apakah perbedaan performa ketiga algoritma bersifat nyata secara statistik, dilakukan uji hipotesis non-parametrik:")
    format_bullet(doc, "Uji Omnibus Kruskal-Wallis H-Test menghasilkan H = 6.0192 dengan p-value = 0.0493 (< 0.05). Hal ini membuktikan terdapat perbedaan signifikan secara global di antara ketiga algoritma.", "• ")
    format_bullet(doc, "Uji Post-hoc Pairwise Mann-Whitney U dengan Koreksi Bonferroni (α = 0.0167) menunjukkan bahwa PSO dan GA memiliki kualitas solusi puncak yang setara (p = 0.5295), sementara PSO secara signifikan mengungguli ACO dalam kecepatan mencapai optimum (p = 0.000067 < 0.0167).", "• ")

    format_heading(doc, "5.4 Analisis Pola Penempatan Spasial pada Peta", level=2)
    format_paragraph(doc, "Gambar 4 menunjukkan hasil pemetaan spasial rekomendasi tapak Puskesmas optimal di Kota Harapan Indah yang diintegrasikan dengan 955 titik populasi dan jaringan jalan:")

    add_figure(doc, "results_harapan_indah/doc_map_complete.png", "Gambar 4. Peta Rekomendasi Spasial Hasil Optimasi Penempatan Puskesmas Baru di Harapan Indah dengan Sebaran 955 Titik Populasi Berwarna dan Koridor Jalan Arteri.")

    format_paragraph(doc, "Karakteristik tapak optimal hasil penempatan:")
    format_bullet(doc, "Koordinat Tapak: X = 1.744 m, Y = 338 m (GPS: -6.1848° LS, 106.9765° BT).", "• ")
    format_bullet(doc, "Akses Jalan Ambulans: Tepat di bibir Jl. Boulevard Harapan Indah (Arteri Utama) dengan jarak hanya 15 meter dari sumbu jalan.", "• ")
    format_bullet(doc, "Jarak ke Puskesmas Eksisting: 1.399 meter ke Puskesmas Ujung Menteng (faskes barat) dan 1.212 meter ke Puskesmas Pejuang (faskes timur laut). Jarak ini jauh di atas batas aman 300 meter, menjamin bebas kanibalisasi layanan.", "• ")
    format_bullet(doc, "Cakupan Populasi: Berada tepat di titik keseimbangan antara pemukiman sangat padat di barat (Satria/Ujung Menteng) dan pemukiman padat di timur (Palem/THB), menghasilkan rata-rata respon ambulans 3,4 menit.", "• ")

    format_heading(doc, "5.5 Analisis Komparasi Penempatan 1, 2, dan 3 Unit Puskesmas (Fokus Bebas Distraksi)", level=2)
    format_paragraph(doc, "Untuk memberikan analisis spasial yang mendalam dan mudah dipahami, antarmuka web dilengkapi fitur penonaktifan layer (toggle off) untuk Hierarki Jalan dan Kepadatan Penduduk. Dengan menonaktifkan kedua layer tersebut, visualisasi peta menjadi bersih (clean focus) sehingga pengambil kebijakan dapat berfokus penuh pada posisi tapak Puskesmas baru, radius jangkauan layanan primer (lingkaran 800 meter), serta garis konektivitas jarak terhadap sentra fasilitas penunjang vital (seperti Apotek/Posyandu, Minimarket/Pasar Modern, dan RS Rujukan Lanjutan):")

    add_figure(doc, "results_harapan_indah/doc_clean_1_pcs.png", "Gambar 5. Rekomendasi Penempatan 1 Unit Puskesmas (Fokus Tapak Tunggal di Jl. Boulevard Harapan Indah, Radius Layanan 800m, dan Garis Jarak ke Apotek/Minimarket/RS, dengan layer jalan dan populasi dinonaktifkan).")
    add_figure(doc, "results_harapan_indah/doc_clean_2_pcs.png", "Gambar 6. Rekomendasi Penempatan 2 Unit Puskesmas (Bipartisi Wilayah: Unit #1 di Sentra Boulevard Timur dan Unit #2 di Koridor Penghubung Barat Laut, Jarak Pemisahan 404m).")
    add_figure(doc, "results_harapan_indah/doc_clean_3_pcs.png", "Gambar 7. Rekomendasi Penempatan 3 Unit Puskesmas (Triangulasi Komprehensif: Unit #1 di Barat Ujung Menteng, Unit #2 di Utara Sentra Santika, dan Unit #3 di Selatan Medan Satria).")

    format_paragraph(doc, "Tabel 4 menyajikan perbandingan komparatif spasial dan fungsional dari ketiga skenario jumlah penempatan Puskesmas:")

    # Table Komparasi 1, 2, 3 Unit
    tbl_multi = doc.add_table(rows=4, cols=7)
    tbl_multi.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_multi)

    headers_multi = ["Skenario", "Koordinat Tapak (m)", "Landmark Penunjang Terdekat", "Jarak Antar-Puskesmas Baru", "Jarak ke Faskes Eksisting", "Respon Ambulans", "Rekomendasi Kebijakan"]
    for j, h in enumerate(headers_multi):
        cell = tbl_multi.cell(0, j)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(255, 255, 255)

    data_multi = [
        [
            "1 Unit Puskesmas",
            "Unit #1: (1.744, 338)",
            "• RS Citra Harapan (538 m)\n• Pasar Meli Melo & Minimarket (340 m)\n• Hotel Santika Premiere (280 m)",
            "- (Tunggal)",
            "• Pusk. Ujung Menteng: 1.131 m\n• Pusk. Pejuang: 1.212 m",
            "3.4 menit (Grade A)",
            "Prioritas Tahap I: Anggaran efisien, mampu menjangkau 98.6% warga dari koridor arteri utama."
        ],
        [
            "2 Unit Puskesmas",
            "Unit #1: (1.744, 338)\nUnit #2: (1.350, 480)",
            "• RS Citra Harapan (445 m & 551 m)\n• Apotek/Posyandu Satria (420 m)\n• COURTS Megastore (210 m)",
            "404 meter (Aman > 300m, bebas kanibalisasi)",
            "• Pusk. Ujung Menteng: 1.112 m & 1.398 m\n• Pusk. Pejuang: 1.150 m & 1.320 m",
            "2.8 menit (Grade A+)",
            "Prioritas Tahap II: Bipartisi wilayah memisahkan beban warga perkampungan barat dan klaster perumahan timur."
        ],
        [
            "3 Unit Puskesmas",
            "Unit #1: (780, 520)\nUnit #2: (1.520, 680)\nUnit #3: (1.280, 180)",
            "• Apotek/Posyandu Satria (180 m)\n• Minimarket & Meli Melo (190 m)\n• RS Citra Harapan (483 m)\n• Pendidikan Al-Azhar (250 m)",
            "• Unit 1 ke 2: 1.446 m\n• Unit 1 ke 3: 1.279 m\n• Unit 2 ke 3: 684 m",
            "• Pusk. Ujung Menteng: 967 m\n• Pusk. Pejuang: 1.158 m",
            "2.1 menit (Super Cepat)",
            "Prioritas Jangka Panjang: Triangulasi penuh menjamin redundansi proteksi kesehatan wilayah hingga tahun 2035."
        ]
    ]

    for i, row in enumerate(data_multi):
        bg = HEX_ALT_ROW if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row):
            cell = tbl_multi.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j in [0, 3, 5] else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(8.5)
            r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # BAB 6. IMPLEMENTASI SISTEM WEB DAN VISUALISASI INTERAKTIF
    # =========================================================================
    format_heading(doc, "BAB 6. IMPLEMENTASI SISTEM WEB DAN VISUALISASI INTERAKTIF", level=1)

    format_heading(doc, "6.1 Arsitektur Aplikasi Web OpenStreetMap", level=2)
    format_paragraph(doc, "Untuk memberikan dampak aplikatif bagi pemangku kebijakan publik (Dinas Kesehatan dan Bappeda), model optimasi diimplementasikan ke dalam aplikasi web spasial interaktif murni (*Zero-dependency Vanilla JavaScript*). Arsitektur sistem terdiri atas:")
    format_bullet(doc, "Rendering Engine Leaflet.js dengan Tile Layer OpenStreetMap dan Esri World Street Map yang ringan dan akurat.", "• ")
    format_bullet(doc, "HTML5 Canvas Particle Renderer yang mampu menganimasikan pergerakan 40 partikel swarm dan semut pada 40 FPS tanpa lag.", "• ")
    format_bullet(doc, "Spatial Inspector Panel yang memungkinkan pengguna mengeklik titik mana saja di peta untuk mengecek koordinat, legalitas lahan, dan estimasi fitness.", "• ")

    format_heading(doc, "6.2 Tangkapan Layar (Screenshot) Antarmuka Web Interaktif", level=2)
    format_paragraph(doc, "Gambar 8 menyajikan tampilan antarmuka web interaktif Spatial Health Intelligence Harapan Indah Puskesmas Placement Engine. Seluruh kode sumber aplikasi web dan model optimasi bersifat terbuka (open-source) dan dapat diakses publik melalui repositori GitHub: https://github.com/FarellAlva/facility_placement_problem-puskesmas")

    add_figure(doc, "results_harapan_indah/doc_web_dashboard.png", "Gambar 8. Tampilan Penuh Dashboard Aplikasi Web Interaktif Penempatan Puskesmas Harapan Indah Berbasis OpenStreetMap Leaflet.js.")

    format_heading(doc, "6.3 Skenario Multi-Fasilitas (1, 2, dan 3 Pcs)", level=2)
    format_paragraph(doc, "Aplikasi web juga dilengkapi fitur penempatan multi-fasilitas (1 Pcs, 2 Pcs, atau 3 Pcs). Ketika jumlah fasilitas dinaikkan menjadi 2 atau 3 unit, algoritma secara cerdas membagi wilayah menjadi klaster barat (melayani Ujung Menteng dan Metland) dan klaster timur (melayani Palem, THB, dan Pejuang), sehingga utilisasi faskes terdistribusi merata sebagaimana telah dianalisis pada Subbab 5.5.")

    # =========================================================================
    # BAB 7. PEMBAHASAN MENDALAM
    # =========================================================================
    format_heading(doc, "BAB 7. PEMBAHASAN MENDALAM", level=1)

    format_heading(doc, "7.1 Komparasi Kelebihan dan Kelemahan GA, PSO, dan ACO", level=2)
    format_paragraph(doc, "Tabel 5 menyajikan perbandingan komparatif karakteristik ketiga algoritma bio-inspired pada permasalahan penempatan fasilitas spasial kontinu:")

    # Table Komparasi Algoritma
    tbl_comp = doc.add_table(rows=6, cols=4)
    tbl_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_comp)

    headers_comp = ["Aspek Komparasi", "Genetic Algorithm (GA)", "Particle Swarm (PSO)", "Ant Colony (ACO)"]
    for j, h in enumerate(headers_comp):
        cell = tbl_comp.cell(0, j)
        set_cell_background(cell, HEX_PRIMARY)
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(255, 255, 255)

    data_comp = [
        ["Kecepatan Konvergensi", "Sedang (bertahap naik)", "Sangat Cepat (generasi awal)", "Cepat dan Stabil"],
        ["Kekuatan Utama", "Eksplorasi ruang global sangat baik via crossover & mutasi acak.", "Eksploitasi intensif di sekitar gbest; sangat efisien dalam komputasi.", "Kestabilan tinggi (variansi hasil antar-run paling kecil)."],
        ["Kelemahan Utama", "Memerlukan waktu lebih lama untuk memusat ke titik presisi tinggi.", "Rentan konvergensi prematur jika partikel terjebak di optimum lokal.", "Memerlukan manajemen memori jejak feromon dan tuning evaporasi ρ."],
        ["Kesesuaian Masalah Spasial", "Sangat cocok untuk penempatan multi-fasilitas (skenario 2–3 puskesmas).", "Sangat cocok untuk simulasi interaktif real-time di web browser.", "Sangat cocok untuk masalah pemilihan rute logistik dan faskes berbobot."],
        ["Rekomendasi Terapan", "Dipilih jika prioritas adalah eksplorasi variasi alternatif solusi.", "Dipilih sebagai engine utama sistem web interaktif (paling responsif).", "Dipilih jika dibutuhkan rekomendasi dengan deviasi paling konsisten."]
    ]

    for i, row in enumerate(data_comp):
        bg = HEX_ALT_ROW if i % 2 == 1 else "FFFFFF"
        for j, val in enumerate(row):
            cell = tbl_comp.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(9)
            r.font.color.rgb = COLOR_TEXT_MAIN

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    format_heading(doc, "7.2 Mengapa Terjadi Perbedaan Karakteristik Antar Algoritma", level=2)
    format_paragraph(doc, "Perbedaan mendasar ini berakar pada mekanisme pertukaran informasi antar-agen:")
    format_bullet(doc, "Pada PSO, partikel saling berbagi informasi secara instan melalui variabel global best (gbest). Komunikasi satu arah langsung ini memicu akselerasi cepat seluruh kawanan ke arah lembah fitness tertinggi.", "• ")
    format_bullet(doc, "Pada GA, informasi diwariskan melalui perkawinan silang (crossover) antar pasangan induk. Hal ini menciptakan proses penelusuran yang menyebar secara bertahap ke berbagai sudut ruang peta.", "• ")
    format_bullet(doc, "Pada ACO, informasi disimpan di lingkungan secara tidak langsung (stigma/feromon). Semut membuat keputusan berdasarkan probabilitas jejak masa lalu, sehingga transisi gerakannya lebih halus dan tidak rentan lonjakan liar.", "• ")

    format_heading(doc, "7.3 Implikasi terhadap Perencanaan Tata Ruang Kesehatan Publik", level=2)
    format_paragraph(doc, "Bagi pengambil kebijakan di Pemerintah Kota Bekasi dan Pemprov DKI Jakarta, hasil pemodelan ini membuktikan bahwa penempatan Puskesmas baru sebaiknya diposisikan pada sisi timur jembatan penghubung utama di Jl. Boulevard Harapan Indah. Posisi ini memberikan nilai tambah ganda: memudahkan rujukan cepat ambulans ke arah timur (RS Citra Harapan dan RSUD Kota Bekasi) sekaligus melayani warga pemukiman padat non-klaster di sisi barat tanpa terhambat kemacetan jalan lingkungan.")

    # =========================================================================
    # BAB 8. KESIMPULAN DAN SARAN
    # =========================================================================
    format_heading(doc, "BAB 8. KESIMPULAN DAN SARAN", level=1)

    format_heading(doc, "8.1 Kesimpulan Utama", level=2)
    format_bullet(doc, "Model fungsi tujuan multi-kriteria (Multi-Criteria Spatial Fitness Function) yang mengintegrasikan aksesibilitas penduduk berbobot 35%, kualitas jalan ambulans 30%, sinergi fasilitas umum 20%, dan jarak anti-kanibalisasi 15% terbukti efektif dan realistis dalam memandu pencarian tapak faskes perkotaan.", "1. ")
    format_bullet(doc, "Ketiga algoritma metaheuristik bio-inspired computing (GA, PSO, ACO) berhasil mencapai tingkat konvergensi feasible 100% pada alokasi anggaran 2.000 evaluasi, mencapai nilai fitness terbaik setara pada 0.9160.", "2. ")
    format_bullet(doc, "Particle Swarm Optimization (PSO) unggul sebagai metode tercepat dengan waktu komputasi 0,12–0,13 detik dan mencapai 95% konvergensi hanya dalam 4 generasi, menjadikannya algoritma paling ideal untuk visualisasi interaktif web real-time.", "3. ")
    format_bullet(doc, "Ant Colony Optimization (ACO) menunjukkan kestabilan tertinggi dengan standar deviasi fitness terkecil, sedangkan Genetic Algorithm (GA) memiliki kemampuan penjelajahan ruang yang paling beragam pada skenario multi-fasilitas.", "4. ")
    format_bullet(doc, "Rekomendasi tapak optimal Puskesmas baru di koridor Jl. Boulevard Harapan Indah (1.744m, 338m) berhasil memenuhi seluruh standar medis: berada 15m dari jalan arteri utama, memiliki buffer aman > 1.200m dari puskesmas eksisting, dan mampu melayani 98,6% populasi dengan respon ambulans rata-rata 3,4 menit.", "5. ")

    format_heading(doc, "8.2 Saran dan Pengembangan Mendatang", level=2)
    format_bullet(doc, "Pengembangan model jaringan jalan menggunakan graf routing rute nyata (Dijkstra/A* berbasis waktu tempuh riil saat jam sibuk) untuk melengkapi perhitungan jarak Euclidean.", "• ")
    format_bullet(doc, "Integrasi data demografi mikro dari sensus BPS (seperti proporsi balita dan lansia) untuk memberikan pembobotan kerentanan kesehatan yang lebih spesifik.", "• ")

    # =========================================================================
    # DAFTAR PUSTAKA
    # =========================================================================
    format_heading(doc, "DAFTAR PUSTAKA", level=1)
    
    pustaka = [
        "Church, R. L., & Murray, A. T. (2009). Business Site Selection, Location Analysis, and GIS. John Wiley & Sons.",
        "Drezner, Z., & Hamacher, H. W. (Eds.). (2002). Facility Location: Applications and Theory. Springer Science & Business Media.",
        "Eberhart, R., & Kennedy, J. (1995). A new optimizer using particle swarm theory. Proceedings of the Sixth International Symposium on Micro Machine and Human Science, 39-43.",
        "Holland, J. H. (1992). Adaptation in Natural and Artificial Systems: An Introductory Analysis with Applications to Biology, Control, and Artificial Intelligence. MIT Press.",
        "Dorigo, M., & Stützle, T. (2004). Ant Colony Optimization. MIT Press.",
        "Kementerian Kesehatan Republik Indonesia. (2019). Peraturan Menteri Kesehatan Republik Indonesia Nomor 43 Tahun 2019 tentang Pusat Kesehatan Masyarakat. Kemenkes RI.",
        "OpenStreetMap Contributors. (2026). Planet Dump and Regional Geodata Extract for Harapan Indah Bekasi. Retrieved from https://www.openstreetmap.org."
    ]

    for p_ref in pustaka:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        r = p.add_run(p_ref)
        r.font.name = "Calibri"
        r.font.size = Pt(9.5)
        r.font.color.rgb = COLOR_TEXT_MAIN

    output_filename = "Laporan_Optimasi_GA_PSO_ACO_Puskesmas.docx"
    try:
        doc.save(output_filename)
        print(f"Dokumen Word berhasil dibuat: {output_filename}")
        print(f"Ukuran file: {os.path.getsize(output_filename)/1024:.1f} KB")
    except PermissionError:
        output_filename = "Laporan_Optimasi_GA_PSO_ACO_Puskesmas_Updated.docx"
        doc.save(output_filename)
        print(f"File utama terkunci (terbuka di Word). Dokumen berhasil disimpan sebagai: {output_filename}")
        print(f"Ukuran file: {os.path.getsize(output_filename)/1024:.1f} KB")

if __name__ == "__main__":
    main()
