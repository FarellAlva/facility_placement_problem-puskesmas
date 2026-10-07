"""
Skrip Pembuatan Peta Kota Harapan Indah (create_harapan_indah_map.py)
Menghasilkan maps/peta_harapan_indah.json berdasarkan tangkapan peta nyata:
- Batas wilayah: 2.4 km x 1.6 km (2.400 x 1.600 meter)
- Membelah Kanal Banjir Timur (BKT) / Kali Rawarengas dan Jl. Inspeksi
- Area Barat (Ujung Menteng, Cakung, Jakarta Timur): UP PKB Ujung Menteng, Jl. Satria, Jl. Akasia, Jl. Irigasi
- Area Timur (Kota Harapan Indah, Medan Satria, Bekasi): Hotel Santika Premiere, Harapan Indah Club, COURTS, GrandLucky, Bebek Kaleyo, Mang Kabayan, Mr.Sumo, Jl. Siliwangi
- 2 Faskes Eksisting: Puskesmas Kelurahan Ujung Menteng (Barat) & Puskesmas Pejuang/Medan Satria (Timur Laut)
"""

import os
import json
import numpy as np


def build_harapan_indah_data() -> dict:
    rng = np.random.default_rng(2026)

    # 1. Pemukiman Penduduk (Houses)
    houses = []
    # 1.1 Klaster Padat Ujung Menteng & Cakung (Barat Kanal BKT)
    for _ in range(110):
        hx = float(np.clip(rng.normal(380, 140), 60, 850))
        hy = float(np.clip(rng.normal(900, 280), 300, 1540))
        # Jangan masuk ke badan air BKT
        if hx > 900 and hy > 700:
            hx -= 120
        w = float(rng.uniform(2.5, 6.0))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 1.2 Klaster Perumahan & Ruko Harapan Indah (Timur Kanal BKT)
    for _ in range(95):
        hx = float(np.clip(rng.normal(1850, 190), 1250, 2350))
        hy = float(np.clip(rng.normal(850, 320), 180, 1550))
        # Hindari danau dan tengah jalan boulevard
        if 1730 <= hx <= 1770:
            hx += 50
        w = float(rng.uniform(2.0, 5.5))
        houses.append({"x": round(hx, 1), "y": round(hy, 1), "weight": round(w, 2)})

    # 2. Fasilitas Publik
    facilities = [
        {"type": "masjid_kantor", "x": 180.0, "y": 550.0, "weight": 2.5, "name": "UP. PKB Ujung Menteng"},
        {"type": "pasar", "x": 1550.0, "y": 1050.0, "weight": 2.5, "name": "GrandLucky Superstore Harapan Indah"},
        {"type": "pasar", "x": 1550.0, "y": 1220.0, "weight": 2.2, "name": "COURTS Megastore Harapan Indah"},
        {"type": "masjid_kantor", "x": 2100.0, "y": 1400.0, "weight": 2.4, "name": "Hotel Santika Premiere Harapan Indah"},
        {"type": "posyandu", "x": 1850.0, "y": 1450.0, "weight": 1.8, "name": "Harapan Indah Club"},
        {"type": "pasar", "x": 1500.0, "y": 420.0, "weight": 1.8, "name": "Bebek Kaleyo Harapan Indah"},
        {"type": "pasar", "x": 1650.0, "y": 320.0, "weight": 1.8, "name": "MANG KABAYAN Harapan Indah"},
        {"type": "pasar", "x": 2000.0, "y": 680.0, "weight": 1.6, "name": "Mr.Sumo Harapan Indah"},
        {"type": "masjid_kantor", "x": 1760.0, "y": 100.0, "weight": 2.0, "name": "Bundaran Gerbang Harapan Indah"},
        {"type": "sekolah", "x": 480.0, "y": 1250.0, "weight": 1.8, "name": "Sentra Pendidikan Ujung Menteng"},
        {"type": "posyandu", "x": 580.0, "y": 750.0, "weight": 1.7, "name": "Posyandu RW Ujung Menteng"},
        {"type": "posyandu", "x": 1450.0, "y": 720.0, "weight": 1.9, "name": "Balai Warga Siliwangi Harapan Indah"},
    ]

    # 3. Dua Puskesmas Eksisting (Tersebar Barat dan Timur Laut)
    competitors = [
        {"x": 350.0, "y": 450.0, "name": "Puskesmas Kelurahan Ujung Menteng (Eksisting Barat)"},
        {"x": 2150.0, "y": 1480.0, "name": "Puskesmas Pejuang / Medan Satria (Eksisting Timur Laut)"},
    ]

    # 4. Jaringan Jalan Realistis
    roads = [
        # 4.1 Jl. Sultan Agung / Raya Bekasi (Arteri Nasional Selatan)
        {
            "name": "Jl. Sultan Agung / Raya Bekasi (Arteri Nasional)",
            "class": "arteri",
            "traffic": 0.95,
            "points": [
                [0.0, 340.0],
                [300.0, 260.0],
                [600.0, 180.0],
                [750.0, 140.0],
                [880.0, 110.0],
                [1100.0, 80.0],
                [1450.0, 50.0],
                [1760.0, 40.0],
                [2400.0, 20.0],
            ],
        },
        # 4.2 Jl. Boulevard Harapan Indah (Arteri Utama Kota Harapan Indah)
        {
            "name": "Jl. Boulevard Harapan Indah (Arteri Utama)",
            "class": "arteri",
            "traffic": 0.92,
            "points": [
                [1760.0, 40.0],
                [1760.0, 300.0],
                [1750.0, 600.0],
                [1740.0, 950.0],
                [1740.0, 1300.0],
                [1740.0, 1600.0],
            ],
        },
        # 4.3 Jl. Inspeksi Kanal Timur - Sisi Barat
        {
            "name": "Jl. Inspeksi Kanal Timur Sisi Barat (Kolektor)",
            "class": "kolektor",
            "traffic": 0.80,
            "points": [
                [580.0, 0.0],
                [680.0, 350.0],
                [890.0, 800.0],
                [1010.0, 1200.0],
                [1040.0, 1600.0],
            ],
        },
        # 4.4 Jl. Inspeksi Kanal Timur - Sisi Timur
        {
            "name": "Jl. Inspeksi Kanal Timur Sisi Timur (Kolektor)",
            "class": "kolektor",
            "traffic": 0.80,
            "points": [
                [660.0, 0.0],
                [760.0, 350.0],
                [980.0, 800.0],
                [1100.0, 1200.0],
                [1130.0, 1600.0],
            ],
        },
        # 4.5 Jl. Siliwangi (Kolektor Penghubung BKT - Harapan Indah)
        {
            "name": "Jl. Siliwangi (Kolektor Harapan Indah)",
            "class": "kolektor",
            "traffic": 0.85,
            "points": [
                [1010.0, 720.0],
                [1250.0, 680.0],
                [1480.0, 640.0],
                [1750.0, 600.0],
                [2100.0, 600.0],
                [2400.0, 600.0],
            ],
        },
        # 4.6 Jl. Akses GrandLucky & COURTS Megastore
        {
            "name": "Jl. Akses Sentra Komersial GrandLucky & COURTS",
            "class": "kolektor",
            "traffic": 0.78,
            "points": [
                [1740.0, 950.0],
                [1550.0, 950.0],
                [1550.0, 1260.0],
                [1740.0, 1260.0],
            ],
        },
        # 4.7 Jl. Satria Raya - Ujung Menteng
        {
            "name": "Jl. Satria Raya Ujung Menteng (Lokal)",
            "class": "lokal",
            "traffic": 0.65,
            "points": [
                [300.0, 260.0],
                [380.0, 500.0],
                [420.0, 850.0],
                [460.0, 1200.0],
                [460.0, 1600.0],
            ],
        },
        # 4.8 Jl. Irigasi & Akasia - Cakung
        {
            "name": "Jl. Irigasi & Akasia (Lokal)",
            "class": "lokal",
            "traffic": 0.60,
            "points": [
                [0.0, 1150.0],
                [300.0, 1050.0],
                [420.0, 850.0],
                [600.0, 850.0],
                [780.0, 950.0],
                [800.0, 1400.0],
                [800.0, 1600.0],
            ],
        },
        # 4.9 Jl. Sentra Kuliner Selatan (Kaleyo & Mang Kabayan)
        {
            "name": "Jl. Kuliner Harapan Indah Selatan (Lokal)",
            "class": "lokal",
            "traffic": 0.72,
            "points": [
                [1760.0, 300.0],
                [1550.0, 320.0],
                [1480.0, 440.0],
                [1480.0, 640.0],
            ],
        },
        # 4.10 Jl. Santika Boulevard Timur
        {
            "name": "Jl. Santika Boulevard Timur (Kolektor)",
            "class": "kolektor",
            "traffic": 0.75,
            "points": [
                [1740.0, 1300.0],
                [2000.0, 1300.0],
                [2150.0, 1450.0],
                [2150.0, 1600.0],
            ],
        },
    ]

    # 5. Zona Terlarang / Rawan
    forbidden_zones = [
        # 5.1 Badan Air Banjir Kanal Timur (BKT) & Sempadan Tanggul
        {
            "name": "Badan Air Banjir Kanal Timur (BKT) & Tanggul",
            "type": "sungai",
            "polygon": [
                [1030.0, 1600.0],
                [1140.0, 1600.0],
                [1110.0, 1200.0],
                [990.0, 800.0],
                [770.0, 350.0],
                [670.0, 0.0],
                [570.0, 0.0],
                [670.0, 350.0],
                [880.0, 800.0],
                [1000.0, 1200.0],
            ],
        },
        # 5.2 Danau Retensi / Kawasan Harapan Indah Club
        {
            "name": "Danau Retensi Air Harapan Indah Club",
            "type": "danau",
            "polygon": [
                [1820.0, 1500.0],
                [2020.0, 1500.0],
                [2020.0, 1600.0],
                [1820.0, 1600.0],
            ],
        },
        # 5.3 Area Fasilitas Khusus Uji Kir Kendaraan Berat Ujung Menteng
        {
            "name": "Area Khusus Pengujian PKB Ujung Menteng (Zona Terbatas)",
            "type": "tambang",
            "polygon": [
                [50.0, 480.0],
                [280.0, 480.0],
                [280.0, 620.0],
                [50.0, 620.0],
            ],
        },
    ]

    return {
        "name": "Peta Kota Harapan Indah (Bekasi - Cakung)",
        "dimensions": {"width": 2400.0, "height": 1600.0},
        "houses": houses,
        "facilities": facilities,
        "competitors": competitors,
        "roads": roads,
        "forbidden_zones": forbidden_zones,
    }


def main():
    os.makedirs("maps", exist_ok=True)
    data = build_harapan_indah_data()
    out_file = os.path.join("maps", "peta_harapan_indah.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Berhasil membuat: {out_file}")
    print(f"  Dimensi Wilayah: {data['dimensions']['width']}m x {data['dimensions']['height']}m")
    print(f"  Klaster Rumah  : {len(data['houses'])}")
    print(f"  Fasilitas Umum : {len(data['facilities'])}")
    print(f"  Faskes Eksisting: {len(data['competitors'])} (Puskesmas Ujung Menteng & Pejuang)")
    print(f"  Ruas Jalan     : {len(data['roads'])}")
    print(f"  Zona Terlarang : {len(data['forbidden_zones'])}")


if __name__ == "__main__":
    main()
