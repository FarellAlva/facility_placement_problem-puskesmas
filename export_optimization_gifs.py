"""
Skrip Generator Animasi GIF Optimasi Puskesmas (export_optimization_gifs.py)
Mengekspor animasi proses pencarian solusi GA, PSO, dan ACO ke format GIF:
1. results/ga_maksimasi.gif
2. results/pso_maksimasi.gif
3. results/aco_maksimasi.gif
4. results/simulasi_maksimasi_split.gif
5. results/simulasi_minimasi_split.gif
"""

import os
import sys
import time
import tkinter as tk
import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from app_tkinter import PuskesmasOptimizationApp


def capture_view_frames(app, view_mode: str, step_interval: int = 2):
    app._set_view_mode(view_mode)
    app.root.update_idletasks()

    total = app.total_frames
    frames = []

    selected_indices = list(range(0, total, step_interval))
    if (total - 1) not in selected_indices:
        selected_indices.append(total - 1)

    print(f"  -> Rendering {len(selected_indices)} frames for '{view_mode}'...", flush=True)

    for f_idx in selected_indices:
        app._render_frame(f_idx)
        app.fig.canvas.draw()

        w, h = app.fig.canvas.get_width_height()
        buf = app.fig.canvas.buffer_rgba()
        raw_img = Image.frombuffer("RGBA", (w, h), buf, "raw", "RGBA", 0, 1)

        rgb_img = raw_img.convert("RGB")
        quant_img = rgb_img.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
        frames.append(quant_img)

    return frames


def save_as_gif(frames, output_path: str, fps: int = 8, final_pause_ms: int = 2500):
    if not frames:
        print(f"Error: Tidak ada frame untuk {output_path}", flush=True)
        return

    frame_duration = int(1000 / fps)
    durations = [frame_duration] * (len(frames) - 1) + [final_pause_ms]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  [OK] Saved: {output_path} ({size_mb:.2f} MB, {len(frames)} frames)", flush=True)


def generate_all_gifs():
    t_start = time.time()
    print("=" * 75, flush=True)
    print("MEMULAI PEMBUATAN ANIMASI GIF GA, PSO, & ACO (PUSKESMAS)", flush=True)
    print("=" * 75, flush=True)

    root = tk.Tk()
    root.geometry("1100x700")
    root.withdraw()

    print("\n[1/2] Menginisialisasi GUI & Menghitung Mode Maksimasi...", flush=True)
    app = PuskesmasOptimizationApp(root)
    root.update()

    # Mode Maksimasi
    app.mode_var.set("max")
    app._recompute_optimization(reset_playback=True)
    root.update()

    print("  Mengekspor GA Maksimasi...", flush=True)
    frames_ga = capture_view_frames(app, "ga", step_interval=2)
    save_as_gif(frames_ga, "results/ga_maksimasi.gif", fps=7)

    print("  Mengekspor PSO Maksimasi...", flush=True)
    frames_pso = capture_view_frames(app, "pso", step_interval=2)
    save_as_gif(frames_pso, "results/pso_maksimasi.gif", fps=7)

    print("  Mengekspor ACO Maksimasi...", flush=True)
    frames_aco = capture_view_frames(app, "aco", step_interval=2)
    save_as_gif(frames_aco, "results/aco_maksimasi.gif", fps=7)

    print("  Mengekspor Split 3-Algoritma Maksimasi...", flush=True)
    frames_split_max = capture_view_frames(app, "split_3", step_interval=2)
    save_as_gif(frames_split_max, "results/simulasi_maksimasi_split.gif", fps=7)

    # Mode Minimasi Valid
    print("\n[2/2] Menghitung Mode Minimasi Valid...", flush=True)
    app.mode_var.set("min_valid")
    app._recompute_optimization(reset_playback=True)
    root.update()

    print("  Mengekspor Split 3-Algoritma Minimasi...", flush=True)
    frames_split_min = capture_view_frames(app, "split_3", step_interval=2)
    save_as_gif(frames_split_min, "results/simulasi_minimasi_split.gif", fps=7)

    t_total = time.time() - t_start
    print("\n" + "=" * 75, flush=True)
    print(f"PEMBUATAN SELURUH ANIMASI GIF SELESAI ({t_total:.1f} detik)!", flush=True)
    print("=" * 75, flush=True)

    try:
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    generate_all_gifs()
