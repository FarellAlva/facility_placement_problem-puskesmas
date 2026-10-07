"""
Modul Model Peta Wilayah Puskesmas (map_model.py)
Menyimpan struktur data spasial wilayah, parsing format JSON,
menghitung geometri vektorisasi NumPy (Ray-Casting, jarak ortogonal ke jalan),
serta menyediakan fungsi render kartografis tematik fasilitas kesehatan (plot_map)
yang adaptif terhadap berbagai skala ukuran wilayah (2.0 x 1.5 km hingga 5.0 x 4.0 km).
"""

from typing import Dict, List, Tuple, Any, Optional
import json
import math
import numpy as np


class MapModel:
    """
    Kelas representasi peta wilayah untuk optimasi penempatan fasilitas kesehatan (Puskesmas).
    Koordinat dalam satuan meter.
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
        pts = np.atleast_2d(points)
        x = pts[:, 0]
        y = pts[:, 1]
        out_mask = (x < 0.0) | (x > self.width) | (y < 0.0) | (y > self.height)
        if points.ndim == 1:
            return out_mask[0]
        return out_mask

    def is_in_forbidden_zone(self, points: np.ndarray) -> np.ndarray:
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
        pt = np.asarray(point, dtype=np.float64).flatten()[:2]
        if len(self.road_seg_starts) == 0:
            return 10000.0, "lokal", "Tidak Ada Jalan"

        P = pt[np.newaxis, :]
        A = self.road_seg_starts
        B = self.road_seg_ends

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
        pt_2d = np.asarray(point, dtype=np.float64).reshape((1, 2))
        for zone in self.forbidden_zones:
            poly = np.array(zone.get("polygon", []), dtype=np.float64)
            if len(poly) >= 3:
                if point_in_polygon_vectorized(pt_2d, poly)[0]:
                    return zone.get("name", zone.get("type", "Zona Terlarang"))
        return None


def point_in_polygon_vectorized(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
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
    Visualisasi kartografis realistis dan adaptif untuk penentuan lokasi Puskesmas.
    Mendukung peta skala 2.0x1.5 km hingga peta skala luas 5.0x4.0 km.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import matplotlib.lines as lines

    if ax is None:
        fig, ax = plt.subplots(figsize=(14.0, 10.2), dpi=150)

    if show_banner is None:
        show_banner = show_legend

    W = map_model.width
    H = map_model.height

    # 1. Latar Belakang Wilayah Hijau Subur
    ax.add_patch(patches.Rectangle((0, 0), W, H, facecolor="#d7ecc0", edgecolor="none", zorder=0))

    # Variasi padang rumput & perbukitan lembut
    ax.add_patch(patches.Polygon([[0, H * 0.5], [W * 0.4, H * 0.8], [W * 0.7, H * 0.4], [0, H * 0.2]], closed=True, facecolor="#cbe5b0", edgecolor="none", alpha=0.5, zorder=0.5))
    ax.add_patch(patches.Polygon([[W * 0.5, 0], [W, 0], [W, H * 0.5], [W * 0.6, H * 0.2]], closed=True, facecolor="#edd8ba", edgecolor="none", alpha=0.4, zorder=0.5))

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

    # 3. Zona Terlarang Poligon Nyata
    zone_styles = {
        "hutan": {"face": "#235327", "edge": "#183f1d", "label": "Hutan Lindung"},
        "sawah": {"face": "#8ebf4b", "edge": "#5e842f", "label": "Sawah LP2B"},
        "sungai": {"face": "#3ea4e8", "edge": "#1a71b3", "label": "Sungai / Banjir"},
        "tambang": {"face": "#d9a67a", "edge": "#aa7044", "label": "Kawasan Industri / B3"},
    }

    for zone in map_model.forbidden_zones:
        ztype = zone.get("type", "zona")
        poly = zone.get("polygon", [])
        st = zone_styles.get(ztype, {"face": "#cbd5e1", "edge": "#64748b", "label": zone.get("name", "Zona")})

        if len(poly) >= 3:
            ax.add_patch(patches.Polygon(poly, closed=True, facecolor=st["face"], edgecolor=st["edge"], linewidth=1.5, zorder=2.0))

    # 4. Permukiman Warga (Houses)
    if len(map_model.houses) > 0:
        h = map_model.houses
        if W <= 2500:
            # Peta skala desa: gambar rumah terakota
            for row in h:
                hx, hy = row[0], row[1]
                w, h_dim = 22, 15
                ax.add_patch(patches.Rectangle((hx - w/2 + 2, hy - h_dim/2 - 2), w, h_dim, facecolor="#b4d588", edgecolor="none", alpha=0.6, zorder=3.8))
                ax.add_patch(patches.Rectangle((hx - w/2, hy - h_dim/2), w, h_dim * 0.65, facecolor="#f8fafc", edgecolor="#94a3b8", linewidth=0.5, zorder=3.9))
                poly_roof_l = [[hx - w/2 - 2, hy - 1], [hx, hy + h_dim/2], [hx, hy - 1]]
                ax.add_patch(patches.Polygon(poly_roof_l, closed=True, facecolor="#e67e22", edgecolor="#922b21", linewidth=0.5, zorder=4.0))
                poly_roof_r = [[hx + w/2 + 2, hy - 1], [hx, hy + h_dim/2], [hx, hy - 1]]
                ax.add_patch(patches.Polygon(poly_roof_r, closed=True, facecolor="#c0392b", edgecolor="#922b21", linewidth=0.5, zorder=4.0))
        else:
            # Peta skala kecamatan luas: titik sebaran permukiman padat
            ax.scatter(h[:, 0], h[:, 1], c="#e11d48", s=30, alpha=0.85, edgecolors="#ffffff", linewidths=0.6, zorder=3.9)

    # 5. Jaringan Jalan & Jembatan
    road_widths = {
        "arteri": (18.0 if W <= 2500 else 12.0, 14.0 if W <= 2500 else 9.0),
        "kolektor": (7.5 if W <= 2500 else 6.0, 5.5 if W <= 2500 else 4.2),
        "lokal": (4.5 if W <= 2500 else 3.5, 3.2 if W <= 2500 else 2.2),
        "hauling": (10.0 if W <= 2500 else 7.0, 7.5 if W <= 2500 else 5.0),
    }

    for road in map_model.roads_raw:
        pts = np.array(road.get("points", []), dtype=np.float64)
        r_class = road.get("class", "lokal")
        outer_w, inner_w = road_widths.get(r_class, (4.5, 3.2))

        if r_class == "arteri":
            ax.plot(pts[:, 0], pts[:, 1], color="#181c20", linewidth=outer_w, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#38404a", linewidth=inner_w, solid_capstyle="round", zorder=4.5)
            ax.plot(pts[:, 0], pts[:, 1], color="#ffffff", linewidth=1.2, linestyle=(0, (6, 7)), zorder=4.6)
        elif r_class == "kolektor":
            ax.plot(pts[:, 0], pts[:, 1], color="#475569", linewidth=outer_w, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#818cf8" if W > 3000 else "#94a3b8", linewidth=inner_w, solid_capstyle="round", zorder=4.5)
        elif r_class == "hauling":
            ax.plot(pts[:, 0], pts[:, 1], color="#dfaa85", linewidth=outer_w, alpha=0.5, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#bf7952", linewidth=inner_w, solid_capstyle="round", zorder=4.5)
        else:
            ax.plot(pts[:, 0], pts[:, 1], color="#94a3b8", linewidth=outer_w, solid_capstyle="round", zorder=4.4)
            ax.plot(pts[:, 0], pts[:, 1], color="#cbd5e1", linewidth=inner_w, solid_capstyle="round", zorder=4.5)

    # 6. Fasilitas Publik
    facility_markers = {
        "balai_desa": ("#1d4ed8", "BD", 155),
        "posyandu": ("#ec4899", "PY", 145),
        "sekolah": ("#eab308", "S", 135),
        "pasar": ("#8b5cf6", "P", 130),
        "masjid_kantor": ("#059669", "M", 145),
    }

    scale_mult = 1.0 if W <= 2500 else 1.2
    for fac in map_model.facilities_raw:
        ftype = fac.get("type", "fasilitas")
        color, letter, size = facility_markers.get(ftype, ("#0284c7", "*", 100))
        fx, fy = fac["x"], fac["y"]
        s_sz = size * scale_mult

        ax.scatter(fx + 2, fy - 2, c="#0f172a", marker="o", s=s_sz, alpha=0.35, edgecolors="none", zorder=6.8)
        ax.scatter(fx, fy, c=color, marker="o", s=s_sz, edgecolors="#ffffff", linewidths=1.8, zorder=7.0)
        ax.text(fx, fy, letter, color="#ffffff", fontsize=8.0 if W <= 2500 else 8.5, weight="bold", ha="center", va="center", zorder=7.2)

    # 7. Faskes Eksisting (Pustu / Klinik)
    if len(map_model.competitors) > 0:
        for cx, cy in map_model.competitors:
            s_sz = 160 * scale_mult
            ax.scatter(cx + 2, cy - 2, c="#0f172a", marker="o", s=s_sz, alpha=0.35, edgecolors="none", zorder=6.8)
            ax.scatter(cx, cy, c="#dc2626", marker="o", s=s_sz, edgecolors="#ffffff", linewidths=2.2, zorder=7.0)
            cross_sz = 5.0 * (1.0 if W <= 2500 else 1.8)
            ax.plot([cx - cross_sz, cx + cross_sz], [cy, cy], color="#ffffff", linewidth=2.5, solid_capstyle="round", zorder=7.2)
            ax.plot([cx, cx], [cy - cross_sz, cy + cross_sz], color="#ffffff", linewidth=2.5, solid_capstyle="round", zorder=7.2)

    # 8. Header Banner & Batas Sumbu
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")

    if show_banner:
        font_sz = 10.5 if show_legend else 8.5
        ax.text(
            W * 0.015, H - (H * 0.035),
            f" {map_model.name} ",
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

    # 9. Legenda & Skala
    if show_legend:
        legend_elements = [
            patches.Patch(facecolor="#e11d48", edgecolor="#9f1239", label="Permukiman Warga"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#1d4ed8", markersize=8.5, label="Balai Desa (BD)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#ec4899", markersize=8.5, label="Posyandu (PY)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#eab308", markersize=8.5, label="Sekolah / UKS (S)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#8b5cf6", markersize=8.5, label="Pasar Desa (P)"),
            lines.Line2D([0], [0], marker="o", color="w", markerfacecolor="#dc2626", markersize=8.5, label="Faskes Eksisting (Pustu)"),
            lines.Line2D([0], [0], color="#202428", lw=4.5, linestyle="--", label="Jl. Arteri (RSUD)"),
            lines.Line2D([0], [0], color="#475569", lw=4.0, label="Jl. Kolektor (Ambulans)"),
            lines.Line2D([0], [0], color="#94a3b8", lw=2.8, label="Jl. Lokal Dusun"),
            lines.Line2D([0], [0], color="#bf7952", lw=4.0, label="Jl. Hauling Rusak"),
            patches.Patch(facecolor="#235327", edgecolor="#143618", label="Hutan Lindung"),
            patches.Patch(facecolor="#8ebf4b", edgecolor="#5e842f", label="Sawah LP2B"),
            patches.Patch(facecolor="#3ea4e8", edgecolor="#1a71b3", label="Sungai / Banjir"),
            patches.Patch(facecolor="#d9a67a", edgecolor="#aa7044", label="Zona Polutif B3"),
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
        scale_len = 2000.0 if W > 3000 else 1000.0
        scale_txt = "2 km" if W > 3000 else "1 km"
        x_start = W * 0.88
        y_pos = -H * 0.08

        ax.annotate(
            "N", xy=(W * 0.95, -H * 0.035), xytext=(W * 0.95, -H * 0.075),
            arrowprops=dict(facecolor="#1e293b", edgecolor="#0f172a", width=2.5, headwidth=8),
            ha="center", va="center", fontsize=8.5, weight="bold", color="#1e293b",
            annotation_clip=False, zorder=20
        )
        ax.plot([x_start - scale_len * 0.05, x_start + scale_len * 0.05], [y_pos, y_pos], color="#1e293b", linewidth=2.0, clip_on=False, zorder=20)
        ax.text(x_start, y_pos - H * 0.015, scale_txt, ha="center", va="top", fontsize=8.0, weight="bold", color="#1e293b", clip_on=False, zorder=20)

    return ax
