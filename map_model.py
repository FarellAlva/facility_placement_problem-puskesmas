"""
Modul Model Peta Wilayah Puskesmas (map_model.py)
Menyimpan struktur data spasial wilayah 2.0 km x 1.5 km (2000 m x 1500 m = 300 Ha),
parsing format JSON, menghitung geometri vektorisasi NumPy (Ray-Casting, jarak ortogonal ke jalan),
serta menyediakan fungsi render kartografis tematik fasilitas kesehatan (plot_map).
"""

from typing import Dict, List, Tuple, Any, Optional
import json
import math
import numpy as np


class MapModel:
    """
    Kelas representasi peta wilayah untuk optimasi penempatan fasilitas kesehatan (Puskesmas).
    Koordinat dalam satuan meter (default: 2000m x 1500m).
    """

    def __init__(self, data: Dict[str, Any]):
        self.name: str = data.get("name", "Peta Wilayah Puskesmas")
        dims = data.get("dimensions", {"width": 2000.0, "height": 1500.0})
        self.width: float = float(dims.get("width", 2000.0))
        self.height: float = float(dims.get("height", 1500.0))

        # 1. Rumah / Pemukiman: array [x, y, weight] (populasi pasien, balita, lansia)
        houses_raw = data.get("houses", [])
        if houses_raw:
            self.houses = np.array(
                [[h["x"], h["y"], h.get("weight", 1.0)] for h in houses_raw],
                dtype=np.float64,
            )
        else:
            self.houses = np.empty((0, 3), dtype=np.float64)

        # 2. Fasilitas Umum: list dict & dictionary array per jenis
        self.facilities_raw: List[Dict[str, Any]] = data.get("facilities", [])
        self.facilities_by_type: Dict[str, np.ndarray] = {}
        for fac in self.facilities_raw:
            ftype = fac["type"]
            coord_w = [fac["x"], fac["y"], fac.get("weight", 1.0)]
            if ftype not in self.facilities_by_type:
                self.facilities_by_type[ftype] = []
            self.facilities_by_type[ftype].append(coord_w)
        for ftype in self.facilities_by_type:
            self.facilities_by_type[ftype] = np.array(
                self.facilities_by_type[ftype], dtype=np.float64
            )

        # 3. Faskes Eksisting (Pustu / Klinik Lama): array [x, y]
        comp_raw = data.get("competitors", [])
        if comp_raw:
            self.competitors = np.array(
                [[c["x"], c["y"]] for c in comp_raw], dtype=np.float64
            )
            self.competitor_names = [c.get("name", f"Faskes {i+1}") for i, c in enumerate(comp_raw)]
        else:
            self.competitors = np.empty((0, 2), dtype=np.float64)
            self.competitor_names = []

        # 4. Jalan: prekomputasi menjadi daftar segmen garis [A, B]
        self.roads_raw: List[Dict[str, Any]] = data.get("roads", [])
        self._build_road_segments()

        # 5. Zona Terlarang: daftar poligon numpy array
        self.forbidden_zones: List[Dict[str, Any]] = []
        for zone in data.get("forbidden_zones", []):
            poly_pts = np.array(zone.get("polygon", []), dtype=np.float64)
            self.forbidden_zones.append({
                "name": zone.get("name", "Zona Terlarang"),
                "type": zone.get("type", "zona"),
                "polygon": poly_pts,
            })

    def _build_road_segments(self) -> None:
        """
        Mengonversi polyline jalan menjadi pasangan segmen garis vektor [seg_start, seg_end]
        lengkap dengan kelas jalan dan nilai lalu lintas untuk kalkulasi jarak cepat.
        """
        seg_starts = []
        seg_ends = []
        seg_classes = []
        seg_traffics = []
        seg_names = []

        for road in self.roads_raw:
            pts = np.array(road.get("points", []), dtype=np.float64)
            r_class = road.get("class", "lokal")
            traffic = float(road.get("traffic", 0.5))
            r_name = str(road.get("name", "Jalan"))

            if len(pts) >= 2:
                for i in range(len(pts) - 1):
                    seg_starts.append(pts[i])
                    seg_ends.append(pts[i + 1])
                    seg_classes.append(r_class)
                    seg_traffics.append(traffic)
                    seg_names.append(r_name)

        if seg_starts:
            self.road_seg_starts = np.array(seg_starts, dtype=np.float64)
            self.road_seg_ends = np.array(seg_ends, dtype=np.float64)
            self.road_seg_classes = seg_classes
            self.road_seg_traffics = np.array(seg_traffics, dtype=np.float64)
            self.road_seg_names = seg_names
        else:
            self.road_seg_starts = np.empty((0, 2), dtype=np.float64)
            self.road_seg_ends = np.empty((0, 2), dtype=np.float64)
            self.road_seg_classes = []
            self.road_seg_traffics = np.empty((0,), dtype=np.float64)
            self.road_seg_names = []

    @classmethod
    def load_from_json(cls, file_path: str) -> "MapModel":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def is_out_of_bounds(self, points: np.ndarray) -> np.ndarray:
        """
        Mengecek apakah titik berada di luar batas peta [0, width] x [0, height].
        """
        pts = np.atleast_2d(points)
        x = pts[:, 0]
        y = pts[:, 1]
        out_mask = (x < 0.0) | (x > self.width) | (y < 0.0) | (y > self.height)
        if points.ndim == 1:
            return out_mask[0]
        return out_mask

    def is_in_forbidden_zone(self, points: np.ndarray) -> np.ndarray:
        """
        Mengecek apakah titik berada di salah satu zona terlarang (sungai, sawah, hutan, tambang).
        """
        pts = np.atleast_2d(points)
        in_any = np.zeros(len(pts), dtype=bool)

        for zone in self.forbidden_zones:
            poly = zone["polygon"]
            if len(poly) >= 3:
                inside_poly = point_in_polygon_vectorized(pts, poly)
                in_any = in_any | inside_poly

        if points.ndim == 1:
            return in_any[0]
        return in_any

    def geometric_distance_to_roads(self, points: np.ndarray) -> np.ndarray:
        """
        Menghitung jarak geometris murni (meter Euclidean) dari titik ke garis sumbu jalan terdekat.
        """
        pts = np.atleast_2d(points)
        if len(self.road_seg_starts) == 0:
            res = np.full(len(pts), 10000.0, dtype=np.float64)
            return res[0] if points.ndim == 1 else res

        P = pts[:, np.newaxis, :]  # (N, 1, 2)
        A = self.road_seg_starts[np.newaxis, :, :]  # (1, S, 2)
        B = self.road_seg_ends[np.newaxis, :, :]    # (1, S, 2)

        AB = B - A
        AP = P - A
        AB_lensq = np.maximum(np.sum(AB ** 2, axis=2), 1e-12)
        t = np.clip(np.sum(AP * AB, axis=2) / AB_lensq, 0.0, 1.0)
        closest_pts = A + t[:, :, np.newaxis] * AB
        dists = np.sqrt(np.sum((P - closest_pts) ** 2, axis=2))
        min_dists = np.min(dists, axis=1)

        if points.ndim == 1:
            return float(min_dists[0])
        return min_dists

    def get_nearest_road_info(self, point: np.ndarray) -> Tuple[float, str, str]:
        """
        Mengembalikan (jarak_geometris, kelas_jalan, nama_jalan) untuk titik (x, y) terhadap segmen terdekat.
        """
        pt = np.asarray(point, dtype=np.float64).flatten()[:2]
        if len(self.road_seg_starts) == 0:
            return 10000.0, "lokal", "Tidak Ada Jalan"

        P = pt[np.newaxis, :]  # (1, 2)
        A = self.road_seg_starts  # (S, 2)
        B = self.road_seg_ends    # (S, 2)

        AB = B - A
        AP = P - A
        AB_lensq = np.maximum(np.sum(AB ** 2, axis=1), 1e-12)
        t = np.clip(np.sum(AP * AB, axis=1) / AB_lensq, 0.0, 1.0)
        closest_pts = A + t[:, np.newaxis] * AB
        dists = np.sqrt(np.sum((P - closest_pts) ** 2, axis=1))

        best_idx = int(np.argmin(dists))
        best_dist = float(dists[best_idx])
        best_class = self.road_seg_classes[best_idx] if best_idx < len(self.road_seg_classes) else "lokal"
        best_name = self.road_seg_names[best_idx] if best_idx < len(self.road_seg_names) else "Jalan"

        return best_dist, best_class, best_name

    def get_forbidden_zone_name(self, point: np.ndarray) -> Optional[str]:
        """
        Mengembalikan nama zona terlarang jika titik berada di dalamnya, atau None jika valid.
        """
        pt_2d = np.asarray(point, dtype=np.float64).reshape((1, 2))
        for zone in self.forbidden_zones:
            poly = np.array(zone.get("polygon", []), dtype=np.float64)
            if len(poly) >= 3:
                if point_in_polygon_vectorized(pt_2d, poly)[0]:
                    return zone.get("name", zone.get("type", "Zona Terlarang"))
        return None


def point_in_polygon_vectorized(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """
    Algoritma Ray Casting tervektorisasi untuk mengecek apakah titik-titik berada di dalam poligon.
    points: array shape (N, 2)
    polygon: array shape (V, 2)
    Output: boolean array shape (N,)
    """
    x = points[:, 0]
    y = points[:, 1]
    n_pts = len(points)
    n_vert = len(polygon)
    inside = np.zeros(n_pts, dtype=bool)

    p1 = polygon[0]
    for i in range(1, n_vert + 1):
        p2 = polygon[i % n_vert]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        cond_y = (y1 > y) != (y2 > y)

        if np.any(cond_y):
            dx = x2 - x1
            dy = y2 - y1
            denom = dy if dy != 0 else 1e-12
            x_intersect = x1 + (y - y1) * dx / denom
            cond_x = x < x_intersect
            intersect = cond_y & cond_x
            inside = inside ^ intersect

        p1 = p2

    return inside


def plot_map(
    map_model: MapModel,
    ax=None,
    title: str = "Peta Wilayah Puskesmas",
    show_legend: bool = True,
    show_heatmap: bool = False,
    heatmap_grid: Optional[np.ndarray] = None,
    heatmap_extent: Optional[Tuple[float, float, float, float]] = None,
    heatmap_cmap: str = "viridis",
    heatmap_alpha: float = 0.50,
    show_banner: Optional[bool] = None,
):
    """
    Visualisasi kartografis realistis dan profesional untuk penentuan lokasi Puskesmas.
    Menyajikan lanskap pedesaan, fasilitas umum, jaringan jalan ambulans, dan zona terlarang.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import matplotlib.lines as lines

    if ax is None:
        fig, ax = plt.subplots(figsize=(14.0, 10.2), dpi=150)

    if show_banner is None:
        show_banner = show_legend

    is_study_map = True

    # 1. Latar Belakang Wilayah
    # Sisi Barat: Padang hijau pedesaan
    ax.add_patch(patches.Rectangle((0, 0), 1150, map_model.height, facecolor="#cfe8a9", edgecolor="none", zorder=0))
    ax.add_patch(patches.Polygon([[0, 800], [500, 1100], [700, 700], [0, 500]], closed=True, facecolor="#c7e39f", edgecolor="none", alpha=0.5, zorder=0))
    ax.add_patch(patches.Polygon([[400, 0], [900, 300], [1150, 200], [1150, 0]], closed=True, facecolor="#c4e199", edgecolor="none", alpha=0.4, zorder=0))

    # Sisi Timur: Wilayah bukit tambang & tanah merah
    ax.add_patch(patches.Rectangle((1150, 0), map_model.width - 1150, map_model.height, facecolor="#e6c8a2", edgecolor="none", zorder=0))
    ax.add_patch(patches.Polygon([[1150, 600], [1600, 800], [1800, 400], [1150, 300]], closed=True, facecolor="#deb68b", edgecolor="none", alpha=0.45, zorder=0))

    # Pepohonan Hiasan Hijau di Padang Desa
    tree_clumps = [
        (140, 1040), (230, 1020), (380, 1120), (510, 1160), (630, 1220), (680, 1050),
        (450, 410), (530, 440), (650, 310), (620, 160), (320, 560), (430, 580),
        (710, 1340), (730, 1200), (840, 1380), (870, 1180), (950, 1300), (940, 650)
    ]
    for tx, ty in tree_clumps:
        ax.add_patch(patches.Ellipse((tx + 2, ty - 3), 30, 18, facecolor="#b2d488", edgecolor="none", alpha=0.6, zorder=1))
        offsets = [(-8, -3, 13, "#2d5a27"), (8, -2, 14, "#387d3a"), (0, 6, 15, "#439247"), (-2, 2, 11, "#4cae50")]
        for ox, oy, r, col in offsets:
            ax.add_patch(patches.Circle((tx + ox, ty + oy), r, facecolor=col, edgecolor="#20461b", linewidth=0.5, zorder=1.1))

    # 2. Tampilkan Heatmap jika diminta
    if show_heatmap and heatmap_grid is not None and heatmap_extent is not None:
        ax.imshow(
            heatmap_grid,
            origin="lower",
            extent=heatmap_extent,
            cmap=heatmap_cmap,
            alpha=heatmap_alpha,
            aspect="auto",
            zorder=1.5,
        )

    # 3. Zona Terlarang
    # 3A. Hutan Lindung
    hutan_zone = next((z for z in map_model.forbidden_zones if z.get("type") == "hutan"), None)
    if hutan_zone is not None:
        poly_pts = hutan_zone["polygon"]
        ax.add_patch(patches.Polygon(poly_pts, closed=True, facecolor="#235327", edgecolor="#183f1d", linewidth=1.5, zorder=2))
        rng = np.random.RandomState(101)
        for gx in np.linspace(30, 720, 20):
            for gy in np.linspace(1110, 1480, 12):
                jx = gx + rng.uniform(-15, 15)
                jy = gy + rng.uniform(-15, 15)
                if jx < 740 and jy > 1080:
                    cr = rng.uniform(32, 48)
                    ccol = rng.choice(["#183f1d", "#235327", "#2e6a32", "#3b853e"])
                    ax.add_patch(patches.Circle((jx, jy), cr, facecolor=ccol, edgecolor="#143618", linewidth=0.6, alpha=0.92, zorder=2.1))

    # 3B. Sawah Irigasi LP2B
    sawah_zone = next((z for z in map_model.forbidden_zones if z.get("type") == "sawah"), None)
    if sawah_zone is not None:
        poly_pts = sawah_zone["polygon"]
        ax.add_patch(patches.Polygon(poly_pts, closed=True, facecolor="#8ebf4b", edgecolor="#5e842f", linewidth=1.5, zorder=2))
        x_cuts = [0, 90, 180, 270, 360, 450, 540, 640]
        y_cuts = [0, 90, 180, 270, 360, 450, 520]
        paddy_palette = ["#a3c959", "#8ebf4b", "#b8d96e", "#9bbe47", "#c8dd7b", "#7fa73d", "#92bd44"]
        p_idx = 0
        for i in range(len(x_cuts) - 1):
            for j in range(len(y_cuts) - 1):
                x0, x1 = x_cuts[i], x_cuts[i + 1]
                y0, y1 = y_cuts[j], y_cuts[j + 1]
                col = paddy_palette[(p_idx + i * 2 + j) % len(paddy_palette)]
                p_idx += 1
                ax.add_patch(patches.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=col, edgecolor="#5c822e", linewidth=1.0, zorder=2.1))

    # 3C. Sungai Sukamaju
    sungai_zone = next((z for z in map_model.forbidden_zones if z.get("type") == "sungai"), None)
    if sungai_zone is not None:
        poly_pts = sungai_zone["polygon"]
        ax.add_patch(patches.Polygon(poly_pts, closed=True, facecolor="#3ea4e8", edgecolor="#1a71b3", linewidth=2.0, zorder=2.5))
        river_mid_pts = [(795, 1500), (765, 1150), (795, 900), (825, 750), (810, 500), (765, 250), (710, 0)]
        rmp = np.array(river_mid_pts)
        ax.plot(rmp[:, 0], rmp[:, 1], color="#75c8f9", linewidth=2.0, alpha=0.7, zorder=2.6)

    # 3D. Area Tambang & Stockpile
    tambang_zone = next((z for z in map_model.forbidden_zones if z.get("type") == "tambang"), None)
    if tambang_zone is not None:
        poly_pts = tambang_zone["polygon"]
        ax.add_patch(patches.Polygon(poly_pts, closed=True, facecolor="#d9a67a", edgecolor="#aa7044", linewidth=1.5, zorder=2.1))
        # Open pit terraces
        pit_center = (1750, 420)
        pit_steps = [(250, 180, "#c59163", "#945930"), (190, 140, "#ab7243", "#7d421d"), (130, 95, "#8d5328", "#5e2e0e")]
        for w, h, fcol, ecol in pit_steps:
            ax.add_patch(patches.Ellipse(pit_center, w, h, angle=-10, facecolor=fcol, edgecolor=ecol, linewidth=1.2, zorder=2.2))

    # 4. Permukiman Warga (Kluster Dusun)
    ellipse = patches.Ellipse(
        (280, 765), width=490, height=430,
        facecolor="#dcf0fd", edgecolor="#258cdb",
        linestyle="--", linewidth=1.8, alpha=0.35, zorder=3,
    )
    ax.add_patch(ellipse)

    if len(map_model.houses) > 0:
        for h in map_model.houses:
            hx, hy = h[0], h[1]
            w, h_dim = 22, 15
            ax.add_patch(patches.Rectangle((hx - w/2 + 2, hy - h_dim/2 - 2), w, h_dim, facecolor="#b4d588", edgecolor="none", alpha=0.6, zorder=3.8))
            ax.add_patch(patches.Rectangle((hx - w/2, hy - h_dim/2), w, h_dim * 0.65, facecolor="#f8fafc", edgecolor="#94a3b8", linewidth=0.5, zorder=3.9))
            roof_palette = [("#e67e22", "#c0392b"), ("#d35400", "#a93226"), ("#e74c3c", "#922b21")]
            c_light, c_dark = roof_palette[int(hx + hy) % len(roof_palette)]
            poly_roof_l = [[hx - w/2 - 2, hy - 1], [hx, hy + h_dim/2], [hx, hy - 1]]
            ax.add_patch(patches.Polygon(poly_roof_l, closed=True, facecolor=c_light, edgecolor="#922b21", linewidth=0.5, zorder=4.0))
            poly_roof_r = [[hx + w/2 + 2, hy - 1], [hx, hy + h_dim/2], [hx, hy - 1]]
            ax.add_patch(patches.Polygon(poly_roof_r, closed=True, facecolor=c_dark, edgecolor="#922b21", linewidth=0.5, zorder=4.0))

    # 5. Jaringan Jalan & Jembatan
    # Jembatan Beton pada Sungai
    ax.add_patch(patches.Rectangle((750, 792), 100, 26, facecolor="#94a3b8", edgecolor="#334155", linewidth=1.5, zorder=4.2))
    ax.plot([750, 850], [805 + 13, 805 + 13], color="#1e293b", linewidth=2.5, zorder=4.3)
    ax.plot([750, 850], [805 - 13, 805 - 13], color="#1e293b", linewidth=2.5, zorder=4.3)

    for road in map_model.roads_raw:
        pts = np.array(road.get("points", []), dtype=np.float64)
        r_class = road.get("class", "lokal")

        if r_class == "arteri":
            # Jalan Arteri Lintas Provinsi (Akses Evakuasi RSUD)
            ax.plot(pts[:, 0], pts[:, 1], color="#181c20", linewidth=22.0, solid_capstyle="butt", zorder=4.6)
            ax.plot(pts[:, 0], pts[:, 1], color="#38404a", linewidth=17.5, solid_capstyle="butt", zorder=4.7)
            ax.plot(pts[:, 0], pts[:, 1], color="#ffffff", linewidth=1.5, linestyle=(0, (6, 7)), zorder=4.8)

        elif r_class == "kolektor":
            # Jalan Kolektor Utama (Akses Ambulans Desa)
            ax.plot(pts[:, 0], pts[:, 1], color="#64748b", linewidth=8.0, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#94a3b8", linewidth=6.0, solid_capstyle="round", zorder=4.5)

        elif r_class == "hauling":
            # Jalan Hauling / Tanah Rusak
            ax.plot(pts[:, 0], pts[:, 1], color="#dfaa85", linewidth=14.0, alpha=0.5, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#bf7952", linewidth=10.0, solid_capstyle="round", zorder=4.5)

        else:
            # Jalan Lokal Lingkungan Dusun
            ax.plot(pts[:, 0], pts[:, 1], color="#94a3b8", linewidth=5.0, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#cbd5e1", linewidth=3.6, solid_capstyle="round", zorder=4.5)

    # 6. Fasilitas Publik & Sinergi Kesehatan
    facility_markers = {
        "balai_desa": ("#1d4ed8", "BD", 155),     # Kantor Desa & BPJS
        "posyandu": ("#ec4899", "PY", 145),       # Posyandu Balita/Lansia
        "sekolah": ("#eab308", "S", 135),         # Sekolah (Mitra UKS & Imunisasi)
        "pasar": ("#8b5cf6", "P", 130),           # Pasar Tradisional
        "masjid_kantor": ("#059669", "M", 145),   # Masjid / Balai Warga
    }

    for fac in map_model.facilities_raw:
        ftype = fac.get("type", "fasilitas")
        color, letter, size = facility_markers.get(ftype, ("#0284c7", "*", 100))
        fx, fy = fac["x"], fac["y"]

        ax.scatter(fx + 2, fy - 2, c="#0f172a", marker="o", s=size, alpha=0.35, edgecolors="none", zorder=6.8)
        ax.scatter(fx, fy, c=color, marker="o", s=size, edgecolors="#ffffff", linewidths=2.0, zorder=7.0)
        ax.text(fx, fy, letter, color="#ffffff", fontsize=8.0, weight="bold", ha="center", va="center", zorder=7.2)

    # 7. Faskes Eksisting (Pustu / Puskesmas Pembantu Sukamukti)
    if len(map_model.competitors) > 0:
        for cx, cy in map_model.competitors:
            ax.scatter(cx + 2, cy - 2, c="#0f172a", marker="o", s=160, alpha=0.35, edgecolors="none", zorder=6.8)
            ax.scatter(cx, cy, c="#dc2626", marker="o", s=160, edgecolors="#ffffff", linewidths=2.2, zorder=7.0)
            # Palang Merah di dalam lingkaran faskes eksisting
            ax.plot([cx - 5, cx + 5], [cy, cy], color="#ffffff", linewidth=2.5, solid_capstyle="round", zorder=7.2)
            ax.plot([cx, cx], [cy - 5, cy + 5], color="#ffffff", linewidth=2.5, solid_capstyle="round", zorder=7.2)

    # 8. Pill Labels Spasial
    def pill_label(x, y, text, fcol, text_col="#ffffff", font_size=7.5, pad=0.35):
        ax.text(x + 2, y - 2, text, color="#0f172a", fontsize=font_size, weight="bold", ha="center", va="center",
                bbox=dict(boxstyle=f"round,pad={pad}", facecolor="#0f172a", edgecolor="none", alpha=0.3), zorder=6.0)
        ax.text(x, y, text, color=text_col, fontsize=font_size, weight="bold", ha="center", va="center",
                bbox=dict(boxstyle=f"round,pad={pad}", facecolor=fcol, edgecolor="#ffffff", linewidth=0.8, alpha=0.96), zorder=6.2)

    pill_label(120, 1370, "Hutan Lindung (Konservasi)", "#143818", pad=0.4, font_size=8.0)
    pill_label(120, 260, "Sawah Irigasi LP2B", "#244517", pad=0.4, font_size=8.0)
    pill_label(815, 480, "Sungai (Bantaran Banjir)", "#1565c0", pad=0.4, font_size=8.0)
    pill_label(155, 1025, "Permukiman Dusun Krajan", "#1565c0", pad=0.4, font_size=8.0)
    pill_label(860, 755, "Pustu Eksisting (FE)", "#b91c1c", pad=0.4, font_size=7.5)

    pill_label(210, 680, "Jl. Utama Desa (Kolektor)", "#1e293b", font_size=7.2)
    pill_label(1150, 1260, "Jl. Lintas Provinsi (Arteri RSUD)", "#1e293b", font_size=8.0)
    pill_label(1660, 1440, "Jalan Hauling Rusak", "#78350f", font_size=7.5)
    pill_label(1720, 620, "Area Tambang (Zona Polutif)", "#2c1b12", font_size=7.5)

    # 9. Header Banner
    ax.set_xlim(0, map_model.width)
    ax.set_ylim(0, map_model.height)
    ax.set_aspect("equal")

    if show_banner:
        header_text = "Peta Wilayah: Penentuan Lokasi Puskesmas Kecamatan Sukamaju Sejahtera"
        font_sz = 11.0 if show_legend else 9.0
        ax.text(
            25, map_model.height - 35,
            f" {header_text} ",
            color="#ffffff",
            fontsize=font_sz,
            weight="bold",
            ha="left",
            va="top",
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#065f46", edgecolor="#ffffff", linewidth=1.2, alpha=0.96),
            zorder=6.5,
        )

    for spine in ax.spines.values():
        spine.set_color("#64748b")
        spine.set_linewidth(1.2)

    ax.set_xticks([])
    ax.set_yticks([])

    # 10. Legenda Bawah
    if show_legend:
        legend_elements = [
            patches.Patch(facecolor="#e11d48", edgecolor="#9f1239", label="Rumah / Warga"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#1d4ed8", markersize=8.5, label="Balai Desa (BD)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#ec4899", markersize=8.5, label="Posyandu (PY)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#eab308", markersize=8.5, label="Sekolah / UKS (S)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#8b5cf6", markersize=8.5, label="Pasar Desa (P)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#dc2626", markersize=8.5, label="Faskes Eksisting (FE)"),
            lines.Line2D([0], [0], color="#64748b", lw=4.0, label="Jl. Kolektor (Ambulans)"),
            lines.Line2D([0], [0], color="#202428", lw=5.0, linestyle="--", label="Jl. Arteri (RSUD)"),
            lines.Line2D([0], [0], color="#94a3b8", lw=3.0, label="Jl. Lokal"),
            lines.Line2D([0], [0], color="#bf7952", lw=5.0, label="Jl. Hauling Rusak"),
            patches.Patch(facecolor="#235327", edgecolor="#143618", label="Hutan Lindung"),
            patches.Patch(facecolor="#8ebf4b", edgecolor="#5e842f", label="Sawah LP2B"),
            patches.Patch(facecolor="#3ea4e8", edgecolor="#1a71b3", label="Sungai Banjir"),
            patches.Patch(facecolor="#d9a67a", edgecolor="#aa7044", label="Tambang Polutif"),
        ]
        leg = ax.legend(
            handles=legend_elements,
            loc="upper center",
            bbox_to_anchor=(0.44, -0.02),
            ncol=5,
            fontsize=8.0,
            frameon=True,
            facecolor="#ffffff",
            edgecolor="#94a3b8",
            framealpha=0.98,
        )
        leg.get_frame().set_linewidth(1.2)

        # Kompas & Skala
        ax.annotate(
            "N", xy=(1920, -55), xytext=(1920, -115),
            arrowprops=dict(facecolor="#1e293b", edgecolor="#0f172a", width=2.5, headwidth=9),
            ha="center", va="center", fontsize=9, weight="bold", color="#1e293b",
            annotation_clip=False, zorder=20
        )
        ax.plot([1780, 1980], [-135, -135], color="#1e293b", linewidth=2.0, clip_on=False, zorder=20)
        ax.plot([1780, 1780], [-130, -140], color="#1e293b", linewidth=2.0, clip_on=False, zorder=20)
        ax.plot([1980, 1980], [-130, -140], color="#1e293b", linewidth=2.0, clip_on=False, zorder=20)
        ax.text(1880, -150, "1 km", ha="center", va="top", fontsize=8.5, weight="bold", color="#1e293b", clip_on=False, zorder=20)

    return ax
