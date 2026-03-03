import numpy as np
from .geo_logic import GeoLogic

class RASATScorer:
    def __init__(self, track_points, config):
        self.geo = GeoLogic()
        self.config = config
        
        # 1. โหลดพิกัดและรัศมีจาก Config
        self.sp = tuple(config['coordinates']['start_point'])
        self.fp = tuple(config['coordinates']['finish_point'])
        self.sp_radius_km = config['coordinates']['sp_radius_meters'] / 1000.0
        self.fp_radius_km = config['coordinates']['fp_radius_meters'] / 1000.0
        
        # 2. กรอง Noise และทำความสะอาด Track เบื้องต้น
        self.all_points = self._filter_noise(track_points)
        
        # 3. ตัด Track ให้เหลือเฉพาะช่วง Task (จากขอบ SP ถึงขอบ FP)
        self.points, self.status_msg = self._trim_track_to_task(self.all_points)
        
        if self.points:
            self.np_points = np.array([p[:2] for p in self.points])
        else:
            self.np_points = np.empty((0, 2))

    def _filter_noise(self, pts):
        if not pts: return []
        filtered = [pts[0]]
        for i in range(1, len(pts)):
            # ระยะระหว่างจุดไม่ควรเกิน 50 เมตรต่อวินาที (180 กม./ชม.) สำหรับพารามอเตอร์
            dist = self.geo.calculate_distance(pts[i-1][:2], pts[i][:2])
            if dist < 0.05: 
                filtered.append(pts[i])
        return filtered

    def _trim_track_to_task(self, pts):
        """ค้นหาจุดเริ่ม Task (เข้า SP ครั้งแรก) และจุดจบ Task (เข้า FP ครั้งสุดท้าย)"""
        start_idx = None
        finish_idx = None

        # หาจุดแรกที่นักบิน 'สัมผัส' รัศมี Start Point
        for i, p in enumerate(pts):
            if self.geo.calculate_distance(p[:2], self.sp) <= self.sp_radius_km:
                start_idx = i
                break
        
        if start_idx is None:
            return [], f"FAILED: OUTSIDE START RADIUS ({int(self.sp_radius_km*1000)}m)"

        # หาจุดสุดท้ายที่นักบิน 'สัมผัส' รัศมี Finish Point (หลังจากเริ่ม Task แล้ว)
        for i in range(len(pts) - 1, start_idx, -1):
            if self.geo.calculate_distance(pts[i][:2], self.fp) <= self.fp_radius_km:
                finish_idx = i
                break
        
        if finish_idx is None:
            return [], f"FAILED: DID NOT REACH FINISH RADIUS ({int(self.fp_radius_km*1000)}m)"

        return pts[start_idx : finish_idx + 1], "SUCCESS"

    def calculate_results(self):
        if not self.points:
            return self._empty_result(self.status_msg)

        # ค้นหาจุด Turnpoints (V2, V3) ที่ดีที่สุดในช่วงที่บิน Task
        v1, v2, v3, tri_dist, is_fai = self._find_optimal_open_triangle()

        # สร้างจุดตรวจสอบ Hidden Gates
        gate_coords = self._get_gate_coordinates((v1, v2, v3))
        scored_gates = self._check_gate_passage_fast(gate_coords)
        
        mult = self.config['scoring_params']['fai_multiplier'] if is_fai else self.config['scoring_params']['flat_multiplier']
        
        # ระยะทางสุทธิ (ใช้ tri_dist ซึ่งคำนวณแบบหักลบรัศมีแล้ว)
        effective_km = tri_dist * mult

        return {
            "is_valid": True,
            "status_message": "SUCCESS",
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
        """ค้นหาสามเหลี่ยมที่ให้คะแนนสูงสุด"""
        best_dist, best_idx, v1, n = 0, (0, 0), self.sp, len(self.points)
        
        # Coarse Search (เพื่อความเร็ว)
        step = max(1, n // 50)
        for i in range(0, n, step):
            for j in range(i + step, n, step):
                v2, v3 = self.points[i][:2], self.points[j][:2]
                is_fai, d = self._check_open_fai_threshold(v1, v2, v3, self.fp)
                m = 1.5 if is_fai else 1.0
                if d * m > best_dist:
                    best_dist, best_idx = d * m, (i, j)

        # Fine Search (ค้นหาละเอียดรอบจุดที่เจอ)
        ref_i, ref_j = best_idx
        sr = max(5, n // 100)
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
        """คำนวณระยะทางแบบหักลบรัศมี Cylinder SP/FP ออกจากระยะรวม"""
        d1 = self.geo.calculate_distance(v1, v2)
        d2 = self.geo.calculate_distance(v2, v3)
        d3 = self.geo.calculate_distance(v3, fp)
        
        # ระยะทางที่นับจริงคือระยะพ้นขอบรัศมี (ขอบถัง)
        total_task_dist = max(0, d1 - self.sp_radius_km) + d2 + max(0, d3 - self.fp_radius_km)
        
        # กฎ FAI Triangle 28%
        is_fai = min(d1, d2, d3) >= (total_task_dist * 0.28)
        return is_fai, total_task_dist

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
        count = 0
        if self.np_points.size == 0: return 0
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

    def _empty_result(self, msg):
        return {
            "is_valid": False, "status_message": msg, "triangle_km": 0.0, "effective_km": 0.0,
            "is_fai": False, "multiplier": 1.0, "gate_coords": [], "total_gates": 0,
            "scored_gates": 0, "vertices": (self.sp, self.sp, self.sp), "finish_point": self.fp
        }