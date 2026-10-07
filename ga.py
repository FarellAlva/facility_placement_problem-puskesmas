"""
Modul Algoritma Genetika Puskesmas (ga.py)
Implementasi Real-Coded Genetic Algorithm (RCGA) dari nol tanpa library optimasi eksternal.

Fitur:
- Representasi kromosom riil (panjang 2*p untuk p-fasilitas Puskesmas)
- Seleksi Tournament (Tournament Selection)
- Crossover BLX-alpha (Blend Crossover)
- Mutasi Gaussian adaptif dengan batasan wilayah
- Elitisme (mempertahankan individu terbaik tiap generasi)
- Penghentian tepat pada batas anggaran evaluasi (matched evaluation budget)
- Pencatatan riwayat lengkap tiap generasi untuk animasi dan visualisasi
- RNG reproducible dengan numpy.random.default_rng(seed)
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np

from fitness import FitnessEvaluator


@dataclass
class GAGenerationRecord:
    """Struktur data riwayat generasi GA untuk animasi dan analisis."""
    generation: int
    evaluations: int
    population: np.ndarray       # shape: (pop_size, 2*p)
    fitnesses: np.ndarray        # shape: (pop_size,)
    best_position: np.ndarray    # shape: (2*p,)
    best_fitness: float
    elite_indices: List[int]
    parent_pairs: List[Tuple[int, int]]  # Pasangan indeks induk untuk tiap anak baru
    mutated_mask: np.ndarray     # Boolean mask individu yang mengalami mutasi


class GeneticAlgorithm:
    """
    Kelas Genetic Algorithm Real-Coded untuk optimasi penempatan Puskesmas.
    """

    def __init__(
        self,
        evaluator: FitnessEvaluator,
        num_stores: int = 1,
        pop_size: int = 40,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.15,
        tournament_size: int = 3,
        blx_alpha: float = 0.5,
        mutation_sigma: float = 40.0,
        elitism_count: int = 2,
        seed: Optional[int] = 42,
    ):
        self.evaluator = evaluator
        self.num_facilities = num_stores
        self.dim = 2 * num_stores
        self.pop_size = pop_size
        self.pc = crossover_rate
        self.pm = mutation_rate
        self.tournament_size = tournament_size
        self.alpha = blx_alpha
        self.sigma_mut = mutation_sigma
        self.elitism_count = max(1, min(elitism_count, pop_size // 2))

        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.bounds_lower = np.tile([0.0, 0.0], self.num_facilities)
        self.bounds_upper = np.tile([self.evaluator.map.width, self.evaluator.map.height], self.num_facilities)

        self.history: List[GAGenerationRecord] = []
        self.best_solution: Optional[np.ndarray] = None
        self.best_fitness: float = -np.inf

    def _initialize_population(self) -> np.ndarray:
        pop = self.rng.uniform(
            low=self.bounds_lower,
            high=self.bounds_upper,
            size=(self.pop_size, self.dim),
        )
        return pop

    def _tournament_select(self, population: np.ndarray, fitnesses: np.ndarray) -> int:
        candidates = self.rng.choice(self.pop_size, size=self.tournament_size, replace=False)
        best_cand = candidates[0]
        best_fit = fitnesses[best_cand]
        for cand in candidates[1:]:
            if fitnesses[cand] > best_fit:
                best_cand = cand
                best_fit = fitnesses[cand]
        return int(best_cand)

    def _blx_alpha_crossover(
        self, parent1: np.ndarray, parent2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        child1 = np.empty(self.dim, dtype=np.float64)
        child2 = np.empty(self.dim, dtype=np.float64)

        for d in range(self.dim):
            p1_val = parent1[d]
            p2_val = parent2[d]
            c_min = min(p1_val, p2_val)
            c_max = max(p1_val, p2_val)
            diff = c_max - c_min
            lower_bound = c_min - self.alpha * diff
            upper_bound = c_max + self.alpha * diff

            child1[d] = self.rng.uniform(lower_bound, upper_bound)
            child2[d] = self.rng.uniform(lower_bound, upper_bound)

        child1 = np.clip(child1, self.bounds_lower, self.bounds_upper)
        child2 = np.clip(child2, self.bounds_lower, self.bounds_upper)
        return child1, child2

    def _gaussian_mutate(self, individual: np.ndarray) -> Tuple[np.ndarray, bool]:
        mutated = individual.copy()
        did_mutate = False

        for d in range(self.dim):
            if self.rng.random() < self.pm:
                noise = self.rng.normal(0.0, self.sigma_mut)
                mutated[d] += noise
                did_mutate = True

        if did_mutate:
            mutated = np.clip(mutated, self.bounds_lower, self.bounds_upper)

        return mutated, did_mutate

    def optimize(self, max_evaluations: int = 2000) -> Tuple[np.ndarray, float, List[GAGenerationRecord]]:
        self.history.clear()
        self.evaluator.reset_counter()

        population = self._initialize_population()
        fitnesses = np.empty(self.pop_size, dtype=np.float64)

        for i in range(self.pop_size):
            if self.evaluator.eval_count >= max_evaluations:
                fitnesses[i] = -self.evaluator.penalty_out_of_bounds
            else:
                fitnesses[i] = self.evaluator.evaluate(population[i])

        best_idx = int(np.argmax(fitnesses))
        self.best_fitness = float(fitnesses[best_idx])
        self.best_solution = population[best_idx].copy()

        sorted_indices = np.argsort(fitnesses)[::-1]
        elite_indices = list(sorted_indices[: self.elitism_count])

        self.history.append(
            GAGenerationRecord(
                generation=0,
                evaluations=self.evaluator.eval_count,
                population=population.copy(),
                fitnesses=fitnesses.copy(),
                best_position=self.best_solution.copy(),
                best_fitness=self.best_fitness,
                elite_indices=elite_indices,
                parent_pairs=[],
                mutated_mask=np.zeros(self.pop_size, dtype=bool),
            )
        )

        gen = 1
        while self.evaluator.eval_count < max_evaluations:
            new_population = np.empty_like(population)
            new_fitnesses = np.empty(self.pop_size, dtype=np.float64)
            mutated_mask = np.zeros(self.pop_size, dtype=bool)
            parent_pairs = []

            # 1. Elitisme
            sorted_idx = np.argsort(fitnesses)[::-1]
            elite_ptrs = []
            for e in range(self.elitism_count):
                idx = sorted_idx[e]
                new_population[e] = population[idx].copy()
                new_fitnesses[e] = fitnesses[idx]
                elite_ptrs.append(e)

            curr_idx = self.elitism_count

            # 2. Rekombinasi dan Mutasi
            while curr_idx < self.pop_size:
                p1_idx = self._tournament_select(population, fitnesses)
                p2_idx = self._tournament_select(population, fitnesses)
                parent1 = population[p1_idx]
                parent2 = population[p2_idx]

                if self.rng.random() < self.pc:
                    c1, c2 = self._blx_alpha_crossover(parent1, parent2)
                else:
                    c1 = parent1.copy()
                    c2 = parent2.copy()

                c1_mut, did_mut1 = self._gaussian_mutate(c1)
                c2_mut, did_mut2 = self._gaussian_mutate(c2)

                if curr_idx < self.pop_size:
                    new_population[curr_idx] = c1_mut
                    mutated_mask[curr_idx] = did_mut1
                    parent_pairs.append((p1_idx, p2_idx))

                    if self.evaluator.eval_count < max_evaluations:
                        new_fitnesses[curr_idx] = self.evaluator.evaluate(c1_mut)
                    else:
                        new_fitnesses[curr_idx] = -self.evaluator.penalty_out_of_bounds
                    curr_idx += 1

                if curr_idx < self.pop_size:
                    new_population[curr_idx] = c2_mut
                    mutated_mask[curr_idx] = did_mut2
                    parent_pairs.append((p2_idx, p1_idx))

                    if self.evaluator.eval_count < max_evaluations:
                        new_fitnesses[curr_idx] = self.evaluator.evaluate(c2_mut)
                    else:
                        new_fitnesses[curr_idx] = -self.evaluator.penalty_out_of_bounds
                    curr_idx += 1

            population = new_population
            fitnesses = new_fitnesses

            best_idx_gen = int(np.argmax(fitnesses))
            if fitnesses[best_idx_gen] > self.best_fitness:
                self.best_fitness = float(fitnesses[best_idx_gen])
                self.best_solution = population[best_idx_gen].copy()

            sorted_gen = np.argsort(fitnesses)[::-1]
            gen_elites = list(sorted_gen[: self.elitism_count])

            self.history.append(
                GAGenerationRecord(
                    generation=gen,
                    evaluations=self.evaluator.eval_count,
                    population=population.copy(),
                    fitnesses=fitnesses.copy(),
                    best_position=self.best_solution.copy(),
                    best_fitness=self.best_fitness,
                    elite_indices=gen_elites,
                    parent_pairs=parent_pairs,
                    mutated_mask=mutated_mask,
                )
            )

            gen += 1

        return self.best_solution, self.best_fitness, self.history
