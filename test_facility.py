"""
Unit Test Komprehensif untuk Penempatan Puskesmas (test_facility.py)
Menggunakan pytest untuk menguji:
1. Counter evaluasi fitness (eval_count) dan isolasi prekomputasi heatmap
2. Penalti zona terlarang (sungai, sawah, hutan, tambang) dan luar batas peta
3. Mode maksimasi ('max') vs mode minimasi valid ('min_valid')
4. Reproducibility hasil dengan seed RNG (GA, PSO, ACO)
5. Algoritma geometri Ray-Casting dan jarak ortogonal koridor jalan
6. Penalti kanibalisasi fasilitas baru (p=2)
7. Matched budget protocol penghentian tepat pada 2000 evaluasi
8. Uji statistik Kruskal-Wallis dan post-hoc Mann-Whitney U
"""

import pytest
import numpy as np

from map_model import MapModel, point_in_polygon_vectorized
from fitness import FitnessEvaluator
from ga import GeneticAlgorithm
from pso import ParticleSwarmOptimization
from aco import AntColonyOptimization
from stats_utils import (
    compute_eval_to_95_percent,
    perform_kruskal_wallis_test,
    perform_pairwise_mann_whitney,
)


@pytest.fixture
def sample_map():
    map_dict = {
        "name": "Peta Uji Puskesmas",
        "dimensions": {"width": 1000.0, "height": 800.0},
        "houses": [
            {"x": 200.0, "y": 200.0, "weight": 4.0},
            {"x": 220.0, "y": 210.0, "weight": 3.5},
            {"x": 800.0, "y": 700.0, "weight": 1.0},
        ],
        "facilities": [
            {"type": "balai_desa", "x": 250.0, "y": 250.0, "weight": 2.0},
            {"type": "posyandu", "x": 300.0, "y": 300.0, "weight": 1.8},
        ],
        "competitors": [
            {"x": 280.0, "y": 260.0, "name": "Pustu Lama"},
        ],
        "roads": [
            {
                "name": "Jl. Utama",
                "class": "arteri",
                "traffic": 0.9,
                "points": [[0.0, 250.0], [500.0, 250.0], [1000.0, 250.0]],
            }
        ],
        "forbidden_zones": [
            {
                "name": "Bantaran Banjir",
                "type": "sungai",
                "polygon": [[400.0, 0.0], [450.0, 0.0], [450.0, 800.0], [400.0, 800.0]],
            }
        ],
    }
    return MapModel(map_dict)


def test_geometry_point_in_polygon():
    polygon = np.array([[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]])
    points = np.array([
        [200.0, 200.0],  # Di dalam
        [50.0, 50.0],    # Di luar
        [250.0, 150.0],  # Di dalam
        [350.0, 200.0],  # Di luar
    ])
    result = point_in_polygon_vectorized(points, polygon)
    assert result[0] == True
    assert result[1] == False
    assert result[2] == True
    assert result[3] == False


def test_evaluation_counter_and_heatmap(sample_map):
    evaluator = FitnessEvaluator(sample_map, mode="max")
    assert evaluator.eval_count == 0

    evaluator.evaluate(np.array([200.0, 200.0]))
    assert evaluator.eval_count == 1

    batch = np.array([[100.0, 100.0] for _ in range(5)])
    evaluator.evaluate_batch(batch)
    assert evaluator.eval_count == 6

    grid, extent = evaluator.compute_grid_heatmap(resolution_x=10, resolution_y=10)
    assert grid.shape == (10, 10)
    assert evaluator.eval_count == 6

    evaluator.reset_counter()
    assert evaluator.eval_count == 0


def test_forbidden_zone_and_oob_penalties(sample_map):
    evaluator = FitnessEvaluator(sample_map, mode="max")

    fit_valid = evaluator.evaluate(np.array([210.0, 250.0]))
    assert fit_valid > -100.0

    # Titik di zona terlarang (x: 400-450)
    fit_forbid = evaluator.evaluate(np.array([425.0, 400.0]))
    assert fit_forbid <= -evaluator.penalty_forbidden

    # Titik di luar batas peta
    fit_oob = evaluator.evaluate(np.array([-50.0, 300.0]))
    assert fit_oob <= -evaluator.penalty_out_of_bounds


def test_mode_min_valid(sample_map):
    eval_max = FitnessEvaluator(sample_map, mode="max")
    eval_min = FitnessEvaluator(sample_map, mode="min_valid")

    pt_ramai = np.array([210.0, 250.0])  # Di koridor jalan dekat pemukiman
    pt_sepi = np.array([900.0, 250.0])   # Di koridor jalan jauh dari pemukiman
    pt_forbid = np.array([425.0, 400.0])

    assert eval_max.evaluate(pt_ramai) > eval_max.evaluate(pt_sepi)
    assert eval_min.evaluate(pt_sepi) > eval_min.evaluate(pt_ramai)
    assert eval_min.evaluate(pt_forbid) <= -eval_min.penalty_forbidden


def test_cannibalization_p2(sample_map):
    evaluator = FitnessEvaluator(sample_map, num_stores=2, mode="max")

    sol_overlap = np.array([210.0, 250.0, 210.0, 250.0])
    sol_separated = np.array([210.0, 250.0, 800.0, 250.0])

    fit_overlap = evaluator.evaluate(sol_overlap)
    fit_separated = evaluator.evaluate(sol_separated)
    assert fit_separated > fit_overlap


def test_seed_reproducibility(sample_map):
    # 1. GA Reproducibility
    ev1 = FitnessEvaluator(sample_map, mode="max")
    ev2 = FitnessEvaluator(sample_map, mode="max")
    ga1 = GeneticAlgorithm(ev1, pop_size=20, seed=42)
    sol1, fit1, _ = ga1.optimize(max_evaluations=100)
    ga2 = GeneticAlgorithm(ev2, pop_size=20, seed=42)
    sol2, fit2, _ = ga2.optimize(max_evaluations=100)
    np.testing.assert_allclose(sol1, sol2, rtol=1e-5)
    assert fit1 == pytest.approx(fit2)

    # 2. PSO Reproducibility
    ev3 = FitnessEvaluator(sample_map, mode="max")
    ev4 = FitnessEvaluator(sample_map, mode="max")
    pso1 = ParticleSwarmOptimization(ev3, num_particles=20, seed=77)
    sol_pso1, fit_pso1, _ = pso1.optimize(max_evaluations=100)
    pso2 = ParticleSwarmOptimization(ev4, num_particles=20, seed=77)
    sol_pso2, fit_pso2, _ = pso2.optimize(max_evaluations=100)
    np.testing.assert_allclose(sol_pso1, sol_pso2, rtol=1e-5)
    assert fit_pso1 == pytest.approx(fit_pso2)

    # 3. ACO Reproducibility
    ev5 = FitnessEvaluator(sample_map, mode="max")
    ev6 = FitnessEvaluator(sample_map, mode="max")
    aco1 = AntColonyOptimization(ev5, archive_size=20, num_ants=10, seed=99)
    sol_aco1, fit_aco1, _ = aco1.optimize(max_evaluations=100)
    aco2 = AntColonyOptimization(ev6, archive_size=20, num_ants=10, seed=99)
    sol_aco2, fit_aco2, _ = aco2.optimize(max_evaluations=100)
    np.testing.assert_allclose(sol_aco1, sol_aco2, rtol=1e-5)
    assert fit_aco1 == pytest.approx(fit_aco2)


def test_matched_budget_limit(sample_map):
    budget = 120

    # GA
    ev_ga = FitnessEvaluator(sample_map)
    ga = GeneticAlgorithm(ev_ga, pop_size=20, seed=12)
    ga.optimize(max_evaluations=budget)
    assert ev_ga.eval_count == budget

    # PSO
    ev_pso = FitnessEvaluator(sample_map)
    pso = ParticleSwarmOptimization(ev_pso, num_particles=20, seed=12)
    pso.optimize(max_evaluations=budget)
    assert ev_pso.eval_count == budget

    # ACO
    ev_aco = FitnessEvaluator(sample_map)
    aco = AntColonyOptimization(ev_aco, archive_size=20, num_ants=10, seed=12)
    aco.optimize(max_evaluations=budget)
    assert ev_aco.eval_count == budget


def test_stats_utils():
    evals = np.array([10, 20, 30, 40, 50, 60])
    fits = np.array([0.1, 0.2, 0.5, 0.85, 0.96, 1.0])
    e95 = compute_eval_to_95_percent(evals, fits)
    assert e95 == 50

    data_dict = {
        "GA": np.array([0.80, 0.82, 0.81, 0.79, 0.83]),
        "PSO": np.array([0.90, 0.92, 0.91, 0.89, 0.93]),
        "ACO": np.array([0.88, 0.89, 0.87, 0.86, 0.90]),
    }
    kw_res = perform_kruskal_wallis_test(data_dict)
    assert kw_res["is_significant"] == True

    pw_res = perform_pairwise_mann_whitney(data_dict)
    assert len(pw_res) == 3
