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
    root = tk.Tk()
    root.geometry("1400x880")
    root.withdraw()

    app = PuskesmasOptimizationApp(root)
    root.update()

    # Maju ke iterasi akhir
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

    try:
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    capture_screenshots()
