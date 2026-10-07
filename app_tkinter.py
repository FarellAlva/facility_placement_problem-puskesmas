"""
Aplikasi GUI Interaktif Penentuan Lokasi Fasilitas Puskesmas (app_tkinter.py)
Menyediakan visualisasi interaktif penuh untuk membandingkan tiga algoritma metaheuristik:
1. Genetic Algorithm (GA) — Seleksi Alam, Rekombinasi BLX-alpha, Mutasi Gaussian & Elitisme
2. Particle Swarm Optimization (PSO) — Swarm Intelligence, Vektor Kecepatan & Inersia Adaptif
3. Ant Colony Optimization (ACO) — Continuous ACOR, Arsip Solusi & Kepadatan Feromon Gaussian

Fitur Utama:
- Tampilan Multi-Mode: Split 3-Algoritma (GA vs PSO vs ACO bersamaan), Layar Penuh GA, Layar Penuh PSO,
  Layar Penuh ACO, serta Layar Penuh Kurva Konvergensi 3 Algoritma.
- Kontrol Simulasi Lengkap: Play/Pause, Step, Reset, Run to End, dan Slider Kecepatan Animasi.
- Sensitivity Analysis Dinamis: Slider Bobot Kriteria (Warga, Ambulans, Fasilitas, Faskes Eksisting)
  dengan pembaruan live heatmap kesesuaian lokasi.
- Fitur Inspeksi Spasial (Klik Peta): Klik koordinat manapun untuk membedah status zonasi, legalitas,
  jarak jalan ambulans, skor 4 kriteria, dan total estimasi fitness.
- Papan Skor Komparatif Live (Scoreboard) yang membandingkan performa ketiga algoritma secara real-time.

Jalankan dengan:
    python app_tkinter.py
"""

import sys
import os
import json
import time
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches

from map_model import MapModel, plot_map
from fitness import FitnessEvaluator
from ga import GeneticAlgorithm, GAGenerationRecord
from pso import ParticleSwarmOptimization, PSOIterationRecord
from aco import AntColonyOptimization, ACOIterationRecord


class PuskesmasOptimizationApp:
    """
    Kelas utama GUI Desktop Tkinter untuk visualisasi komparasi GA, PSO, dan ACO.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simulasi Optimasi Penempatan Fasilitas Puskesmas: GA vs PSO vs ACO")
        self.root.geometry("1480x920")
        self.root.minsize(1150, 720)

        self._setup_styles()

        # Konfigurasi Peta & Model
        self.config_path = "config.json"
        self._load_config()

        self.current_map_file = "maps/peta_studi.json"
        self.map_model = MapModel.load_from_json(self.current_map_file)

        # Mode Tampilan: 'split_3', 'ga', 'pso', 'aco', 'conv'
        self.view_mode = "split_3"
        self.last_inspected_pt: Optional[Tuple[float, float]] = None

        # Variabel Kontrol
        self.mode_var = tk.StringVar(value="max")
        self.facilities_var = tk.IntVar(value=1)
        self.budget_var = tk.IntVar(value=2000)
        self.speed_var = tk.IntVar(value=80)

        # Bobot Kriteria
        weights = self.config.get("fitness_weights", {})
        self.w1_var = tk.DoubleVar(value=weights.get("w1_populasi", 0.35))
        self.w2_var = tk.DoubleVar(value=weights.get("w2_akses_jalan", 0.30))
        self.w3_var = tk.DoubleVar(value=weights.get("w3_fasilitas", 0.20))
        self.w4_var = tk.DoubleVar(value=weights.get("w4_faskes_kompetitor", 0.15))

        # Status Playback
        self.is_running = False
        self.current_frame = 0
        self.total_frames = 0
        self.timer_id = None

        # Riwayat Optimasi
        self.ga_history: List[GAGenerationRecord] = []
        self.pso_history: List[PSOIterationRecord] = []
        self.aco_history: List[ACOIterationRecord] = []
        self.ga_best_sol = None
        self.ga_best_fit = -np.inf
        self.pso_best_sol = None
        self.pso_best_fit = -np.inf
        self.aco_best_sol = None
        self.aco_best_fit = -np.inf

        # Inisialisasi Tampilan
        self._build_header()
        self._build_main_interface()

        # Eksekusi komputasi pertama
        self._recompute_optimization(reset_playback=True)

    def _setup_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(background="#0f172a")
        self.style.configure(".", background="#0f172a", foreground="#f8fafc")
        self.style.configure("TFrame", background="#0f172a")
        self.style.configure("Card.TFrame", background="#1e293b", relief="flat")
        self.style.configure("TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 9))
        self.style.configure("Card.TLabel", background="#1e293b", foreground="#f8fafc", font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background="#0f172a", foreground="#38bdf8", font=("Segoe UI", 12, "bold"))
        self.style.configure("SubHeader.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 8))

        self.style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background="#0284c7", foreground="#ffffff")
        self.style.configure("Play.TButton", font=("Segoe UI", 9, "bold"), background="#10b981", foreground="#ffffff")
        self.style.configure("Pause.TButton", font=("Segoe UI", 9, "bold"), background="#f59e0b", foreground="#ffffff")
        self.style.configure("Reset.TButton", font=("Segoe UI", 9, "bold"), background="#ef4444", foreground="#ffffff")
        self.style.configure("View.TButton", font=("Segoe UI", 8, "bold"), background="#334155", foreground="#f8fafc")
        self.style.configure("ActiveView.TButton", font=("Segoe UI", 8, "bold"), background="#38bdf8", foreground="#0f172a")

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "fitness_weights": {"w1_populasi": 0.35, "w2_akses_jalan": 0.30, "w3_fasilitas": 0.20, "w4_faskes_kompetitor": 0.15},
                "facility": {"num_facilities": 1},
                "optimization": {"population_size": 40},
            }

    def _build_header(self):
        hdr = ttk.Frame(self.root, padding=(14, 8, 14, 6))
        hdr.pack(fill=tk.X, side=tk.TOP)

        title_box = ttk.Frame(hdr)
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        lbl_t = ttk.Label(
            title_box,
            text="🏥 SIMULASI OPTIMASI LOKASI PUSKESMAS — GA vs PSO vs ACO",
            font=("Segoe UI", 13, "bold"),
            foreground="#38bdf8",
        )
        lbl_t.pack(anchor="w")

        lbl_sub = ttk.Label(
            title_box,
            text="Studi Komparasi Metaheuristik Spasial: Algoritma Genetika, Particle Swarm, dan Continuous Ant Colony",
            font=("Segoe UI", 8),
            foreground="#94a3b8",
        )
        lbl_sub.pack(anchor="w")

        # Status badge di kanan
        self.status_badge = tk.Label(
            hdr,
            text="STATUS: SIAP",
            font=("Segoe UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            padx=12,
            pady=4,
            relief="solid",
            bd=1,
        )
        self.status_badge.pack(side=tk.RIGHT, padx=6)

    def _build_main_interface(self):
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Panel Kiri: Kontrol & Parameter (Lebar ~360px)
        self.left_panel = ttk.Frame(self.main_paned, width=380)
        self.main_paned.add(self.left_panel, weight=0)

        # Panel Kanan: Canvas Visualisasi Matplotlib
        self.right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_panel, weight=1)

        self._build_sidebar_controls()
        self._build_visualization_panel()

    def _build_sidebar_controls(self):
        nb = ttk.Notebook(self.left_panel)
        nb.pack(fill=tk.BOTH, expand=True)

        tab_sim = ttk.Frame(nb, padding=8)
        tab_weights = ttk.Frame(nb, padding=8)
        tab_inspect = ttk.Frame(nb, padding=8)
        tab_about = ttk.Frame(nb, padding=8)

        nb.add(tab_sim, text="⚙️ Simulasi")
        nb.add(tab_weights, text="⚖️ Bobot Kriteria")
        nb.add(tab_inspect, text="🔍 Inspeksi Titik")
        nb.add(tab_about, text="ℹ️ Edukasi 3 Algo")

        self._build_tab_simulasi(tab_sim)
        self._build_tab_bobot(tab_weights)
        self._build_tab_inspeksi(tab_inspect)
        self._build_tab_edukasi(tab_about)

    def _build_tab_simulasi(self, parent):
        # 1. Kontrol Tampilan (View Mode)
        card_view = ttk.LabelFrame(parent, text=" 🖥️ Mode Tampilan Kanvas ", padding=8)
        card_view.pack(fill=tk.X, pady=(0, 8))

        btn_row1 = ttk.Frame(card_view)
        btn_row1.pack(fill=tk.X, pady=2)
        self.btn_v_split = ttk.Button(btn_row1, text="Split 3-Algo", command=lambda: self._set_view_mode("split_3"), style="ActiveView.TButton")
        self.btn_v_split.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_v_conv = ttk.Button(btn_row1, text="Konvergensi", command=lambda: self._set_view_mode("conv"), style="View.TButton")
        self.btn_v_conv.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_row2 = ttk.Frame(card_view)
        btn_row2.pack(fill=tk.X, pady=2)
        self.btn_v_ga = ttk.Button(btn_row2, text="Layar GA", command=lambda: self._set_view_mode("ga"), style="View.TButton")
        self.btn_v_ga.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_v_pso = ttk.Button(btn_row2, text="Layar PSO", command=lambda: self._set_view_mode("pso"), style="View.TButton")
        self.btn_v_pso.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_v_aco = ttk.Button(btn_row2, text="Layar ACO", command=lambda: self._set_view_mode("aco"), style="View.TButton")
        self.btn_v_aco.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # 2. Mode Optimasi
        card_mode = ttk.LabelFrame(parent, text=" 🎯 Sasaran Optimasi ", padding=8)
        card_mode.pack(fill=tk.X, pady=(0, 8))

        rb1 = ttk.Radiobutton(
            card_mode, text="Maksimasi (Cari Lokasi Terbaik Puskesmas)",
            variable=self.mode_var, value="max", command=self._on_param_change
        )
        rb1.pack(anchor="w", pady=2)

        rb2 = ttk.Radiobutton(
            card_mode, text="Minimasi Valid (Cari Lokasi Terburuk Legal)",
            variable=self.mode_var, value="min_valid", command=self._on_param_change
        )
        rb2.pack(anchor="w", pady=2)

        # 3. Kontrol Playback
        card_play = ttk.LabelFrame(parent, text=" ⏯️ Kontrol Animasi Iterasi ", padding=8)
        card_play.pack(fill=tk.X, pady=(0, 8))

        row_ctrl = ttk.Frame(card_play)
        row_ctrl.pack(fill=tk.X, pady=3)

        self.btn_play = ttk.Button(row_ctrl, text="▶ Mulai", command=self._toggle_play, style="Play.TButton")
        self.btn_play.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.btn_step = ttk.Button(row_ctrl, text="⏭️ Step", command=self._step_frame, style="Action.TButton")
        self.btn_step.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.btn_reset = ttk.Button(row_ctrl, text="⏮️ Reset", command=self._reset_playback, style="Reset.TButton")
        self.btn_reset.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        btn_end = ttk.Button(card_play, text="🏁 Selesaikan Langsung (Run to End)", command=self._run_to_end, style="Action.TButton")
        btn_end.pack(fill=tk.X, pady=(4, 2))

        # Slider Progress
        row_prog = ttk.Frame(card_play)
        row_prog.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(row_prog, text="Langkah:").pack(side=tk.LEFT)
        self.lbl_frame_info = ttk.Label(row_prog, text="0 / 0", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        self.lbl_frame_info.pack(side=tk.RIGHT)

        self.scale_frame = ttk.Scale(card_play, from_=0, to=100, orient=tk.HORIZONTAL, command=self._on_slider_frame_changed)
        self.scale_frame.pack(fill=tk.X, pady=2)

        # Slider Kecepatan Delay
        row_spd = ttk.Frame(card_play)
        row_spd.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(row_spd, text="Delay Animasi:").pack(side=tk.LEFT)
        self.lbl_speed_val = ttk.Label(row_spd, text="80 ms", foreground="#facc15")
        self.lbl_speed_val.pack(side=tk.RIGHT)

        scale_spd = ttk.Scale(card_play, from_=10, to=300, orient=tk.HORIZONTAL, variable=self.speed_var, command=self._on_speed_changed)
        scale_spd.pack(fill=tk.X, pady=2)

        # 4. Papan Skor Komparatif 3 Algoritma (Scoreboard)
        card_score = ttk.LabelFrame(parent, text=" 📊 Papan Skor Komparatif Live ", padding=8)
        card_score.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.score_tree = ttk.Treeview(card_score, columns=("algo", "fit", "coords", "evals"), show="headings", height=3)
        self.score_tree.heading("algo", text="Algoritma")
        self.score_tree.heading("fit", text="Best Fitness")
        self.score_tree.heading("coords", text="Koordinat Puskesmas")
        self.score_tree.heading("evals", text="Evaluasi")

        self.score_tree.column("algo", width=70, anchor="center")
        self.score_tree.column("fit", width=80, anchor="center")
        self.score_tree.column("coords", width=110, anchor="center")
        self.score_tree.column("evals", width=60, anchor="center")
        self.score_tree.pack(fill=tk.BOTH, expand=True)

        self.score_tree.insert("", "end", iid="GA", values=("GA", "-", "-", "-"))
        self.score_tree.insert("", "end", iid="PSO", values=("PSO", "-", "-", "-"))
        self.score_tree.insert("", "end", iid="ACO", values=("ACO", "-", "-", "-"))

    def _build_tab_bobot(self, parent):
        ttk.Label(
            parent,
            text="Analisis Sensitivitas Bobot Kriteria Puskesmas:\nAtur proporsi kriteria lalu tekan 'Hitung Ulang'.",
            foreground="#94a3b8",
            wraplength=340,
        ).pack(anchor="w", pady=(0, 8))

        def add_weight_slider(label, var, color):
            box = ttk.Frame(parent)
            box.pack(fill=tk.X, pady=4)
            lbl_b = ttk.Label(box, text=label, foreground=color, font=("Segoe UI", 9, "bold"))
            lbl_b.pack(side=tk.LEFT)
            lbl_val = ttk.Label(box, text=f"{var.get():.2f}", foreground="#f8fafc", font=("Segoe UI", 9, "bold"))
            lbl_val.pack(side=tk.RIGHT)

            def update_lbl(val):
                lbl_val.config(text=f"{float(val):.2f}")

            scale = ttk.Scale(parent, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=var, command=update_lbl)
            scale.pack(fill=tk.X, pady=(0, 6))

        add_weight_slider("w1: Populasi Warga / Pasien (0.0 - 1.0)", self.w1_var, "#38bdf8")
        add_weight_slider("w2: Mutu Akses Jalan Ambulans (0.0 - 1.0)", self.w2_var, "#eab308")
        add_weight_slider("w3: Sinergi Balai Desa & Fasilitas (0.0 - 1.0)", self.w3_var, "#a855f7")
        add_weight_slider("w4: Jarak Optimal Faskes Eksisting (0.0 - 1.0)", self.w4_var, "#ef4444")

        btn_apply = ttk.Button(parent, text="🔄 Terapkan Bobot & Hitung Ulang", command=self._on_param_change, style="Action.TButton")
        btn_apply.pack(fill=tk.X, pady=(12, 6))

    def _build_tab_inspeksi(self, parent):
        ttk.Label(
            parent,
            text="Klik titik manapun pada kanvas peta untuk membedah kelayakan lokasi Puskesmas:",
            foreground="#94a3b8",
            wraplength=340,
        ).pack(anchor="w", pady=(0, 6))

        self.lbl_insp_coords = ttk.Label(parent, text="Koordinat: -", font=("Segoe UI", 9, "bold"), foreground="#38bdf8")
        self.lbl_insp_coords.pack(anchor="w", pady=2)

        self.lbl_insp_valid = ttk.Label(parent, text="Status Zonasi: -", font=("Segoe UI", 9, "bold"))
        self.lbl_insp_valid.pack(anchor="w", pady=2)

        self.lbl_insp_road = ttk.Label(parent, text="Jalan Terdekat: -")
        self.lbl_insp_road.pack(anchor="w", pady=2)

        self.lbl_insp_fit = ttk.Label(parent, text="Estimasi Fitness: -", font=("Segoe UI", 10, "bold"), foreground="#10b981")
        self.lbl_insp_fit.pack(anchor="w", pady=(6, 8))

        # Progress bars fitur
        self.pb_pop, self.lbl_pb_pop = self._create_feature_bar(parent, "Kepadatan Populasi Pasien (s_pop)", "#38bdf8")
        self.pb_road, self.lbl_pb_road = self._create_feature_bar(parent, "Kelaikan Jalan Ambulans (s_road)", "#eab308")
        self.pb_fac, self.lbl_pb_fac = self._create_feature_bar(parent, "Sinergi Balai Desa & Posyandu (s_fac)", "#a855f7")
        self.pb_faskes, self.lbl_pb_faskes = self._create_feature_bar(parent, "Distribusi Faskes Eksisting (s_faskes)", "#ef4444")

    def _create_feature_bar(self, parent, text, color):
        box = ttk.Frame(parent)
        box.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(box, text=text, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        lbl_v = ttk.Label(box, text="0.00", font=("Segoe UI", 8, "bold"), foreground=color)
        lbl_v.pack(side=tk.RIGHT)
        bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate", maximum=1.0)
        bar.pack(fill=tk.X, pady=(0, 4))
        return bar, lbl_v

    def _build_tab_edukasi(self, parent):
        txt = tk.Text(parent, bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 8), wrap="word", relief="flat")
        txt.pack(fill=tk.BOTH, expand=True)

        content = """--- PERBANDINGAN TIGA ALGORITMA ---

1. GENETIC ALGORITHM (GA):
- Bio-Inspired: Seleksi alam Darwin & genetika evolusioner.
- Representasi: Kromosom koordinat riil [X, Y].
- Mekanisme: Tournament Selection (k=3), BLX-alpha crossover, adaptif Gaussian mutation, elitisme.
- Keunggulan: Eksplorasi global luas, tangguh keluar dari jebakan lokal optimum.

2. PARTICLE SWARM OPTIMIZATION (PSO):
- Bio-Inspired: Gerakan kawanan burung/ikan mencari sumber pakan.
- Representasi: Partikel dengan posisi X dan vektor kecepatan V.
- Mekanisme: Komponen inersia peluruhan w(t), kognitif personal best (pbest), dan sosial global best (gbest).
- Keunggulan: Kecepatan konvergensi sangat tinggi, presisi lokal tinggi pada ruang kontinu.

3. ANT COLONY OPTIMIZATION (ACO / ACOR):
- Bio-Inspired: Perilaku koloni semut meletakkan feromon jejak.
- Continuous Domain: Algoritma ACOR (Socha & Dorigo 2008).
- Mekanisme: Solution Archive terurut k solusi. Probabilitas feromon Gaussian kernel PDF. Dispersi feromon xi dan seleksi lokal q.
- Keunggulan: Keseimbangan eksplorasi multi-pusat dan eksploitasi terpandu jejak feromon terbaik.

--- TATA RUANG PUSKESMAS ---
- Akses Ambulans: Wajib dekat jalan aspal (d <= 50m).
- Bebas Bahaya: Dilarang di bantaran banjir sungai & tambang B3.
- Jarak Optimal Faskes: Dihindari berdempetan dengan Pustu lama (<200m).
"""
        txt.insert("1.0", content)
        txt.config(state="disabled")

    def _build_visualization_panel(self):
        self.fig = plt.Figure(figsize=(11.0, 7.5), facecolor="#0f172a")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self.toolbar_frame = ttk.Frame(self.right_panel)
        self.toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()

        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        for btn in [self.btn_v_split, self.btn_v_ga, self.btn_v_pso, self.btn_v_aco, self.btn_v_conv]:
            btn.config(style="View.TButton")

        if mode == "split_3":
            self.btn_v_split.config(style="ActiveView.TButton")
        elif mode == "ga":
            self.btn_v_ga.config(style="ActiveView.TButton")
        elif mode == "pso":
            self.btn_v_pso.config(style="ActiveView.TButton")
        elif mode == "aco":
            self.btn_v_aco.config(style="ActiveView.TButton")
        elif mode == "conv":
            self.btn_v_conv.config(style="ActiveView.TButton")

        self._init_canvas_plots()
        self._render_frame(self.current_frame)

    def _on_param_change(self):
        self._recompute_optimization(reset_playback=True)

    def _recompute_optimization(self, reset_playback: bool = True):
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.btn_play.config(text="▶ Mulai", style="Play.TButton")
        self.status_badge.config(text="STATUS: MENGHITUNG OPTIMASI...", bg="#1e293b", fg="#facc15")
        self.root.update_idletasks()

        cfg_copy = json.loads(json.dumps(self.config))
        cfg_copy["fitness_weights"] = {
            "w1_populasi": self.w1_var.get(),
            "w2_akses_jalan": self.w2_var.get(),
            "w3_fasilitas": self.w3_var.get(),
            "w4_faskes_kompetitor": self.w4_var.get(),
        }
        num_stores = self.facilities_var.get()
        cfg_copy["facility"]["num_facilities"] = num_stores

        self.evaluator = FitnessEvaluator(
            self.map_model,
            config=cfg_copy,
            mode=self.mode_var.get(),
            num_stores=num_stores,
        )

        self.heatmap_grid, self.heatmap_extent = self.evaluator.compute_grid_heatmap(
            resolution_x=65, resolution_y=50
        )

        budget = self.budget_var.get()
        pop_size = cfg_copy.get("optimization", {}).get("population_size", 40)

        # 1. Jalankan GA
        ga_cfg = cfg_copy.get("ga", {})
        self.ga = GeneticAlgorithm(
            self.evaluator,
            num_stores=num_stores,
            pop_size=pop_size,
            crossover_rate=ga_cfg.get("crossover_rate", 0.85),
            mutation_rate=ga_cfg.get("mutation_rate", 0.15),
            tournament_size=ga_cfg.get("tournament_size", 3),
            blx_alpha=ga_cfg.get("blx_alpha", 0.5),
            mutation_sigma=ga_cfg.get("gaussian_mutation_sigma", 40.0),
            elitism_count=ga_cfg.get("elitism_count", 2),
            seed=42,
        )
        self.ga_best_sol, self.ga_best_fit, self.ga_history = self.ga.optimize(max_evaluations=budget)

        # 2. Jalankan PSO
        pso_cfg = cfg_copy.get("pso", {})
        self.pso = ParticleSwarmOptimization(
            self.evaluator,
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
            seed=42,
        )
        self.pso_best_sol, self.pso_best_fit, self.pso_history = self.pso.optimize(max_evaluations=budget)

        # 3. Jalankan ACO
        aco_cfg = cfg_copy.get("aco", {})
        self.aco = AntColonyOptimization(
            self.evaluator,
            num_stores=num_stores,
            archive_size=aco_cfg.get("archive_size", 40),
            num_ants=aco_cfg.get("num_ants", 20),
            q_locality=aco_cfg.get("q_locality", 0.35),
            xi_evaporation=aco_cfg.get("xi_evaporation", 0.70),
            boundary_handling=aco_cfg.get("boundary_handling", "reflect"),
            seed=42,
        )
        self.aco_best_sol, self.aco_best_fit, self.aco_history = self.aco.optimize(max_evaluations=budget)

        self.total_frames = max(len(self.ga_history), len(self.pso_history), len(self.aco_history))
        self.scale_frame.config(to=max(1, self.total_frames - 1))

        if reset_playback:
            self.current_frame = 0

        self._init_canvas_plots()
        self._render_frame(self.current_frame)
        self.status_badge.config(text="STATUS: SIAP", bg="#1e293b", fg="#38bdf8")

    def _init_canvas_plots(self):
        self.fig.clf()

        if self.view_mode == "split_3":
            gs = gridspec.GridSpec(
                2, 3, height_ratios=[3.2, 1.8], hspace=0.40, wspace=0.14,
                left=0.05, right=0.98, top=0.94, bottom=0.08
            )
            self.ax_ga = self.fig.add_subplot(gs[0, 0])
            self.ax_pso = self.fig.add_subplot(gs[0, 1])
            self.ax_aco = self.fig.add_subplot(gs[0, 2])
            self.ax_conv = self.fig.add_subplot(gs[1, :])

            self._draw_map_view(self.ax_ga, "GA: Algoritma Genetika", is_full=False)
            self._draw_map_view(self.ax_pso, "PSO: Particle Swarm", is_full=False)
            self._draw_map_view(self.ax_aco, "ACO: Ant Colony", is_full=False)
            self._draw_conv(self.ax_conv, is_full=False)

        elif self.view_mode == "ga":
            self.fig.subplots_adjust(left=0.06, right=0.97, top=0.94, bottom=0.10)
            self.ax_ga = self.fig.add_subplot(1, 1, 1)
            self.ax_pso = self.ax_aco = self.ax_conv = None
            self._draw_map_view(self.ax_ga, "Algoritma Genetika (GA) — Layar Penuh", is_full=True)

        elif self.view_mode == "pso":
            self.fig.subplots_adjust(left=0.06, right=0.97, top=0.94, bottom=0.10)
            self.ax_pso = self.fig.add_subplot(1, 1, 1)
            self.ax_ga = self.ax_aco = self.ax_conv = None
            self._draw_map_view(self.ax_pso, "Particle Swarm Optimization (PSO) — Layar Penuh", is_full=True)

        elif self.view_mode == "aco":
            self.fig.subplots_adjust(left=0.06, right=0.97, top=0.94, bottom=0.10)
            self.ax_aco = self.fig.add_subplot(1, 1, 1)
            self.ax_ga = self.ax_pso = self.ax_conv = None
            self._draw_map_view(self.ax_aco, "Ant Colony Optimization (ACO) — Layar Penuh", is_full=True)

        elif self.view_mode == "conv":
            self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.12)
            self.ax_conv = self.fig.add_subplot(1, 1, 1)
            self.ax_ga = self.ax_pso = self.ax_aco = None
            self._draw_conv(self.ax_conv, is_full=True)

        self.canvas.draw_idle()

    def _draw_map_view(self, ax, title_prefix: str, is_full: bool = False):
        ax.clear()
        is_max = (self.mode_var.get() == "max")
        mode_desc = "Lokasi Terbaik" if is_max else "Lokasi Terburuk Sah"
        full_title = f"{title_prefix} ({mode_desc})"
        plot_map(
            self.map_model,
            ax=ax,
            title=full_title,
            show_legend=is_full,
            show_heatmap=True,
            heatmap_grid=self.heatmap_grid,
            heatmap_extent=self.heatmap_extent,
            heatmap_cmap="RdYlGn" if is_max else "RdYlGn_r",
            heatmap_alpha=0.45,
            show_banner=False,
        )

    def _draw_conv(self, ax, is_full: bool = False):
        ax.clear()
        ax.set_facecolor("#1e293b")
        title_txt = "Kurva Konvergensi Live Matched Budget: GA (Biru) vs PSO (Merah) vs ACO (Hijau)"
        ax.set_title(title_txt, fontsize=10.5 if is_full else 9.0, weight="bold", color="#38bdf8")
        ax.set_xlabel("Evaluasi Fungsi Fitness", fontsize=9.0, color="#94a3b8")
        ax.set_ylabel("Fitness Terbaik Berjalan", fontsize=9.0, color="#94a3b8")
        ax.set_xlim(0, self.budget_var.get())
        ax.grid(True, linestyle="--", alpha=0.3, color="#64748b")
        ax.tick_params(colors="#94a3b8", labelsize=8)

    def _render_frame(self, frame_idx: int):
        self.lbl_frame_info.config(text=f"{frame_idx + 1} / {self.total_frames}")
        self.scale_frame.set(frame_idx)

        ga_rec = self.ga_history[min(frame_idx, len(self.ga_history) - 1)] if self.ga_history else None
        pso_rec = self.pso_history[min(frame_idx, len(self.pso_history) - 1)] if self.pso_history else None
        aco_rec = self.aco_history[min(frame_idx, len(self.aco_history) - 1)] if self.aco_history else None

        # Render dinamis pada masing-masing axis
        if self.ax_ga is not None and ga_rec is not None:
            self._update_ga_plot(self.ax_ga, ga_rec)

        if self.ax_pso is not None and pso_rec is not None:
            self._update_pso_plot(self.ax_pso, pso_rec)

        if self.ax_aco is not None and aco_rec is not None:
            self._update_aco_plot(self.ax_aco, aco_rec)

        if self.ax_conv is not None:
            self._update_conv_plot(self.ax_conv, frame_idx)

        # Update Scoreboard
        if ga_rec:
            self.score_tree.item("GA", values=("GA", f"{ga_rec.best_fitness:.5f}", f"({ga_rec.best_position[0]:.1f}, {ga_rec.best_position[1]:.1f})", ga_rec.evaluations))
        if pso_rec:
            self.score_tree.item("PSO", values=("PSO", f"{pso_rec.gbest_fitness:.5f}", f"({pso_rec.gbest_position[0]:.1f}, {pso_rec.gbest_position[1]:.1f})", pso_rec.evaluations))
        if aco_rec:
            self.score_tree.item("ACO", values=("ACO", f"{aco_rec.best_fitness:.5f}", f"({aco_rec.best_position[0]:.1f}, {aco_rec.best_position[1]:.1f})", aco_rec.evaluations))

        self.canvas.draw_idle()

    def _update_ga_plot(self, ax, rec: GAGenerationRecord):
        # Bersihkan elemen dinamis sebelumnya
        for c in list(ax.collections[len(self.map_model.houses) + 5:]):
            c.remove()

        pop = rec.population
        ax.scatter(pop[:, 0], pop[:, 1], c="#2563eb", s=32, alpha=0.7, edgecolors="#ffffff", linewidths=0.6, zorder=8)

        elites = pop[rec.elite_indices]
        ax.scatter(elites[:, 0], elites[:, 1], c="#fbbf24", s=55, marker="D", edgecolors="#b45309", linewidths=1.0, zorder=9)

        bx, by = rec.best_position[0], rec.best_position[1]
        ax.scatter(bx, by, c="#10b981", s=130, marker="*", edgecolors="#ffffff", linewidths=1.5, zorder=10)

    def _update_pso_plot(self, ax, rec: PSOIterationRecord):
        for c in list(ax.collections[len(self.map_model.houses) + 5:]):
            c.remove()

        pos = rec.positions
        ax.scatter(pos[:, 0], pos[:, 1], c="#dc2626", s=32, alpha=0.7, edgecolors="#ffffff", linewidths=0.6, zorder=8)

        pb = rec.pbest_positions
        ax.scatter(pb[:, 0], pb[:, 1], c="#fb923c", s=40, marker="s", alpha=0.5, edgecolors="none", zorder=8.5)

        gx, gy = rec.gbest_position[0], rec.gbest_position[1]
        ax.scatter(gx, gy, c="#10b981", s=130, marker="*", edgecolors="#ffffff", linewidths=1.5, zorder=10)

    def _update_aco_plot(self, ax, rec: ACOIterationRecord):
        for c in list(ax.collections[len(self.map_model.houses) + 5:]):
            c.remove()

        ants = rec.ant_positions
        ax.scatter(ants[:, 0], ants[:, 1], c="#059669", s=34, alpha=0.75, edgecolors="#ffffff", linewidths=0.6, zorder=8)

        arch = rec.archive_positions
        ax.scatter(arch[:, 0], arch[:, 1], c="#10b981", s=45, marker="^", alpha=0.6, edgecolors="#047857", linewidths=0.8, zorder=8.5)

        bx, by = rec.best_position[0], rec.best_position[1]
        ax.scatter(bx, by, c="#10b981", s=130, marker="*", edgecolors="#ffffff", linewidths=1.5, zorder=10)

    def _update_conv_plot(self, ax, frame_idx: int):
        ax.lines.clear()

        ga_sub = self.ga_history[: min(frame_idx + 1, len(self.ga_history))]
        if ga_sub:
            evs = [r.evaluations for r in ga_sub]
            fits = [r.best_fitness for r in ga_sub]
            ax.plot(evs, fits, color="#38bdf8", linewidth=2.0, label="GA (Evolusioner)")

        pso_sub = self.pso_history[: min(frame_idx + 1, len(self.pso_history))]
        if pso_sub:
            evs = [r.evaluations for r in pso_sub]
            fits = [r.gbest_fitness for r in pso_sub]
            ax.plot(evs, fits, color="#ef4444", linewidth=2.0, linestyle="--", label="PSO (Swarm)")

        aco_sub = self.aco_history[: min(frame_idx + 1, len(self.aco_history))]
        if aco_sub:
            evs = [r.evaluations for r in aco_sub]
            fits = [r.best_fitness for r in aco_sub]
            ax.plot(evs, fits, color="#10b981", linewidth=2.0, linestyle="-.", label="ACO (Koloni Semut)")

        ax.legend(loc="lower right" if self.mode_var.get() == "max" else "upper right", fontsize=8.0, frameon=True, facecolor="#0f172a", edgecolor="#334155")

    def _toggle_play(self):
        if self.is_running:
            self.is_running = False
            self.btn_play.config(text="▶ Mulai", style="Play.TButton")
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
        else:
            self.is_running = True
            self.btn_play.config(text="⏸️ Jeda", style="Pause.TButton")
            self._playback_loop()

    def _playback_loop(self):
        if not self.is_running:
            return
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self._render_frame(self.current_frame)
            self.timer_id = self.root.after(self.speed_var.get(), self._playback_loop)
        else:
            self.is_running = False
            self.btn_play.config(text="▶ Mulai", style="Play.TButton")
            self.status_badge.config(text="STATUS: SIMULASI SELESAI", bg="#1e293b", fg="#10b981")

    def _step_frame(self):
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self._render_frame(self.current_frame)

    def _reset_playback(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.btn_play.config(text="▶ Mulai", style="Play.TButton")
        self.current_frame = 0
        self._render_frame(0)

    def _run_to_end(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.btn_play.config(text="▶ Mulai", style="Play.TButton")
        self.current_frame = max(0, self.total_frames - 1)
        self._render_frame(self.current_frame)
        self.status_badge.config(text="STATUS: SELESAI", bg="#1e293b", fg="#10b981")

    def _on_slider_frame_changed(self, val):
        f = int(float(val))
        if f != self.current_frame and f < self.total_frames:
            self.current_frame = f
            self._render_frame(self.current_frame)

    def _on_speed_changed(self, val):
        self.lbl_speed_val.config(text=f"{int(float(val))} ms")

    def _on_canvas_click(self, event):
        if event.xdata is None or event.ydata is None:
            return
        x, y = float(event.xdata), float(event.ydata)
        self.last_inspected_pt = (x, y)

        res = self.evaluator.evaluate_features_single_point(np.array([x, y]))

        self.lbl_insp_coords.config(text=f"Koordinat: ({x:.1f} m, {y:.1f} m)")
        if not res["is_valid"]:
            if res["is_forbidden"]:
                status_txt = f"❌ Terlarang ({res['forbidden_zone_name']})"
            elif res["is_oob"]:
                status_txt = "❌ Di Luar Batas Wilayah"
            else:
                status_txt = f"⚠️ Di Luar Koridor Jalan ({res['off_road_dist']:.1f} m dari koridor)"
            self.lbl_insp_valid.config(text=f"Status: {status_txt}", foreground="#ef4444")
        else:
            self.lbl_insp_valid.config(text="✅ Legal (Di Koridor Jalan & Bebas Bahaya)", foreground="#10b981")

        self.lbl_insp_road.config(
            text=f"Jalan: {res['nearest_road_name']} ({res['nearest_road_class']}) - Jarak: {res['d_road_geo']:.1f}m"
        )
        self.lbl_insp_fit.config(text=f"Estimasi Nilai Fitness: {res['raw_score']:.4f}")

        # Update bars
        self.pb_pop["value"] = res["populasi"]
        self.lbl_pb_pop.config(text=f"{res['populasi']:.2f}")

        self.pb_road["value"] = res["akses_jalan"]
        self.lbl_pb_road.config(text=f"{res['akses_jalan']:.2f}")

        self.pb_fac["value"] = res["fasilitas"]
        self.lbl_pb_fac.config(text=f"{res['fasilitas']:.2f}")

        self.pb_faskes["value"] = res["faskes_kompetitor"]
        self.lbl_pb_faskes.config(text=f"{res['faskes_kompetitor']:.2f}")


def main():
    root = tk.Tk()
    app = PuskesmasOptimizationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
