"""
Modul Eksperimen Batch Puskesmas (run_batch.py)
Menjalankan 30 run independen per algoritma (seed 1..30) tanpa GUI:
- Membandingkan Genetic Algorithm (GA), Particle Swarm Optimization (PSO), dan Ant Colony Optimization (ACO)
- Mendukung mode 'max' (lokasi terbaik) dan 'min_valid' (lokasi terburuk legal di tepi jalan)
- Mengukur waktu komputasi, evaluasi ke-95%, fitness akhir, dan koordinat penempatan Puskesmas
- Menyimpan hasil ke results/raw_runs.csv, results/config_used.json, dan results/convergence_data.npz
"""

import sys
import os
import time
import json
import argparse
import warnings
warnings.filterwarnings("ignore")
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd

from map_model import MapModel
from fitness import FitnessEvaluator
from ga import GeneticAlgorithm
from pso import ParticleSwarmOptimization
from aco import AntColonyOptimization
from stats_utils import compute_eval_to_95_percent


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Eksperimen Batch 30 Run GA vs PSO vs ACO untuk Penempatan Puskesmas"
    )
    parser.add_argument(
        "--map",
        type=str,
        default="maps/peta_studi.json",
        help="Path ke file peta kustom JSON (default: maps/peta_studi.json)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path ke file konfigurasi JSON (default: config.json)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        help="Jumlah run independen per algoritma (default: 30)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=2000,
        help="Anggaran evaluasi fitness per run (default: 2000)",
    )
    parser.add_argument(
        "--p",
        type=int,
        default=1,
        help="Jumlah fasilitas Puskesmas (default: 1)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["max", "min_valid", "both"],
        default="both",
        help="Mode optimasi yang diuji: 'max', 'min_valid', atau 'both' (default: both)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Folder penyimpanan luaran (default: results)",
    )
    return parser.parse_args()


def print_progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    percent = float(current) / float(total)
    filled_len = int(length * percent)
    bar = "=" * filled_len + "-" * (length - filled_len)
    sys.stdout.write(f"\r{prefix} [{bar}] {current}/{total} ({percent*100:.1f}%)")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def run_batch_experiment(
    map_path: str,
    config_path: str,
    num_runs: int = 30,
    budget: int = 2000,
    num_stores: int = 1,
    modes: List[str] = None,
    output_dir: str = "results",
):
    if modes is None:
        modes = ["max", "min_valid"]

    os.makedirs(output_dir, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    config_used_path = os.path.join(output_dir, "config_used.json")
    with open(config_used_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    map_model = MapModel.load_from_json(map_path)

    raw_records = []
    convergence_dict = {}

    pop_size = config_data.get("optimization", {}).get("population_size", 40)
    ga_cfg = config_data.get("ga", {})
    pso_cfg = config_data.get("pso", {})
    aco_cfg = config_data.get("aco", {})

    algos = ["GA", "PSO", "ACO"]

    print("=" * 75)
    print(f"EKSPERIMEN BATCH PENENTUAN LOKASI PUSKESMAS (GA vs PSO vs ACO) - {num_runs} RUNS")
    print(f"Peta: {map_model.name}")
    print(f"Anggaran Evaluasi: {budget} | Ukuran Populasi/Swarm/Arsip: {pop_size} | Fasilitas: p={num_stores}")
    print(f"Mode yang diuji: {', '.join(modes)}")
    print("=" * 75)

    total_tasks = len(modes) * len(algos) * num_runs
    completed_tasks = 0

    for mode in modes:
        print(f"\n>>> Memulai Eksperimen Mode: '{mode.upper()}' <<<")

        evaluator = FitnessEvaluator(
            map_model,
            config=config_data,
            mode=mode,
            num_stores=num_stores,
        )

        for algo_name in algos:
            print(f"  Menjalankan Algoritma: {algo_name}...")

            for r in range(1, num_runs + 1):
                seed = r
                t_start = time.perf_counter()

                if algo_name == "GA":
                    ga = GeneticAlgorithm(
                        evaluator,
                        num_stores=num_stores,
                        pop_size=pop_size,
                        crossover_rate=ga_cfg.get("crossover_rate", 0.85),
                        mutation_rate=ga_cfg.get("mutation_rate", 0.15),
                        tournament_size=ga_cfg.get("tournament_size", 3),
                        blx_alpha=ga_cfg.get("blx_alpha", 0.5),
                        mutation_sigma=ga_cfg.get("gaussian_mutation_sigma", 40.0),
                        elitism_count=ga_cfg.get("elitism_count", 2),
                        seed=seed,
                    )
                    best_sol, best_fit, history = ga.optimize(max_evaluations=budget)
                    evals_curve = np.array([rec.evaluations for rec in history], dtype=np.int64)
                    fits_curve = np.array([rec.best_fitness for rec in history], dtype=np.float64)

                elif algo_name == "PSO":
                    pso = ParticleSwarmOptimization(
                        evaluator,
                        num_stores=num_stores,
                        num_particles=pop_size,
                        inertia_weight=pso_cfg.get("inertia_weight", 0.729),
                        inertia_decay=pso_cfg.get("inertia_decay", True),
                        inertia_max=pso_cfg.get("inertia_max", 0.9),
                        inertia_min=pso_cfg.get("inertia_min", 0.4),
                        c1_cognitive=pso_cfg.get("c1_cognitive", 1.494),
                        c2_social=pso_cfg.get("c2_social", 1.494),
                        v_max_fraction=pso_cfg.get("v_max_fraction", 0.15),
                        boundary_handling=pso_cfg.get("boundary_handling", "reflect"),
                        seed=seed,
                    )
                    best_sol, best_fit, history = pso.optimize(max_evaluations=budget)
                    evals_curve = np.array([rec.evaluations for rec in history], dtype=np.int64)
                    fits_curve = np.array([rec.gbest_fitness for rec in history], dtype=np.float64)

                else:  # ACO
                    aco = AntColonyOptimization(
                        evaluator,
                        num_stores=num_stores,
                        archive_size=aco_cfg.get("archive_size", 40),
                        num_ants=aco_cfg.get("num_ants", 20),
                        q_locality=aco_cfg.get("q_locality", 0.35),
                        xi_evaporation=aco_cfg.get("xi_evaporation", 0.70),
                        boundary_handling=aco_cfg.get("boundary_handling", "reflect"),
                        seed=seed,
                    )
                    best_sol, best_fit, history = aco.optimize(max_evaluations=budget)
                    evals_curve = np.array([rec.evaluations for rec in history], dtype=np.int64)
                    fits_curve = np.array([rec.best_fitness for rec in history], dtype=np.float64)

                t_elapsed = time.perf_counter() - t_start
                eval_95 = compute_eval_to_95_percent(evals_curve, fits_curve)

                coords_str = "; ".join([f"({best_sol[2*k]:.1f}, {best_sol[2*k+1]:.1f})" for k in range(num_stores)])
                primary_x = float(best_sol[0])
                primary_y = float(best_sol[1])

                raw_records.append({
                    "algoritma": algo_name,
                    "mode": mode,
                    "run": r,
                    "seed": seed,
                    "x": primary_x,
                    "y": primary_y,
                    "coords": coords_str,
                    "fitness": float(best_fit),
                    "waktu_detik": float(t_elapsed),
                    "evaluasi": int(evaluator.eval_count),
                    "evaluasi_ke_95persen": int(eval_95),
                })

                key_prefix = f"{mode}_{algo_name}_run{r}"
                convergence_dict[f"{key_prefix}_evals"] = evals_curve
                convergence_dict[f"{key_prefix}_fits"] = fits_curve

                completed_tasks += 1
                print_progress_bar(
                    completed_tasks,
                    total_tasks,
                    prefix=f"  {algo_name} [{mode}] Run {r:02d}/{num_runs}",
                )

    raw_df = pd.DataFrame(raw_records)
    csv_path = os.path.join(output_dir, "raw_runs.csv")
    raw_df.to_csv(csv_path, index=False)

    npz_path = os.path.join(output_dir, "convergence_data.npz")
    np.savez_compressed(npz_path, **convergence_dict)

    print("\n" + "=" * 75)
    print("EKSPERIMEN BATCH SELESAI SUKSES!")
    print(f"Data mentah tersimpan di       : {csv_path}")
    print(f"Kurva konvergensi tersimpan di : {npz_path}")
    print("=" * 75)

    return raw_df


def main():
    args = parse_arguments()
    modes = ["max", "min_valid"] if args.mode == "both" else [args.mode]
    run_batch_experiment(
        map_path=args.map,
        config_path=args.config,
        num_runs=args.runs,
        budget=args.budget,
        num_stores=args.p,
        modes=modes,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
