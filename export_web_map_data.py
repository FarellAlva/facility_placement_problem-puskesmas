"""
Skrip untuk mengekspor ketiga peta JSON ke web/map_data.js
sehingga aplikasi web dapat berjalan 100% offline (file://) tanpa kendala CORS.
"""

import os
import json

os.makedirs("web", exist_ok=True)

maps_dict = {}

# 1. Harapan Indah
with open("maps/peta_harapan_indah.json", "r", encoding="utf-8") as f:
    maps_dict["harapan_indah"] = json.load(f)

# 2. Peta Studi Desa
with open("maps/peta_studi.json", "r", encoding="utf-8") as f:
    maps_dict["peta_studi"] = json.load(f)

# 3. Peta Kecamatan Luas
with open("maps/peta_kecamatan_luas.json", "r", encoding="utf-8") as f:
    maps_dict["kecamatan_luas"] = json.load(f)

with open("web/map_data.js", "w", encoding="utf-8") as f:
    f.write("// Data Peta Terpadu untuk Aplikasi Web Optimasi Penempatan Puskesmas Harapan Indah\n")
    f.write("window.PRESET_MAPS = ")
    json.dump(maps_dict, f, ensure_ascii=False)
    f.write(";\n")

print("Berhasil mengekspor web/map_data.js")
