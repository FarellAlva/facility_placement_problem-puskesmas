"""
Skrip untuk merender dan menyimpan gambar peta tata ruang Puskesmas ke results/map_study_area.png.
"""

import os
import matplotlib.pyplot as plt
from map_model import MapModel, plot_map


def render_and_save():
    os.makedirs("results", exist_ok=True)
    os.makedirs("results_luas", exist_ok=True)

    # 1. Peta Wilayah Studi Desa (2.0 x 1.5 km)
    map_model1 = MapModel.load_from_json("maps/peta_studi.json")
    fig1, ax1 = plt.subplots(figsize=(13.5, 9.8), dpi=200)
    plot_map(
        map_model1,
        ax=ax1,
        title="Peta Tata Ruang: Wilayah Studi Desa Sukamaju Sejahtera (2.0 x 1.5 km)",
        show_legend=True,
        show_banner=True,
    )
    plt.tight_layout()
    out1 = "results/map_study_area.png"
    plt.savefig(out1, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Berhasil merender peta studi: {out1}")

    # 2. Peta Wilayah Kecamatan Luas (5.0 x 4.0 km)
    map_model2 = MapModel.load_from_json("maps/peta_kecamatan_luas.json")
    fig2, ax2 = plt.subplots(figsize=(14.5, 10.5), dpi=200)
    plot_map(
        map_model2,
        ax=ax2,
        title="Peta Tata Ruang: Wilayah Kecamatan Sukamaju Raya (5.0 x 4.0 km - 2.000 Ha)",
        show_legend=True,
        show_banner=True,
    )
    plt.tight_layout()
    out2 = "results/map_kecamatan_luas.png"
    plt.savefig(out2, dpi=200, bbox_inches="tight")
    plt.savefig("results_luas/map_kecamatan_luas.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Berhasil merender peta kecamatan luas: {out2}")

    # 3. Peta Kota Harapan Indah (2.4 x 1.6 km)
    os.makedirs("results_harapan_indah", exist_ok=True)
    map_model3 = MapModel.load_from_json("maps/peta_harapan_indah.json")
    fig3, ax3 = plt.subplots(figsize=(14.0, 9.6), dpi=200)
    plot_map(
        map_model3,
        ax=ax3,
        title="Peta Tata Ruang: Kawasan Kota Harapan Indah & Ujung Menteng (2.4 x 1.6 km)",
        show_legend=True,
        show_banner=True,
    )
    plt.tight_layout()
    out3 = "results/map_harapan_indah.png"
    plt.savefig(out3, dpi=200, bbox_inches="tight")
    plt.savefig("results_harapan_indah/map_harapan_indah.png", dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Berhasil merender peta harapan indah: {out3}")


if __name__ == "__main__":
    render_and_save()
