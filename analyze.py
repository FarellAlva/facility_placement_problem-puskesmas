"""
Modul Analisis Statistik Komparatif Puskesmas (analyze.py)
Memproses luaran dari run_batch.py (results/raw_runs.csv & convergence_data.npz):
1. Menghitung tabel ringkasan statistik komprehensif (GA vs PSO vs ACO)
2. Uji hipotesis Kruskal-Wallis dan post-hoc Pairwise Mann-Whitney U test (Bonferroni)
3. Visualisasi saintifik profesional:
   - results/boxplot_fitness.png: Boxplot distribusi fitness GA vs PSO vs ACO
   - results/convergence_comparison.png: Kurva konvergensi komparatif 3 algoritma (mean ± std)
   - results/final_locations_scatter.png: Scatter titik solusi akhir 30 run di atas peta
4. Menyimpan tabel ke results/summary_statistics.csv dan laporan teks ke results/statistical_test_report.txt
"""

import os
import json
import argparse
import warnings
warnings.filterwarnings("ignore")
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from map_model import MapModel, plot_map
from stats_utils import (
    summarize_runs,
    perform_kruskal_wallis_test,
    perform_pairwise_mann_whitney,
)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analisis Statistik dan Visualisasi Komparasi GA vs PSO vs ACO (Puskesmas)"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results",
        help="Folder penyimpanan data hasil run batch (default: results)",
    )
    parser.add_argument(
        "--map",
        type=str,
        default="maps/peta_studi.json",
        help="Path ke file peta kustom JSON (default: maps/peta_studi.json)",
    )
    return parser.parse_args()


def plot_boxplot_fitness_3algos(df: pd.DataFrame, output_path: str):
    """
    Membuat grafik Boxplot komparatif 3 algoritma (GA vs PSO vs ACO).
    """
    modes = df["mode"].unique()
    num_modes = len(modes)

    fig, axes = plt.subplots(1, num_modes, figsize=(7.2 * num_modes, 5.5), squeeze=False)
    fig.patch.set_facecolor("#f8fafc")

    colors = {"GA": "#2563eb", "PSO": "#dc2626", "ACO": "#059669"}
    box_faces = {"GA": "#93c5fd", "PSO": "#fca5a5", "ACO": "#a7f3d0"}
    box_edges = {"GA": "#1d4ed8", "PSO": "#b91c1c", "ACO": "#047857"}

    for idx, mode in enumerate(modes):
        ax = axes[0, idx]
        ax.set_facecolor("#ffffff")
        mode_data = df[df["mode"] == mode]

        algos = ["GA", "PSO", "ACO"]
        data_to_plot = [mode_data[mode_data["algoritma"] == a]["fitness"].values for a in algos]
        labels = [f"{a}\n(n={len(data_to_plot[i])})" for i, a in enumerate(algos)]

        box = ax.boxplot(
            data_to_plot,
            patch_artist=True,
            widths=0.45,
            tick_labels=labels,
            medianprops=dict(color="#0f172a", linewidth=2.0),
            whiskerprops=dict(color="#475569", linewidth=1.2),
            capprops=dict(color="#475569", linewidth=1.2),
            flierprops=dict(marker="o", markerfacecolor="#e11d48", markeredgecolor="#9f1239", markersize=6),
        )

        for i, a in enumerate(algos):
            box["boxes"][i].set_facecolor(box_faces[a])
            box["boxes"][i].set_edgecolor(box_edges[a])

        # Scatter jitter titik individu
        rng = np.random.default_rng(42)
        for i, (a, vals) in enumerate(zip(algos, data_to_plot), start=1):
            jitter = rng.normal(0, 0.04, size=len(vals))
            ax.scatter(i + jitter, vals, color=colors[a], alpha=0.65, s=30, edgecolors="#0f172a", linewidths=0.5, zorder=3)

        mode_title = "Maksimasi (Lokasi Terbaik Puskesmas)" if mode == "max" else "Minimasi Valid (Lokasi Terburuk Legal)"
        ax.set_title(f"Distribusi Fitness — {mode_title}", fontsize=11, weight="bold", color="#0f172a")
        ax.set_ylabel("Nilai Fitness Akhir", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Grafik Boxplot tersimpan di: {output_path}")


def plot_convergence_3algos(npz_path: str, raw_df: pd.DataFrame, output_path: str):
    """
    Membuat kurva konvergensi komparatif 3 algoritma (Mean ± Std).
    """
    if not os.path.exists(npz_path):
        print(f"Peringatan: File {npz_path} tidak ditemukan. Melewati plotting konvergensi.")
        return

    data = np.load(npz_path)
    modes = raw_df["mode"].unique()
    num_modes = len(modes)

    fig, axes = plt.subplots(1, num_modes, figsize=(7.5 * num_modes, 5.0), squeeze=False)
    fig.patch.set_facecolor("#f8fafc")

    colors = {"GA": "#2563eb", "PSO": "#dc2626", "ACO": "#059669"}
    styles = {"GA": "-", "PSO": "--", "ACO": "-."}

    for idx, mode in enumerate(modes):
        ax = axes[0, idx]
        ax.set_facecolor("#ffffff")

        for algo in ["GA", "PSO", "ACO"]:
            runs_data = []
            max_evals_points = 2000

            eval_grid = np.linspace(40, max_evals_points, 100)
            interp_runs = []

            for r in range(1, 31):
                key_evals = f"{mode}_{algo}_run{r}_evals"
                key_fits = f"{mode}_{algo}_run{r}_fits"
                if key_evals in data and key_fits in data:
                    ev = data[key_evals]
                    ft = data[key_fits]
                    if len(ev) > 1:
                        ft_interp = np.interp(eval_grid, ev, ft)
                        interp_runs.append(ft_interp)

            if len(interp_runs) > 0:
                matrix = np.array(interp_runs)
                mean_curve = np.mean(matrix, axis=0)
                std_curve = np.std(matrix, axis=0)

                ax.plot(
                    eval_grid, mean_curve,
                    color=colors[algo], linestyle=styles[algo], linewidth=2.2,
                    label=f"{algo} (Mean)",
                )
                ax.fill_between(
                    eval_grid,
                    mean_curve - std_curve,
                    mean_curve + std_curve,
                    color=colors[algo],
                    alpha=0.15,
                )

        mode_title = "Maksimasi (Lokasi Terbaik)" if mode == "max" else "Minimasi Valid (Lokasi Terburuk)"
        ax.set_title(f"Kurva Konvergensi — {mode_title}", fontsize=11, weight="bold", color="#0f172a")
        ax.set_xlabel("Jumlah Evaluasi Fitness", fontsize=10)
        ax.set_ylabel("Nilai Fitness Terbaik Berjalan", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
        ax.legend(loc="lower right" if mode == "max" else "upper right", frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1")

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Grafik Konvergensi tersimpan di: {output_path}")


def plot_scatter_locations_3algos(map_model: MapModel, raw_df: pd.DataFrame, output_path: str):
    """
    Scatter sebaran koordinat solusi akhir 30 run (GA, PSO, ACO) di atas peta wilayah.
    """
    modes = raw_df["mode"].unique()
    num_modes = len(modes)

    fig, axes = plt.subplots(1, num_modes, figsize=(8.5 * num_modes, 7.5), squeeze=False)

    colors = {"GA": "#2563eb", "PSO": "#dc2626", "ACO": "#059669"}
    markers = {"GA": "o", "PSO": "s", "ACO": "^"}

    for idx, mode in enumerate(modes):
        ax = axes[0, idx]
        mode_title = "Maksimasi (Lokasi Rekomendasi Puskesmas)" if mode == "max" else "Minimasi Valid (Titik Terburuk Legal)"
        plot_map(map_model, ax=ax, title=f"Sebaran Solusi Akhir — {mode_title}", show_legend=(idx == num_modes - 1), show_banner=False)

        mode_data = raw_df[raw_df["mode"] == mode]

        for algo in ["GA", "PSO", "ACO"]:
            sub = mode_data[mode_data["algoritma"] == algo]
            xs = sub["x"].values
            ys = sub["y"].values

            # Scatter titik akhir
            ax.scatter(
                xs, ys,
                color=colors[algo],
                marker=markers[algo],
                s=80,
                alpha=0.75,
                edgecolors="#ffffff",
                linewidths=1.2,
                label=f"{algo} (30 Run)",
                zorder=10,
            )

        # Tambahkan legenda khusus scatter
        ax.legend(loc="upper right", frameon=True, facecolor="#ffffff", edgecolor="#94a3b8", fontsize=9.0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Peta Scatter Titik Akhir tersimpan di: {output_path}")


def run_full_analysis(results_dir: str = "results", map_path: str = "maps/peta_studi.json"):
    csv_path = os.path.join(results_dir, "raw_runs.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} tidak ditemukan! Jalankan run_batch.py terlebih dahulu.")
        return

    df = pd.read_csv(csv_path)
    map_model = MapModel.load_from_json(map_path)

    # 1. Ringkasan Statistik
    summary_list = []
    for mode_name, mode_sub in df.groupby("mode"):
        sub_sum = summarize_runs(mode_sub, group_col="algoritma")
        sub_sum.insert(0, "Mode", mode_name)
        summary_list.append(sub_sum)

    full_summary = pd.concat(summary_list, ignore_index=True)
    summary_path = os.path.join(results_dir, "summary_statistics.csv")
    full_summary.to_csv(summary_path, index=False)
    print(f"Ringkasan statistik tersimpan di: {summary_path}")

    # 2. Uji Statistik Kruskal-Wallis & Post-hoc Mann-Whitney U
    report_lines = [
        "=" * 80,
        "LAPORAN UJI HIPOTESIS STATISTIK NON-PARAMETRIK: GA vs PSO vs ACO",
        "STUDI PENENTUAN LOKASI FASILITAS PUSKESMAS KECAMATAN SUKAMAJU SEJAHTERA",
        "=" * 80,
        "",
    ]

    for mode in df["mode"].unique():
        mode_data = df[df["mode"] == mode]
        data_dict = {
            algo: mode_data[mode_data["algoritma"] == algo]["fitness"].values
            for algo in ["GA", "PSO", "ACO"]
        }

        mode_header = "MODE MAKSIMASI (LOKASI TERBAIK PUSKESMAS)" if mode == "max" else "MODE MINIMASI VALID (LOKASI TERBURUK LEGAL)"
        report_lines.append(f"--- {mode_header} ---")

        # Omnibus Kruskal-Wallis
        kw_res = perform_kruskal_wallis_test(data_dict, metric_name="Nilai Fitness", alpha=0.05)
        report_lines.append(f"1. Uji Omnibus Kruskal-Wallis H-test:")
        report_lines.append(f"   - H-statistic : {kw_res['h_statistic']:.4f}")
        report_lines.append(f"   - p-value     : {kw_res['p_value']:.5e}")
        report_lines.append(f"   - Signifikan  : {kw_res['is_significant']}")
        report_lines.append(f"   - Kesimpulan  : {kw_res['kesimpulan']}")
        report_lines.append("")

        # Post-hoc Pairwise Mann-Whitney U (Bonferroni)
        report_lines.append(f"2. Uji Post-hoc Pairwise Mann-Whitney U (Koreksi Bonferroni alpha = 0.05/3 = 0.0167):")
        pw_results = perform_pairwise_mann_whitney(data_dict, metric_name="Nilai Fitness", alpha=0.05)
        for pw in pw_results:
            report_lines.append(f"   * Pasangan [{pw['algo_1']} vs {pw['algo_2']}]:")
            report_lines.append(f"     - U-statistic       : {pw['u_statistic']:.2f}")
            report_lines.append(f"     - p-value           : {pw['p_value']:.5e}")
            report_lines.append(f"     - Rank-Biserial r   : {pw['rank_biserial']:.3f}")
            report_lines.append(f"     - Interpretasi      : {pw['narasi']}")
        report_lines.append("\n" + "=" * 80 + "\n")

    report_text = "\n".join(report_lines)
    report_path = os.path.join(results_dir, "statistical_test_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"Laporan uji statistik tersimpan di: {report_path}")
    print("\n" + report_text)

    # 3. Visualisasi Grafik
    plot_boxplot_fitness_3algos(df, os.path.join(results_dir, "boxplot_fitness.png"))
    plot_convergence_3algos(
        os.path.join(results_dir, "convergence_data.npz"),
        df,
        os.path.join(results_dir, "convergence_comparison.png"),
    )
    plot_scatter_locations_3algos(map_model, df, os.path.join(results_dir, "final_locations_scatter.png"))


def main():
    args = parse_arguments()
    run_full_analysis(results_dir=args.results_dir, map_path=args.map)


if __name__ == "__main__":
    main()
