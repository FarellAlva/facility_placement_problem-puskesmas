"""
Skrip Generator Peta Spasial Puskesmas (generate_maps.py)
Menghasilkan dua preset peta spasial:
1. 'Peta Wilayah Studi (Desa Sukamaju)' — 2.0 km x 1.5 km (300 Hektar)
2. 'Peta Kecamatan Luas (Sukamaju Raya - Skala OpenStreetMap)' — 5.0 km x 4.0 km (2.000 Hektar / 20 km²)
"""

import os
import json
import numpy as np


def generate_peta_studi_puskesmas() -> dict:
    """
    Peta Studi Skala Desa / Lingkungan: 2.0 km x 1.5 km (300 Ha)
    """
    rng = np.random.default_rng(2026)

    houses = []
    # 1. Permukiman Utama Dusun Krajan
    for _ in range(96):
        hx = float(np.clip(rng.normal(290, 105), 60, 520))
        hy = float(np.clip(rng.normal(780, 110), 570, 990))
        w = float(rng.uniform(1.8, 5.0))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 2. Permukiman Pekerja Perkebunan / Tambang
    for _ in range(18):
        hx = float(np.clip(rng.normal(1840, 45), 1740, 1940))
        hy = float(np.clip(rng.normal(1280, 50), 1180, 1380))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": 1.5})

    facilities = [
        {"type": "balai_desa", "x": 280.0, "y": 780.0, "weight": 2.0, "name": "Kantor Desa & Layanan BPJS"},
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

    faskes_eksisting = [
        {"x": 860.0, "y": 800.0, "name": "Pustu Sukamukti (Faskes Eksisting)"},
    ]

    roads = [
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

    forbidden_zones = [
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
        "name": "Peta Wilayah Studi: Desa Sukamaju (2.0 x 1.5 km)",
        "dimensions": {"width": 2000.0, "height": 1500.0},
        "houses": houses,
        "facilities": facilities,
        "competitors": faskes_eksisting,
        "roads": roads,
        "forbidden_zones": forbidden_zones,
    }


def generate_peta_kecamatan_luas() -> dict:
    """
    Peta Kecamatan Skala Luas (OpenStreetMap / Google Maps Style):
    Dimensi: 5.0 km x 4.0 km (5000 m x 4000 m = 2.000 Hektar / 20 km²)
    Mencakup 4 Desa / Kelurahan:
    - Desa Sukamaju Krajan (Pusat Pemerintahan Kecamatan & Rumah Sakit Rujukan)
    - Desa Sukarukun (Sentra Perkebunan & Peternakan Timur)
    - Desa Sukadamai (Lembah Pertanian Selatan)
    - Dusun Danau Mandiri (Barat Daya)
    """
    rng = np.random.default_rng(777)

    houses = []
    # 1. Ibukota Kecamatan (Sukamaju Krajan) - Kepadatan Tinggi (130 titik)
    for _ in range(130):
        hx = float(np.clip(rng.normal(1350, 240), 750, 1950))
        hy = float(np.clip(rng.normal(2450, 250), 1900, 3050))
        w = float(rng.uniform(2.5, 6.0))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 2. Desa Sukarukun (Kawasan Timur) - 65 titik
    for _ in range(65):
        hx = float(np.clip(rng.normal(3850, 180), 3400, 4350))
        hy = float(np.clip(rng.normal(3050, 200), 2600, 3500))
        w = float(rng.uniform(1.8, 4.5))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 3. Desa Sukadamai (Lembah Selatan) - 50 titik
    for _ in range(50):
        hx = float(np.clip(rng.normal(2150, 190), 1700, 2600))
        hy = float(np.clip(rng.normal(950, 180), 550, 1400))
        w = float(rng.uniform(1.8, 4.2))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 4. Dusun Danau Mandiri (Barat Daya) - 30 titik
    for _ in range(30):
        hx = float(np.clip(rng.normal(650, 140), 300, 1000))
        hy = float(np.clip(rng.normal(1200, 150), 850, 1550))
        w = float(rng.uniform(1.5, 3.5))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # Fasilitas Umum Tingkat Kecamatan
    facilities = [
        {"type": "balai_desa", "x": 1350.0, "y": 2450.0, "weight": 2.5, "name": "Kantor Kecamatan & Layanan BPJS Mandiri"},
        {"type": "pasar", "x": 1550.0, "y": 2380.0, "weight": 2.0, "name": "Pasar Induk Sukamaju Raya"},
        {"type": "sekolah", "x": 1600.0, "y": 2600.0, "weight": 1.8, "name": "SMA Negeri 1 Sukamaju"},
        {"type": "sekolah", "x": 1200.0, "y": 2650.0, "weight": 1.6, "name": "SMP Negeri 1 Sukamaju"},
        {"type": "sekolah", "x": 1150.0, "y": 2200.0, "weight": 1.5, "name": "SDN Sukamaju 1 (UKS)"},
        {"type": "posyandu", "x": 1400.0, "y": 2250.0, "weight": 1.8, "name": "Posyandu Mawar Indah"},
        {"type": "masjid_kantor", "x": 1350.0, "y": 2550.0, "weight": 1.4, "name": "Masjid Agung Sukamaju Raya"},

        # Fasilitas Desa Timur (Sukarukun)
        {"type": "balai_desa", "x": 3750.0, "y": 3050.0, "weight": 1.6, "name": "Balai Desa Sukarukun"},
        {"type": "posyandu", "x": 3850.0, "y": 2900.0, "weight": 1.5, "name": "Posyandu Melati Sukarukun"},
        {"type": "sekolah", "x": 3950.0, "y": 3200.0, "weight": 1.4, "name": "SDN Sukarukun 1"},

        # Fasilitas Desa Selatan (Sukadamai)
        {"type": "balai_desa", "x": 2150.0, "y": 950.0, "weight": 1.6, "name": "Balai Desa Sukadamai"},
        {"type": "posyandu", "x": 2250.0, "y": 850.0, "weight": 1.5, "name": "Posyandu Cempaka Sukadamai"},
        {"type": "sekolah", "x": 2050.0, "y": 1050.0, "weight": 1.4, "name": "SDN Sukadamai 1"},
    ]

    # Faskes Eksisting Tingkat Kecamatan (Pustu & Klinik Tersebar)
    faskes_eksisting = [
        {"x": 3900.0, "y": 3050.0, "name": "Pustu Sukarukun (Faskes Eksisting 1)"},
        {"x": 2250.0, "y": 950.0, "name": "Pustu Sukadamai (Faskes Eksisting 2)"},
        {"x": 750.0, "y": 2400.0, "name": "Klinik Pratama Sehat (Faskes Eksisting 3)"},
    ]

    # Jaringan Jalan Skala Kecamatan (OpenStreetMap Hierarchy)
    roads = [
        # Jalan Nasional / Arteri Utama (Lintas Kabupaten, Membentang Barat - Timur)
        {
            "name": "Jl. Raya Nasional (Arteri Evakuasi RSUD)",
            "class": "arteri",
            "traffic": 0.95,
            "points": [
                [0.0, 2400.0],
                [1000.0, 2400.0],
                [1350.0, 2450.0],
                [2000.0, 2450.0],
                [3000.0, 2450.0],
                [3800.0, 2450.0],
                [5000.0, 2450.0],
            ],
        },
        # Jalan Kolektor Utama Utara - Selatan (Penghubung Kecamatan)
        {
            "name": "Jl. Raya Sukamaju (Kolektor Ambulans)",
            "class": "kolektor",
            "traffic": 0.85,
            "points": [
                [1350.0, 0.0],
                [1350.0, 1000.0],
                [1350.0, 1800.0],
                [1350.0, 2450.0],
                [1350.0, 3200.0],
                [1350.0, 4000.0],
            ],
        },
        # Jalan Kolektor Menuju Sukarukun (Timur)
        {
            "name": "Jl. Poros Sukarukun (Kolektor)",
            "class": "kolektor",
            "traffic": 0.80,
            "points": [
                [3800.0, 2450.0],
                [3800.0, 2800.0],
                [3850.0, 3050.0],
                [3850.0, 3600.0],
                [3850.0, 4000.0],
            ],
        },
        # Jalan Kolektor Menuju Sukadamai (Selatan)
        {
            "name": "Jl. Poros Sukadamai (Kolektor)",
            "class": "kolektor",
            "traffic": 0.75,
            "points": [
                [1350.0, 1000.0],
                [1750.0, 950.0],
                [2150.0, 950.0],
                [2600.0, 950.0],
            ],
        },
        # Jalan Lingkar Krajan (Lokal Dusun Utama)
        {
            "name": "Jl. Lingkar Krajan (Lokal)",
            "class": "lokal",
            "traffic": 0.60,
            "points": [
                [1100.0, 2200.0],
                [1100.0, 2700.0],
                [1600.0, 2700.0],
                [1600.0, 2200.0],
                [1100.0, 2200.0],
            ],
        },
        # Jalan Lingkar Barat (Lokal Dusun Danau)
        {
            "name": "Jl. Dusun Danau (Lokal)",
            "class": "lokal",
            "traffic": 0.55,
            "points": [
                [650.0, 2400.0],
                [650.0, 1800.0],
                [650.0, 1200.0],
                [1000.0, 1200.0],
                [1350.0, 1200.0],
            ],
        },
        # Jalan Hauling Perbukitan Utara (Tanah Rusak)
        {
            "name": "Jl. Perbukitan Hauling (Tanah)",
            "class": "hauling",
            "traffic": 0.20,
            "points": [
                [3850.0, 3600.0],
                [4200.0, 3650.0],
                [4600.0, 3750.0],
                [4950.0, 3850.0],
            ],
        },
    ]

    # Zona Terlarang Lingkungan Skala Kecamatan
    forbidden_zones = [
        # 1. Aliran Sungai Utama & Bantaran Banjir (Meliuk dari Barat Laut ke Tenggara)
        {
            "name": "Bantaran Banjir Sungai Citarum / Sukamaju",
            "type": "sungai",
            "polygon": [
                [2400.0, 4000.0],
                [2650.0, 4000.0],
                [2800.0, 3000.0],
                [2500.0, 2000.0],
                [2100.0, 1400.0],
                [1900.0, 0.0],
                [1650.0, 0.0],
                [1850.0, 1400.0],
                [2250.0, 2000.0],
                [2550.0, 3000.0],
            ],
        },
        # 2. Kawasan Hutan Lindung Gunung Utara (Konservasi Tangkapan Air)
        {
            "name": "Kawasan Hutan Lindung Lereng Utara",
            "type": "hutan",
            "polygon": [
                [2800.0, 3550.0],
                [5000.0, 3550.0],
                [5000.0, 4000.0],
                [2800.0, 4000.0],
            ],
        },
        # 3. Lahan Pertanian Pangan Berkelanjutan (LP2B Sawah Irigasi Selatan)
        {
            "name": "Kawasan Pertanian Pangan Abadi (LP2B)",
            "type": "sawah",
            "polygon": [
                [2600.0, 0.0],
                [3600.0, 0.0],
                [3600.0, 1600.0],
                [2600.0, 1600.0],
            ],
        },
        # 4. Kawasan Industri & TPA Sampah Terpadu (Zona B3 Polutif)
        {
            "name": "Kawasan Industri & TPA Terpadu (Zona Polutif B3)",
            "type": "tambang",
            "polygon": [
                [4200.0, 500.0],
                [5000.0, 500.0],
                [5000.0, 1600.0],
                [4200.0, 1600.0],
            ],
        },
    ]

    return {
        "name": "Peta Kecamatan Luas: Sukamaju Raya (5.0 x 4.0 km)",
        "dimensions": {"width": 5000.0, "height": 4000.0},
        "houses": houses,
        "facilities": facilities,
        "competitors": faskes_eksisting,
        "roads": roads,
        "forbidden_zones": forbidden_zones,
    }


def main():
    os.makedirs("maps", exist_ok=True)

    # 1. Peta Studi (2.0 x 1.5 km)
    peta_studi = generate_peta_studi_puskesmas()
    out1 = os.path.join("maps", "peta_studi.json")
    with open(out1, "w", encoding="utf-8") as f:
        json.dump(peta_studi, f, indent=2, ensure_ascii=False)
    print(f"Berhasil menghasilkan: {out1} ({peta_studi['dimensions']['width']}m x {peta_studi['dimensions']['height']}m)")

    # 2. Peta Kecamatan Luas (5.0 x 4.0 km)
    peta_luas = generate_peta_kecamatan_luas()
    out2 = os.path.join("maps", "peta_kecamatan_luas.json")
    with open(out2, "w", encoding="utf-8") as f:
        json.dump(peta_luas, f, indent=2, ensure_ascii=False)
    print(f"Berhasil menghasilkan: {out2} ({peta_luas['dimensions']['width']}m x {peta_luas['dimensions']['height']}m)")
    print(f"  Total Titik Pemukiman : {len(peta_luas['houses'])}")
    print(f"  Total Fasilitas Publik : {len(peta_luas['facilities'])}")
    print(f"  Faskes Eksisting       : {len(peta_luas['competitors'])}")
    print(f"  Jaringan Jalan         : {len(peta_luas['roads'])}")
    print(f"  Zona Terlarang         : {len(peta_luas['forbidden_zones'])}")


if __name__ == "__main__":
    main()
