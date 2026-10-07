"""
Modul Particle Swarm Optimization Puskesmas (pso.py)
Implementasi PSO kontinu dari nol tanpa library eksternal.

Fitur:
- Posisi partikel berdimensi 2*p (koordinat x, y untuk p-fasilitas Puskesmas)
- Kecepatan dengan pembatasan Vmax (v_max_fraction)
- Bobot inersia adaptif (peluruhan linier w_max ke w_min)
- Komponen kognitif (c1) dan sosial (c2)
- Penanganan batas: 'reflect' (memantul) atau 'clamp' (menempel)
- Pelacakan pbest (personal best) dan gbest (global best)
- Penghentian tepat pada batas anggaran evaluasi (matched budget)
- Riwayat lengkap tiap iterasi untuk animasi dan visualisasi
- RNG reproducible dengan numpy.random.default_rng(seed)
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np

from fitness import FitnessEvaluator


@dataclass
class PSOIterationRecord:
    """Struktur data riwayat iterasi PSO untuk visualisasi dan animasi."""
    iteration: int
    evaluations: int
    positions: np.ndarray        # shape: (num_particles, 2*p)
    velocities: np.ndarray       # shape: (num_particles, 2*p)
    fitnesses: np.ndarray        # shape: (num_particles,)
    pbest_positions: np.ndarray  # shape: (num_particles, 2*p)
    pbest_fitnesses: np.ndarray  # shape: (num_particles,)
    gbest_position: np.ndarray   # shape: (2*p,)
    gbest_fitness: float


class ParticleSwarmOptimization:
    """
    Kelas Particle Swarm Optimization untuk penempatan Puskesmas.
    """

    def __init__(
        self,
        evaluator: FitnessEvaluator,
        num_stores: int = 1,
        num_particles: int = 40,
        inertia_weight: float = 0.729,
        inertia_decay: bool = True,
        inertia_max: float = 0.9,
        inertia_min: float = 0.4,
        c1_cognitive: float = 1.494,
        c2_social: float = 1.494,
        v_max_fraction: float = 0.15,
        boundary_handling: str = "reflect",
        seed: Optional[int] = 42,
    ):
        self.evaluator = evaluator
        self.num_facilities = num_stores
        self.dim = 2 * num_stores
        self.num_particles = num_particles

        self.w = inertia_weight
        self.inertia_decay = inertia_decay
        self.w_max = inertia_max
        self.w_min = inertia_min
        self.c1 = c1_cognitive
        self.c2 = c2_social

        self.v_max_fraction = v_max_fraction
        self.boundary_handling = boundary_handling.lower()
        if self.boundary_handling not in ("clamp", "reflect"):
            raise ValueError(f"Metode penanganan batas '{boundary_handling}' tidak dikenal.")

        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.bounds_lower = np.tile([0.0, 0.0], self.num_facilities)
        self.bounds_upper = np.tile([self.evaluator.map.width, self.evaluator.map.height], self.num_facilities)

        range_span = self.bounds_upper - self.bounds_lower
        self.v_max = self.v_max_fraction * range_span

        self.history: List[PSOIterationRecord] = []
        self.gbest_position: Optional[np.ndarray] = None
        self.gbest_fitness: float = -np.inf

    def _initialize_swarm(self) -> Tuple[np.ndarray, np.ndarray]:
        positions = self.rng.uniform(
            low=self.bounds_lower,
            high=self.bounds_upper,
            size=(self.num_particles, self.dim),
        )
        velocities = self.rng.uniform(
            low=-self.v_max,
            high=self.v_max,
            size=(self.num_particles, self.dim),
        )
        return positions, velocities

    def _apply_boundary(self, positions: np.ndarray, velocities: np.ndarray) -> None:
        if self.boundary_handling == "clamp":
            for d in range(self.dim):
                low_mask = positions[:, d] < self.bounds_lower[d]
                high_mask = positions[:, d] > self.bounds_upper[d]
                positions[low_mask, d] = self.bounds_lower[d]
                velocities[low_mask, d] = 0.0
                positions[high_mask, d] = self.bounds_upper[d]
                velocities[high_mask, d] = 0.0

        elif self.boundary_handling == "reflect":
            for d in range(self.dim):
                low_mask = positions[:, d] < self.bounds_lower[d]
                if np.any(low_mask):
                    positions[low_mask, d] = 2.0 * self.bounds_lower[d] - positions[low_mask, d]
                    velocities[low_mask, d] = -velocities[low_mask, d]
                    positions[low_mask, d] = np.clip(positions[low_mask, d], self.bounds_lower[d], self.bounds_upper[d])

                high_mask = positions[:, d] > self.bounds_upper[d]
                if np.any(high_mask):
                    positions[high_mask, d] = 2.0 * self.bounds_upper[d] - positions[high_mask, d]
                    velocities[high_mask, d] = -velocities[high_mask, d]
                    positions[high_mask, d] = np.clip(positions[high_mask, d], self.bounds_lower[d], self.bounds_upper[d])

    def optimize(self, max_evaluations: int = 2000) -> Tuple[np.ndarray, float, List[PSOIterationRecord]]:
        self.history.clear()
        self.evaluator.reset_counter()

        positions, velocities = self._initialize_swarm()
        fitnesses = np.empty(self.num_particles, dtype=np.float64)

        for i in range(self.num_particles):
            if self.evaluator.eval_count < max_evaluations:
                fitnesses[i] = self.evaluator.evaluate(positions[i])
            else:
                fitnesses[i] = -self.evaluator.penalty_out_of_bounds

        pbest_positions = positions.copy()
        pbest_fitnesses = fitnesses.copy()

        best_idx = int(np.argmax(pbest_fitnesses))
        self.gbest_fitness = float(pbest_fitnesses[best_idx])
        self.gbest_position = pbest_positions[best_idx].copy()

        estimated_max_iter = max(1, (max_evaluations - self.num_particles) // self.num_particles + 1)

        self.history.append(
            PSOIterationRecord(
                iteration=0,
                evaluations=self.evaluator.eval_count,
                positions=positions.copy(),
                velocities=velocities.copy(),
                fitnesses=fitnesses.copy(),
                pbest_positions=pbest_positions.copy(),
                pbest_fitnesses=pbest_fitnesses.copy(),
                gbest_position=self.gbest_position.copy(),
                gbest_fitness=self.gbest_fitness,
            )
        )

        iter_count = 1
        while self.evaluator.eval_count < max_evaluations:
            if self.inertia_decay:
                w_curr = self.w_max - (self.w_max - self.w_min) * min(1.0, iter_count / estimated_max_iter)
            else:
                w_curr = self.w

            for i in range(self.num_particles):
                r1 = self.rng.uniform(0.0, 1.0, size=self.dim)
                r2 = self.rng.uniform(0.0, 1.0, size=self.dim)

                cognitive = self.c1 * r1 * (pbest_positions[i] - positions[i])
                social = self.c2 * r2 * (self.gbest_position - positions[i])

                new_v = w_curr * velocities[i] + cognitive + social
                velocities[i] = np.clip(new_v, -self.v_max, self.v_max)
                positions[i] = positions[i] + velocities[i]

            self._apply_boundary(positions, velocities)

            for i in range(self.num_particles):
                if self.evaluator.eval_count < max_evaluations:
                    fit = self.evaluator.evaluate(positions[i])
                    fitnesses[i] = fit

                    if fit > pbest_fitnesses[i]:
                        pbest_fitnesses[i] = fit
                        pbest_positions[i] = positions[i].copy()

                        if fit > self.gbest_fitness:
                            self.gbest_fitness = float(fit)
                            self.gbest_position = positions[i].copy()
                else:
                    break

            self.history.append(
                PSOIterationRecord(
                    iteration=iter_count,
                    evaluations=self.evaluator.eval_count,
                    positions=positions.copy(),
                    velocities=velocities.copy(),
                    fitnesses=fitnesses.copy(),
                    pbest_positions=pbest_positions.copy(),
                    pbest_fitnesses=pbest_fitnesses.copy(),
                    gbest_position=self.gbest_position.copy(),
                    gbest_fitness=self.gbest_fitness,
                )
            )

            iter_count += 1

        return self.gbest_position, self.gbest_fitness, self.history
