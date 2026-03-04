import numpy as np
from datetime import datetime
from .geo_logic import GeoLogic

class RASATScorer:
    def __init__(self, track_points, config):
        self.geo = GeoLogic()
        self.config = config
        self.track = track_points # (lat, lon, alt, time_str)
        self.sp = tuple(config['coordinates']['start_point'])
        self.fp = tuple(config['coordinates']['finish_point'])
        self.sp_radius_km = config['coordinates']['sp_radius_meters'] / 1000.0
        self.fp_radius_km = config['coordinates']['fp_radius_meters'] / 1000.0
        
        self.points, self.status_msg, self.duration_sec = self._trim_track_to_task(track_points)
        
        # แปลงเป็น NumPy Array ครั้งเดียวเพื่อใช้คำนวณแบบ Vectorized
        if self.points:
            self.np_points = np.array([p[:2] for p in self.points])
        else:
            self.np_points = np.empty((0, 2))

    def _trim_track_to_task(self, pts):
        if not pts: return [], "EMPTY TRACK", 0
        start_idx, finish_idx = None, None
        
        # หาจุดเข้า Start
        for i, p in enumerate(pts):
            if self.geo.calculate_distance(p[:2], self.sp) <= self.sp_radius_km:
                start_idx = i
                break
        if start_idx is None:
            return [], f"OUTSIDE START", 0

        # หาจุดเข้า Finish (ย้อนกลับ)
        for i in range(len(pts) - 1, start_idx, -1):
            if self.geo.calculate_distance(pts[i][:2], self.fp) <= self.fp_radius_km:
                finish_idx = i
                break
        if finish_idx is None:
            return [], f"NOT REACHED FINISH", 0

        try:
            t1 = datetime.strptime(pts[start_idx][3], "%H%M%S")
            t2 = datetime.strptime(pts[finish_idx][3], "%H%M%S")
            duration = (t2 - t1).total_seconds()
        except: duration = 0

        return pts[start_idx : finish_idx + 1], "SUCCESS", duration

    def calculate_results(self):
        if not self.points:
            return self._empty_result(self.status_msg)

        v1, v2, v3, tri_dist, is_fai = self._find_optimal_open_triangle()
        gate_coords = self._get_gate_coordinates((v1, v2, v3))
        scored_gates = self._check_gate_passage_fast(gate_coords)
        
        mult = self.config['scoring_params']['fai_multiplier'] if is_fai else self.config['scoring_params']['flat_multiplier']
        
        return {
            "is_valid": True, "status_message": "SUCCESS",
            "triangle_km": round(tri_dist, 2), "effective_km": round(tri_dist * mult, 2),
            "is_fai": is_fai, "multiplier": mult, "duration_sec": self.duration_sec,
            "gate_coords": gate_coords, "total_gates": len(gate_coords),
            "scored_gates": scored_gates, "vertices": (v1, v2, v3), "finish_point": self.fp
        }

    def _find_optimal_open_triangle(self):
        n = len(self.points)
        if n < 3: return self.sp, self.sp, self.sp, 0, False
        best_dist, best_idx, v1 = 0, (0, 0), self.sp
        
        # Step optimization เพื่อป้องกันการค้าง
        step = max(1, n // 40)
        for i in range(0, n, step):
            for j in range(i + step, n, step):
                v2, v3 = self.points[i][:2], self.points[j][:2]
                is_fai, d = self._check_open_fai_threshold(v1, v2, v3, self.fp)
                if d * (1.5 if is_fai else 1.0) > best_dist:
                    best_dist, best_idx = d * (1.5 if is_fai else 1.0), (i, j)

        ref_i, ref_j = best_idx
        sr = max(2, n // 80)
        f_dist, f_v, f_is_fai, r_dist = 0, (v1, None, None), False, 0
        for i in range(max(0, ref_i - sr), min(n, ref_i + sr)):
            for j in range(max(i + 1, ref_j - sr), min(n, ref_j + sr)):
                v2, v3 = self.points[i][:2], self.points[j][:2]
                is_fai, d = self._check_open_fai_threshold(v1, v2, v3, self.fp)
                m = 1.5 if is_fai else 1.0
                if d * m > f_dist:
                    f_dist, f_v, f_is_fai, r_dist = d * m, (v1, v2, v3), is_fai, d
        return f_v[0], f_v[1], f_v[2], r_dist, f_is_fai

    def _check_open_fai_threshold(self, v1, v2, v3, fp):
        d1 = self.geo.calculate_distance(v1, v2)
        d2 = self.geo.calculate_distance(v2, v3)
        d3 = self.geo.calculate_distance(v3, fp)
        total = max(0, d1 - self.sp_radius_km) + d2 + max(0, d3 - self.fp_radius_km)
        is_fai = min(d1, d2, d3) >= (total * 0.28) if total > 0 else False
        return is_fai, total

    def _get_gate_coordinates(self, vertices):
        interval = self.config['scoring_params']['hidden_gate_interval_km']
        gates = []
        legs = [(vertices[0], vertices[1]), (vertices[1], vertices[2]), (vertices[2], self.fp)]
        for p1, p2 in legs:
            d = self.geo.calculate_distance(p1, p2)
            if d < interval: continue
            for k in range(1, int(d / interval) + 1):
                frac = (k * interval) / d
                gates.append((p1[0] + (p2[0]-p1[0])*frac, p1[1] + (p2[1]-p1[1])*frac))
        return gates

    def _check_gate_passage_fast(self, gates):
        if self.np_points.size == 0 or not gates: return 0
        count = 0
        r_km = self.config['scoring_params']['hidden_gate_radius_meters'] / 1000.0
        # ประมวลผลแบบ Vectorized เพื่อความเร็ว
        for g in gates:
            # คำนวณ Euclidean distance แบบหยาบๆ เพื่อกรองจุด
            dist_sq = np.sum((self.np_points - np.array(g))**2, axis=1)
            # 0.01 deg ~= 1.1km
            near_indices = np.where(dist_sq < (r_km/100)**2)[0]
            for idx in near_indices:
                if self.geo.calculate_distance(self.np_points[idx], g) <= r_km:
                    count += 1
                    break
        return count

    def _empty_result(self, msg):
        return {
            "is_valid": False, "status_message": msg, "triangle_km": 0.0, "effective_km": 0.0,
            "is_fai": False, "multiplier": 1.0, "duration_sec": 0, "gate_coords": [], 
            "total_gates": 0, "scored_gates": 0, "vertices": (self.sp, self.sp, self.sp), "finish_point": self.fp
        }