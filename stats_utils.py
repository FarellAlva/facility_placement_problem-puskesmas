"""
Modul Utilitas Statistik Komparatif Puskesmas (stats_utils.py)
Menghitung metrik performa komparatif tiga algoritma metaheuristik:
Genetic Algorithm (GA), Particle Swarm Optimization (PSO), dan Ant Colony Optimization (ACO).

Fitur:
- Evaluasi menuju 95% fitness akhir (evaluasi_ke_95persen)
- Ringkasan statistik deskriptif (Mean, Std, Median, IQR, Min, Max, Waktu, Sukses Feasible %)
- Uji hipotesis non-parametrik omnibus Kruskal-Wallis H-test (3 algoritma)
- Post-hoc Pairwise Mann-Whitney U test dengan koreksi Bonferroni
- Penyusunan kesimpulan komparatif ilmiah otomatis dalam Bahasa Indonesia
"""

from typing import Dict, List, Tuple, Any, Optional
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from scipy import stats


def compute_eval_to_95_percent(
    evaluations: np.ndarray, fitness_history: np.ndarray
) -> int:
    """
    Menghitung jumlah evaluasi yang dibutuhkan algoritma untuk mencapai
    setidaknya 95% dari peningkatan fitness akhir:
        F_target = F_awal + 0.95 * (F_akhir - F_awal)
    """
    evals = np.asarray(evaluations, dtype=np.int64)
    fits = np.asarray(fitness_history, dtype=np.float64)

    if len(evals) == 0 or len(fits) == 0:
        return 0

    f_start = fits[0]
    f_final = fits[-1]
    delta = f_final - f_start

    if delta <= 1e-6:
        return int(evals[0])

    target = f_start + 0.95 * delta
    reached_indices = np.where(fits >= target)[0]

    if len(reached_indices) > 0:
        return int(evals[reached_indices[0]])
    return int(evals[-1])


def summarize_runs(df: pd.DataFrame, group_col: str = "algoritma") -> pd.DataFrame:
    """
    Menghasilkan ringkasan statistik deskriptif dari DataFrame hasil run.
    Metrik: Mean, Std, Median, IQR, Min, Max, Waktu, dan Tingkat Kelayakan Solusi.
    """
    summary_rows = []

    for group_name, group_data in df.groupby(group_col):
        fits = group_data["fitness"].to_numpy(dtype=np.float64)
        times = group_data["waktu_detik"].to_numpy(dtype=np.float64)
        evals_95 = group_data["evaluasi_ke_95persen"].to_numpy(dtype=np.float64)

        q25, q50, q75 = np.percentile(fits, [25, 50, 75])
        iqr = q75 - q25
        feasible_count = np.sum(fits >= 0.0)
        feasible_pct = (feasible_count / len(fits)) * 100.0 if len(fits) > 0 else 0.0

        summary_rows.append({
            "Algoritma": group_name,
            "Jumlah Run": len(fits),
            "Mean Fitness": np.mean(fits),
            "Std Fitness": np.std(fits, ddof=1) if len(fits) > 1 else 0.0,
            "Median Fitness": q50,
            "IQR Fitness": iqr,
            "Worst (Min)": np.min(fits),
            "Best (Max)": np.max(fits),
            "Feasible Solusi (%)": feasible_pct,
            "Mean Waktu (detik)": np.mean(times),
            "Std Waktu (detik)": np.std(times, ddof=1) if len(times) > 1 else 0.0,
            "Mean Eval ke-95%": np.mean(evals_95),
            "Median Eval ke-95%": np.median(evals_95),
        })

    summary_df = pd.DataFrame(summary_rows)
    return summary_df


def perform_kruskal_wallis_test(
    data_dict: Dict[str, np.ndarray],
    metric_name: str = "Nilai Fitness Akhir",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """
    Melakukan uji omnibus non-parametrik Kruskal-Wallis H-test
    untuk menguji apakah ada perbedaan signifikan secara global di antara 3 algoritma (GA, PSO, ACO).
    """
    groups = [np.asarray(vals, dtype=np.float64) for vals in data_dict.values()]
    algo_names = list(data_dict.keys())

    h_stat, p_val = stats.kruskal(*groups)
    is_significant = p_val < alpha

    if is_significant:
        kesimpulan = (
            f"Uji Kruskal-Wallis menunjukkan terdapat perbedaan yang SIGNIFIKAN secara global "
            f"di antara algoritma {', '.join(algo_names)} pada {metric_name} "
            f"(H = {h_stat:.4f}, p-value = {p_val:.5e} < {alpha})."
        )
    else:
        kesimpulan = (
            f"Uji Kruskal-Wallis menunjukkan TIDAK terdapat perbedaan yang signifikan secara statistik "
            f"di antara algoritma {', '.join(algo_names)} pada {metric_name} "
            f"(H = {h_stat:.4f}, p-value = {p_val:.5f} >= {alpha})."
        )

    return {
        "metric_name": metric_name,
        "h_statistic": float(h_stat),
        "p_value": float(p_val),
        "alpha": alpha,
        "is_significant": is_significant,
        "kesimpulan": kesimpulan,
    }


def perform_pairwise_mann_whitney(
    data_dict: Dict[str, np.ndarray],
    metric_name: str = "Nilai Fitness Akhir",
    higher_is_better: bool = True,
    alpha: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Melakukan uji post-hoc Pairwise Mann-Whitney U test untuk semua kombinasi pasangan
    dengan penyesuaian koreksi Bonferroni (alpha_adj = alpha / jumlah_pasangan).
    """
    algo_names = list(data_dict.keys())
    pairs = []
    for i in range(len(algo_names)):
        for j in range(i + 1, len(algo_names)):
            pairs.append((algo_names[i], algo_names[j]))

    num_comparisons = len(pairs)
    alpha_bonf = alpha / num_comparisons if num_comparisons > 0 else alpha

    results = []
    for a1, a2 in pairs:
        d1 = np.asarray(data_dict[a1], dtype=np.float64)
        d2 = np.asarray(data_dict[a2], dtype=np.float64)

        u_stat, p_val = stats.mannwhitneyu(d1, d2, alternative="two-sided")
        n1, n2 = len(d1), len(d2)
        rank_biserial = 1.0 - (2.0 * u_stat / (n1 * n2))

        med1 = float(np.median(d1))
        med2 = float(np.median(d2))
        is_sig = p_val < alpha_bonf

        if is_sig:
            if higher_is_better:
                winner = a1 if med1 > med2 else a2
            else:
                winner = a1 if med1 < med2 else a2
            narasi = (
                f"Perbedaan {a1} vs {a2} SIGNIFIKAN setelah koreksi Bonferroni (U = {u_stat:.2f}, "
                f"p-value = {p_val:.5e} < {alpha_bonf:.4f}). {winner} lebih unggul (Median {a1}={med1:.4f} vs {a2}={med2:.4f}, r={rank_biserial:.3f})."
            )
        else:
            narasi = (
                f"Perbedaan {a1} vs {a2} TIDAK signifikan setelah koreksi Bonferroni (U = {u_stat:.2f}, "
                f"p-value = {p_val:.5f} >= {alpha_bonf:.4f}). Keduanya berkinerja setara (Median {a1}={med1:.4f} vs {a2}={med2:.4f})."
            )

        results.append({
            "algo_1": a1,
            "algo_2": a2,
            "u_statistic": float(u_stat),
            "p_value": float(p_val),
            "alpha_bonferroni": float(alpha_bonf),
            "is_significant": is_sig,
            "rank_biserial": float(rank_biserial),
            "median_1": med1,
            "median_2": med2,
            "narasi": narasi,
        })

    return results
