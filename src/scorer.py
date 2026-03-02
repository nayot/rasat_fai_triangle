import numpy as np
from .geo_logic import GeoLogic

class RASATScorer:
    def __init__(self, track_points, config):
        self.geo = GeoLogic()
        self.points = self._filter_noise(track_points)
        self.config = config
        self.sp = tuple(config['coordinates']['start_point'])
        self.fp = tuple(config['coordinates']['finish_point'])
        self.np_points = np.array([p[:2] for p in self.points])

    def _filter_noise(self, pts):
        if not pts: return []
        filtered = [pts[0]]
        for i in range(1, len(pts)):
            dist = self.geo.calculate_distance(pts[i-1][:2], pts[i][:2])
            if dist < 0.05: # Spike filter
                filtered.append(pts[i])
        return filtered

    def calculate_results(self):
        status_msg = "SUCCESS"
        is_valid = True

        # 1. ตรวจสอบจุด Start (SP)
        if not self.geo.is_within_radius(self.points[0][:2], self.sp, self.config['coordinates']['sp_radius_meters']):
            status_msg = "FAILED: OUTSIDE START RADIUS"
            is_valid = False
        
        # 2. ค้นหา Vertices (V1=SP, V2 & V3 อยู่ใน Track, ปิด Leg 3 ที่ FP)
        v1, v2, v3, tri_dist, is_fai = self._find_optimal_open_triangle()

        # 3. ตรวจสอบจุด Finish (FP)
        if is_valid and not self.geo.is_within_radius(self.points[-1][:2], self.fp, self.config['coordinates']['fp_radius_meters']):
            status_msg = "FAILED: OUTSIDE FINISH RADIUS"
            is_valid = False

        gate_coords = self._get_gate_coordinates((v1, v2, v3))
        scored_gates = self._check_gate_passage_fast(gate_coords)
        
        mult = self.config['scoring_params']['fai_multiplier'] if is_fai else self.config['scoring_params']['flat_multiplier']
        effective_km = (tri_dist * mult) if is_valid else 0.0

        return {
            "is_valid": is_valid,
            "status_message": status_msg,
            "triangle_km": round(tri_dist, 2),
            "effective_km": round(effective_km, 2),
            "is_fai": is_fai,
            "multiplier": mult,
            "gate_coords": gate_coords,
            "total_gates": len(gate_coords),
            "scored_gates": scored_gates,
            "vertices": (v1, v2, v3),
            "finish_point": self.fp
        }

    def _find_optimal_open_triangle(self):
        """ค้นหาสามเหลี่ยมที่เปิดจุดเริ่ม (SP) และจบ (FP) ต่างกัน"""
        best_dist, best_idx, v1, n = 0, (0, 0), self.sp, len(self.points)
        
        # Pass 1: Coarse Search
        step = max(1, n // 60)
        for i in range(1, n, step):
            for j in range(i + step, n, step):
                v2, v3 = self.points[i][:2], self.points[j][:2]
                # กฎ Open Triangle: Leg 1: V1-V2, Leg 2: V2-V3, Leg 3: V3-FP
                is_fai, d = self._check_open_fai_threshold(v1, v2, v3, self.fp)
                m = 1.5 if is_fai else 1.0
                if d * m > best_dist:
                    best_dist, best_idx = d * m, (i, j)

        # Pass 2: Fine Search
        ref_i, ref_j = best_idx
        sr = max(5, n // 80)
        f_dist, f_v, f_is_fai, r_dist = 0, (v1, None, None), False, 0
        for i in range(max(1, ref_i - sr), min(n, ref_i + sr)):
            for j in range(max(i + 1, ref_j - sr), min(n, ref_j + sr), 2):
                v2, v3 = self.points[i][:2], self.points[j][:2]
                is_fai, d = self._check_open_fai_threshold(v1, v2, v3, self.fp)
                m = 1.5 if is_fai else 1.0
                if d * m > f_dist:
                    f_dist, f_v, f_is_fai, r_dist = d * m, (v1, v2, v3), is_fai, d
        return f_v[0], f_v[1], f_v[2], r_dist, f_is_fai

    def _check_open_fai_threshold(self, v1, v2, v3, fp):
        d1 = self.geo.calculate_distance(v1, v2)
        d2 = self.geo.calculate_distance(v2, v3)
        d3 = self.geo.calculate_distance(v3, fp) # Leg สุดท้ายวิ่งเข้า FP
        total = d1 + d2 + d3
        is_fai = min(d1, d2, d3) >= (total * 0.28)
        return is_fai, total

    def _get_gate_coordinates(self, vertices):
        interval = self.config['scoring_params']['hidden_gate_interval_km']
        gates = []
        # Leg 1: V1-V2, Leg 2: V2-V3, Leg 3: V3-FP
        legs = [(vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], self.fp)]
        for p1, p2 in legs:
            d = self.geo.calculate_distance(p1, p2)
            for k in range(1, int(d / interval) + 1):
                frac = (k * interval) / d
                gates.append((p1[0] + (p2[0]-p1[0])*frac, p1[1] + (p2[1]-p1[1])*frac))
        return gates

    def _check_gate_passage_fast(self, gates):
        count = 0
        radius_km = self.config['scoring_params']['hidden_gate_radius_meters'] / 1000.0
        approx_deg = radius_km / 111.0 
        for g_pos in gates:
            mask = (np.abs(self.np_points[:, 0] - g_pos[0]) < approx_deg) & \
                   (np.abs(self.np_points[:, 1] - g_pos[1]) < approx_deg)
            for p in self.np_points[mask]:
                if self.geo.calculate_distance(p, g_pos) <= radius_km:
                    count += 1
                    break
        return count