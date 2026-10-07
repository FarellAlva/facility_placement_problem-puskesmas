"""
Skrip untuk merender dan menyimpan gambar peta tata ruang Puskesmas ke results/map_study_area.png.
"""

import os
import matplotlib.pyplot as plt
from map_model import MapModel, plot_map


def render_and_save():
    os.makedirs("results", exist_ok=True)
    map_model = MapModel.load_from_json("maps/peta_studi.json")

    fig, ax = plt.subplots(figsize=(13.5, 9.8), dpi=200)
    plot_map(
        map_model,
        ax=ax,
        title="Peta Tata Ruang: Wilayah Kecamatan Sukamaju Sejahtera (Penempatan Puskesmas)",
        show_legend=True,
        show_banner=True,
    )
    plt.tight_layout()
    out_path = "results/map_study_area.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Berhasil merender peta: {out_path}")


if __name__ == "__main__":
    render_and_save()
