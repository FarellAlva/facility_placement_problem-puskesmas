"""
Modul Ant Colony Optimization Puskesmas (aco.py)
Implementasi Continuous Ant Colony Optimization (ACOR / ACO_R)
dari nol murni menggunakan NumPy tanpa ketergantungan library optimasi pihak ketiga.

Berdasarkan formulasi standar Socha & Dorigo (2008):
"Ant colony optimization for continuous domains", European Journal of Operational Research.

Fitur:
- Solution Archive berukuran k solusi terbaik yang diurutkan berdasarkan nilai fitness
- Pheromone Representation: Fungsi Kepadatan Probabilitas Kernel Gaussian Multi-modal
- Bobot seleksi feromon non-linear berbasis parameter lokalitas q
- Dispersi feromon adaptif dengan faktor penguapan/penyusutan xi
- Konstruksi koordinat semut multi-dimensi (2*p untuk p-fasilitas Puskesmas)
- Penanganan batasan spasial wilayah (refleksi dan jepit batas peta)
- Pembaruan feromon & evaporasi otomatis melalui pemangkasan arsip solusi
- Penghentian tepat pada batas anggaran evaluasi (matched budget protocol)
- Pencatatan riwayat iterasi lengkap untuk visualisasi animasi kanvas grafis
- RNG reproducible dengan numpy.random.default_rng(seed)
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np

from fitness import FitnessEvaluator


@dataclass
class ACOIterationRecord:
    """Struktur data riwayat iterasi ACO untuk visualisasi dan animasi."""
    iteration: int
    evaluations: int
    ant_positions: np.ndarray       # Posisi semut baru yang dikonstruksi pada iterasi ini: (num_ants, 2*p)
    ant_fitnesses: np.ndarray       # Nilai fitness semut baru: (num_ants,)
    archive_positions: np.ndarray   # Solusi arsip feromon aktif (pusat feromon): (archive_size, 2*p)
    archive_fitnesses: np.ndarray   # Nilai fitness solusi arsip: (archive_size,)
    guide_indices: List[int]        # Indeks solusi arsip yang menjadi pemandu tiap semut
    best_position: np.ndarray       # Posisi solusi terbaik global saat ini: (2*p,)
    best_fitness: float             # Nilai fitness terbaik global saat ini


class AntColonyOptimization:
    """
    Kelas Continuous Ant Colony Optimization (ACOR) untuk penempatan fasilitas Puskesmas.
    """

    def __init__(
        self,
        evaluator: FitnessEvaluator,
        num_stores: int = 1,
        archive_size: int = 40,
        num_ants: int = 20,
        q_locality: float = 0.35,
        xi_evaporation: float = 0.70,
        boundary_handling: str = "reflect",
        seed: Optional[int] = 42,
    ):
        self.evaluator = evaluator
        self.num_facilities = num_stores
        self.dim = 2 * num_stores
        self.k = archive_size          # Ukuran arsip solusi (k)
        self.m = num_ants              # Jumlah semut yang dieksplorasi per iterasi (m)
        self.q = q_locality            # Parameter intensitas seleksi lokalitas feromon
        self.xi = xi_evaporation        # Tingkat dispersi/evaporasi feromon
        self.boundary_handling = boundary_handling.lower()

        if self.boundary_handling not in ("clamp", "reflect"):
            raise ValueError(f"Metode batas '{boundary_handling}' tidak dikenal. Gunakan 'clamp' atau 'reflect'.")

        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.bounds_lower = np.tile([0.0, 0.0], self.num_facilities)
        self.bounds_upper = np.tile([self.evaluator.map.width, self.evaluator.map.height], self.num_facilities)

        # Hitung bobot pemilihan statis untuk peringkat 0..k-1
        ranks = np.arange(self.k)
        weights = (1.0 / (self.q * self.k * np.sqrt(2.0 * np.pi))) * np.exp(
            -(ranks ** 2) / (2.0 * ((self.q * self.k) ** 2))
        )
        self.weights = weights
        self.probabilities = weights / np.sum(weights)

        self.history: List[ACOIterationRecord] = []
        self.best_solution: Optional[np.ndarray] = None
        self.best_fitness: float = -np.inf

    def _initialize_archive(self) -> np.ndarray:
        """Inisialisasi k solusi awal secara acak seragam di dalam batas wilayah."""
        return self.rng.uniform(
            low=self.bounds_lower,
            high=self.bounds_upper,
            size=(self.k, self.dim),
        )

    def _apply_boundary(self, position: np.ndarray) -> np.ndarray:
        """Menangani koordinat semut yang keluar dari batas peta wilayah."""
        pos = position.copy()
        if self.boundary_handling == "clamp":
            pos = np.clip(pos, self.bounds_lower, self.bounds_upper)
        elif self.boundary_handling == "reflect":
            for d in range(self.dim):
                if pos[d] < self.bounds_lower[d]:
                    pos[d] = 2.0 * self.bounds_lower[d] - pos[d]
                    pos[d] = np.clip(pos[d], self.bounds_lower[d], self.bounds_upper[d])
                elif pos[d] > self.bounds_upper[d]:
                    pos[d] = 2.0 * self.bounds_upper[d] - pos[d]
                    pos[d] = np.clip(pos[d], self.bounds_lower[d], self.bounds_upper[d])
        return pos

    def optimize(self, max_evaluations: int = 2000) -> Tuple[np.ndarray, float, List[ACOIterationRecord]]:
        """
        Menjalankan algoritma Continuous ACO hingga anggaran evaluasi maksimal tercapai.
        """
        self.history.clear()
        self.evaluator.reset_counter()

        # 1. Inisialisasi dan Evaluasi Arsip Solusi (Generasi 0)
        archive_pop = self._initialize_archive()
        archive_fits = np.empty(self.k, dtype=np.float64)

        for i in range(self.k):
            if self.evaluator.eval_count < max_evaluations:
                archive_fits[i] = self.evaluator.evaluate(archive_pop[i])
            else:
                archive_fits[i] = -self.evaluator.penalty_out_of_bounds

        # Urutkan arsip berdasarkan fitness secara menurun (ranking 0 = solusi terbaik)
        sort_order = np.argsort(archive_fits)[::-1]
        archive_pop = archive_pop[sort_order]
        archive_fits = archive_fits[sort_order]

        self.best_fitness = float(archive_fits[0])
        self.best_solution = archive_pop[0].copy()

        # Catat iterasi 0
        self.history.append(
            ACOIterationRecord(
                iteration=0,
                evaluations=self.evaluator.eval_count,
                ant_positions=archive_pop.copy(),
                ant_fitnesses=archive_fits.copy(),
                archive_positions=archive_pop.copy(),
                archive_fitnesses=archive_fits.copy(),
                guide_indices=list(range(min(self.m, self.k))),
                best_position=self.best_solution.copy(),
                best_fitness=self.best_fitness,
            )
        )

        iter_count = 1
        # Loop konstruksi koloni semut selama anggaran evaluasi masih tersedia
        while self.evaluator.eval_count < max_evaluations:
            new_ants = []
            new_fits = []
            guide_indices = []

            # 2. Konstruksi Solusi oleh m Ekor Semut
            for ant_idx in range(self.m):
                if self.evaluator.eval_count >= max_evaluations:
                    break

                # Pilih pemandu dari arsip menggunakan distribusi probabilitas p_l
                l = int(self.rng.choice(self.k, p=self.probabilities))
                guide_indices.append(l)
                guide_sol = archive_pop[l]

                # Bangun posisi baru untuk setiap dimensi secara independen
                ant_pos = np.empty(self.dim, dtype=np.float64)
                for d in range(self.dim):
                    # Hitung deviasi standar dispersi feromon sigma_l^d
                    sigma_ld = self.xi * float(np.sum(np.abs(archive_pop[:, d] - guide_sol[d]))) / max(1, self.k - 1)
                    # Berikan ambang batas deviasi minimum untuk menjaga kapabilitas eksplorasi
                    sigma_ld = max(sigma_ld, 2.0)

                    # Cuplik sampel Gaussian di sekitar posisi pemandu
                    ant_pos[d] = self.rng.normal(loc=guide_sol[d], scale=sigma_ld)

                # Terapkan batasan wilayah
                ant_pos = self._apply_boundary(ant_pos)

                # Evaluasi kebugaran semut
                fit = self.evaluator.evaluate(ant_pos)
                new_ants.append(ant_pos)
                new_fits.append(fit)

            if len(new_ants) == 0:
                break

            new_ants_arr = np.array(new_ants, dtype=np.float64)
            new_fits_arr = np.array(new_fits, dtype=np.float64)

            # 3. Pembaruan Arsip Feromon & Evaporasi
            # Gabungkan semut baru dengan arsip aktif (total k + m solusi)
            combined_pop = np.vstack([archive_pop, new_ants_arr])
            combined_fits = np.concatenate([archive_fits, new_fits_arr])

            # Urutkan seluruh solusi berdasarkan fitness menurun
            sorted_idx = np.argsort(combined_fits)[::-1]

            # Pertahankan hanya k solusi terbaik (solusi terburuk terevaporasi/dieliminasi)
            archive_pop = combined_pop[sorted_idx[: self.k]]
            archive_fits = combined_fits[sorted_idx[: self.k]]

            # Perbarui solusi terbaik global jika ditemukan kandidat lebih unggul
            if archive_fits[0] > self.best_fitness:
                self.best_fitness = float(archive_fits[0])
                self.best_solution = archive_pop[0].copy()

            # Catat record iterasi
            self.history.append(
                ACOIterationRecord(
                    iteration=iter_count,
                    evaluations=self.evaluator.eval_count,
                    ant_positions=new_ants_arr.copy(),
                    ant_fitnesses=new_fits_arr.copy(),
                    archive_positions=archive_pop.copy(),
                    archive_fitnesses=archive_fits.copy(),
                    guide_indices=guide_indices,
                    best_position=self.best_solution.copy(),
                    best_fitness=self.best_fitness,
                )
            )

            iter_count += 1

        return self.best_solution, self.best_fitness, self.history
