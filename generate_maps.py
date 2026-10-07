"""
Skrip Generator Peta Spasial Puskesmas (generate_maps.py)
Menghasilkan peta spasial wilayah 2.0 km x 1.5 km (2000 m x 1500 m = 300 Ha)
khusus untuk optimasi penentuan lokasi Pusat Kesehatan Masyarakat (Puskesmas).

Komponen Wilayah:
1. Pemukiman Warga (Pasien Potensial, Kelompok Rentan: Ibu Hamil, Balita, Lansia)
2. Fasilitas Publik Sinergis (Balai Desa, Posyandu, Sekolah/UKS, Pasar, Masjid)
3. Faskes Eksisting (Pustu Sukamukti - Puskesmas Pembantu / Klinik Desa)
4. Jaringan Jalan (Arteri Rujukan RSUD, Kolektor Ambulans, Lokal Dusun, Jalan Tanah)
5. Zona Terlarang (Bantaran Banjir Sungai, Hutan Lindung, Sawah LP2B, Tambang Polutif)
"""

import os
import json
import numpy as np


def generate_peta_studi_puskesmas() -> dict:
    """
    Menghasilkan data peta studi untuk penempatan Puskesmas Kecamatan Sukamaju Sejahtera.
    """
    rng = np.random.default_rng(2026)

    houses = []
    # 1. Permukiman Utama Warga Desa (Dusun Krajan & Mekar Sari)
    # Berpusat di X ~ 290 m, Y ~ 780 m
    for _ in range(96):
        hx = float(np.clip(rng.normal(290, 105), 60, 520))
        hy = float(np.clip(rng.normal(780, 110), 570, 990))
        # Bobot kepadatan pasien / kelompok rentan (skala 1.5 - 5.0 KK/kebutuhan layanan)
        w = float(rng.uniform(1.8, 5.0))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 2. Pemukiman Dusun Perkebunan / Pekerja Tambang Timur
    # Berpusat di X ~ 1840 m, Y ~ 1280 m
    for _ in range(18):
        hx = float(np.clip(rng.normal(1840, 45), 1740, 1940))
        hy = float(np.clip(rng.normal(1280, 50), 1180, 1380))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": 1.5})

    # Fasilitas Umum & Titik Sinergi Layanan Kesehatan
    facilities = [
        {"type": "balai_desa", "x": 280.0, "y": 780.0, "weight": 2.0, "name": "Kantor Desa & Pusat Layanan BPJS"},
        {"type": "posyandu", "x": 360.0, "y": 720.0, "weight": 1.8, "name": "Posyandu Melati Indah"},
        {"type": "sekolah", "x": 480.0, "y": 950.0, "weight": 1.5, "name": "SDN Sukamaju 1 (Mitra UKS)"},
        {"type": "sekolah", "x": 560.0, "y": 950.0, "weight": 1.5, "name": "SMPN 1 Sukamaju (Mitra UKS)"},
        {"type": "sekolah", "x": 480.0, "y": 860.0, "weight": 1.4, "name": "Madrasah Ibtidaiyah Desa"},
        {"type": "pasar", "x": 560.0, "y": 860.0, "weight": 1.2, "name": "Pasar Tradisional Desa"},
        {"type": "masjid_kantor", "x": 640.0, "y": 830.0, "weight": 1.0, "name": "Masjid Jami' Sukamaju"},
        {"type": "masjid_kantor", "x": 600.0, "y": 750.0, "weight": 0.8, "name": "Balai Pertemuan Warga"},
        {"type": "posyandu", "x": 660.0, "y": 750.0, "weight": 1.6, "name": "Posyandu Cempaka"},
        {"type": "masjid_kantor", "x": 1780.0, "y": 1080.0, "weight": 1.0, "name": "Posko Kesehatan Pekerja"},
    ]

    # Faskes Eksisting (Puskesmas Pembantu / Klinik Desa Lama yang dihindari kanibalisasinya)
    faskes_eksisting = [
        {"x": 860.0, "y": 800.0, "name": "Pustu Sukamukti (Faskes Eksisting)"},
    ]

    # Jaringan Jalan Wilayah
    roads = [
        # Jalan Lintas Provinsi (Arteri 4 Lajur - Jalur Utama Ambulans Rujukan ke RSUD)
        {
            "name": "Jl. Lintas Provinsi (Arteri Rujukan RSUD)",
            "class": "arteri",
            "traffic": 0.90,
            "points": [
                [1150.0, 0.0],
                [1150.0, 500.0],
                [1150.0, 800.0],
                [1150.0, 1100.0],
                [1150.0, 1500.0],
            ],
        },
        # Jalan Utama Desa (Kolektor Mulus - Jalur Utama Ambulans Masuk Desa)
        {
            "name": "Jl. Utama Desa (Kolektor Ambulans)",
            "class": "kolektor",
            "traffic": 0.85,
            "points": [
                [60.0, 780.0],
                [280.0, 780.0],
                [480.0, 780.0],
                [640.0, 800.0],
                [800.0, 800.0],
                [860.0, 800.0],
                [960.0, 800.0],
                [1150.0, 800.0],
            ],
        },
        # Jalan Lingkar Dusun Utara (Lokal Aspal Desa)
        {
            "name": "Jl. Dusun Utara (Lokal)",
            "class": "lokal",
            "traffic": 0.60,
            "points": [
                [280.0, 780.0],
                [280.0, 920.0],
                [380.0, 980.0],
                [480.0, 980.0],
                [560.0, 950.0],
                [640.0, 860.0],
                [640.0, 800.0],
            ],
        },
        # Jalan Lingkar Dusun Selatan (Lokal Aspal Desa)
        {
            "name": "Jl. Dusun Selatan (Lokal)",
            "class": "lokal",
            "traffic": 0.60,
            "points": [
                [280.0, 780.0],
                [280.0, 680.0],
                [380.0, 620.0],
                [480.0, 620.0],
                [560.0, 680.0],
                [640.0, 750.0],
                [640.0, 800.0],
            ],
        },
        # Jalan Pertokoan & Pasar Desa
        {
            "name": "Jl. Pasar Desa (Lokal)",
            "class": "lokal",
            "traffic": 0.65,
            "points": [
                [480.0, 780.0],
                [480.0, 860.0],
                [560.0, 860.0],
                [560.0, 780.0],
            ],
        },
        # Jalan Akses Kawasan Timur (Penghubung Arteri ke Perkebunan/Tambang)
        {
            "name": "Jl. Akses Tambang Timur (Kolektor)",
            "class": "kolektor",
            "traffic": 0.70,
            "points": [
                [1150.0, 800.0],
                [1350.0, 800.0],
                [1480.0, 900.0],
                [1580.0, 1020.0],
                [1680.0, 1150.0],
            ],
        },
        # Jalan Hauling / Tanah Rusak (Buruk untuk Ambulans dan Pasien Kritis)
        {
            "name": "Jl. Hauling / Tanah Rusak",
            "class": "hauling",
            "traffic": 0.20,
            "points": [
                [1680.0, 1150.0],
                [1780.0, 1150.0],
                [1880.0, 1200.0],
                [1950.0, 1300.0],
            ],
        },
    ]

    # Zona Terlarang Dilindungi (Dilarang Membangun Fasilitas Kesehatan)
    forbidden_zones = [
        # 1. Hutan Lindung Adat & Resapan Air (Barat Laut)
        {
            "name": "Kawasan Hutan Lindung (Zona Konservasi)",
            "type": "hutan",
            "polygon": [
                [0.0, 1080.0],
                [740.0, 1080.0],
                [760.0, 1500.0],
                [0.0, 1500.0],
            ],
        },
        # 2. Kawasan Sawah Irigasi Berkelanjutan (LP2B - Barat Daya)
        {
            "name": "Kawasan Pertanian Sawah Produktif (LP2B)",
            "type": "sawah",
            "polygon": [
                [0.0, 0.0],
                [640.0, 0.0],
                [640.0, 520.0],
                [0.0, 520.0],
            ],
        },
        # 3. Bantaran Banjir & Sempadan Sungai Sukamaju (Sisi Tengah)
        {
            "name": "Bantaran Banjir Sungai Sukamaju (Rawan Luapan Air)",
            "type": "sungai",
            "polygon": [
                [770.0, 0.0],
                [850.0, 0.0],
                [850.0, 450.0],
                [920.0, 650.0],
                [920.0, 850.0],
                [870.0, 1050.0],
                [870.0, 1500.0],
                [790.0, 1500.0],
                [790.0, 1050.0],
                [840.0, 850.0],
                [840.0, 650.0],
                [770.0, 450.0],
            ],
        },
        # 4. Kawasan Polutif Tambang Terbuka & Stockpile (Bahaya Debu & Getaran)
        {
            "name": "Area Galian Tambang & Stockpile (Zona Polutif B3)",
            "type": "tambang",
            "polygon": [
                [1420.0, 0.0],
                [2000.0, 0.0],
                [2000.0, 750.0],
                [1420.0, 750.0],
            ],
        },
    ]

    return {
        "name": "Peta Wilayah Studi: Kecamatan Sukamaju Sejahtera (Penempatan Puskesmas)",
        "dimensions": {
            "width": 2000.0,
            "height": 1500.0,
        },
        "houses": houses,
        "facilities": facilities,
        "competitors": faskes_eksisting,  # Kunci competitors dipetakan ke faskes_eksisting untuk konsistensi API
        "roads": roads,
        "forbidden_zones": forbidden_zones,
    }


def main():
    os.makedirs("maps", exist_ok=True)
    peta_data = generate_peta_studi_puskesmas()
    out_path = os.path.join("maps", "peta_studi.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(peta_data, f, indent=2, ensure_ascii=False)
    print(f"Berhasil menghasilkan peta spasial Puskesmas: {out_path}")
    print(f"Total titik pemukiman : {len(peta_data['houses'])}")
    print(f"Total fasilitas publik : {len(peta_data['facilities'])}")
    print(f"Faskes eksisting       : {len(peta_data['competitors'])}")
    print(f"Total segmen jalan     : {len(peta_data['roads'])}")
    print(f"Zona terlarang         : {len(peta_data['forbidden_zones'])}")


if __name__ == "__main__":
    main()
