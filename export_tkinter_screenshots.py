"""
Skrip untuk mengekspor gambar tangkapan layar antarmuka Tkinter
ke berkas PNG berkualitas tinggi untuk dokumentasi README dan laporan:
1. results/tkinter_simulasi_split.png
2. results/tkinter_simulasi_ga_full.png
3. results/tkinter_simulasi_pso_full.png
4. results/tkinter_simulasi_aco_full.png
5. results/tkinter_simulasi_conv_full.png
"""

import os
import tkinter as tk
from PIL import Image
from app_tkinter import PuskesmasOptimizationApp


def capture_screenshots():
    os.makedirs("results", exist_ok=True)
    os.makedirs("results_luas", exist_ok=True)
    root = tk.Tk()
    root.geometry("1400x880")
    root.withdraw()

    app = PuskesmasOptimizationApp(root)
    root.update()

    # 1. Peta Studi Desa (2.0 x 1.5 km)
    print("--- Mengambil screenshot untuk Peta Studi Desa ---")
    app._run_to_end()
    root.update()

    view_modes = [
        ("split_3", "results/tkinter_simulasi_split.png"),
        ("ga", "results/tkinter_simulasi_ga_full.png"),
        ("pso", "results/tkinter_simulasi_pso_full.png"),
        ("aco", "results/tkinter_simulasi_aco_full.png"),
        ("conv", "results/tkinter_simulasi_conv_full.png"),
    ]

    for v_mode, out_path in view_modes:
        app._set_view_mode(v_mode)
        root.update()
        app.fig.canvas.draw()

        w, h = app.fig.canvas.get_width_height()
        buf = app.fig.canvas.buffer_rgba()
        raw_img = Image.frombuffer("RGBA", (w, h), buf, "raw", "RGBA", 0, 1)
        rgb_img = raw_img.convert("RGB")
        rgb_img.save(out_path, dpi=(150, 150))
        print(f"Berhasil menyimpan screenshot {v_mode}: {out_path}")

    # 2. Peta Kecamatan Luas (5.0 x 4.0 km)
    print("\n--- Mengambil screenshot untuk Peta Kecamatan Luas ---")
    app.cmb_map.set("Peta Kecamatan Luas / OSM (5.0 km x 4.0 km)")
    app._on_map_selected()
    root.update()
    app._run_to_end()
    root.update()

    view_modes_luas = [
        ("split_3", "results_luas/tkinter_simulasi_split.png"),
        ("ga", "results_luas/tkinter_simulasi_ga_full.png"),
        ("pso", "results_luas/tkinter_simulasi_pso_full.png"),
        ("aco", "results_luas/tkinter_simulasi_aco_full.png"),
        ("conv", "results_luas/tkinter_simulasi_conv_full.png"),
    ]

    for v_mode, out_path in view_modes_luas:
        app._set_view_mode(v_mode)
        root.update()
        app.fig.canvas.draw()

        w, h = app.fig.canvas.get_width_height()
        buf = app.fig.canvas.buffer_rgba()
        raw_img = Image.frombuffer("RGBA", (w, h), buf, "raw", "RGBA", 0, 1)
        rgb_img = raw_img.convert("RGB")
        rgb_img.save(out_path, dpi=(150, 150))
        print(f"Berhasil menyimpan screenshot {v_mode}: {out_path}")

    # 3. Peta Kota Harapan Indah (2.4 x 1.6 km)
    os.makedirs("results_harapan_indah", exist_ok=True)
    print("\n--- Mengambil screenshot untuk Peta Kota Harapan Indah ---")
    app.cmb_map.set("Peta Kota Harapan Indah (2.4 km x 1.6 km)")
    app._on_map_selected()
    root.update()
    app._run_to_end()
    root.update()

    view_modes_hi = [
        ("split_3", "results_harapan_indah/tkinter_simulasi_split.png"),
        ("ga", "results_harapan_indah/tkinter_simulasi_ga_full.png"),
        ("pso", "results_harapan_indah/tkinter_simulasi_pso_full.png"),
        ("aco", "results_harapan_indah/tkinter_simulasi_aco_full.png"),
        ("conv", "results_harapan_indah/tkinter_simulasi_conv_full.png"),
    ]

    for v_mode, out_path in view_modes_hi:
        app._set_view_mode(v_mode)
        root.update()
        app.fig.canvas.draw()

        w, h = app.fig.canvas.get_width_height()
        buf = app.fig.canvas.buffer_rgba()
        raw_img = Image.frombuffer("RGBA", (w, h), buf, "raw", "RGBA", 0, 1)
        rgb_img = raw_img.convert("RGB")
        rgb_img.save(out_path, dpi=(150, 150))
        print(f"Berhasil menyimpan screenshot {v_mode}: {out_path}")

    try:
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    capture_screenshots()
