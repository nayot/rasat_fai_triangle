import numpy as np
import os

class IGCParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        raw_points = []
        pilot_name = os.path.splitext(os.path.basename(self.file_path))[0]
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('B') and len(line) >= 35:
                        lat = self._to_dec(line[7:15], True)
                        lon = self._to_dec(line[15:24], False)
                        # ป้องกันพิกัด 0,0 ซึ่งเป็นสาเหตุหลักของเส้นกระโดด
                        if lat == 0 or lon == 0: continue
                        
                        try:
                            alt = int(line[30:35]) if int(line[30:35]) > 0 else int(line[25:30])
                        except: alt = 0
                        raw_points.append([lat, lon, alt, line[1:7]])
            
            # ใช้ Logic กรองจุดกระโดดที่แม่นยำขึ้น
            filtered_points = self._remove_gps_outliers(raw_points)
            return pilot_name, filtered_points
        except Exception as e:
            print(f"Parser Error: {e}")
            return pilot_name, []

    def _remove_gps_outliers(self, pts):
        if len(pts) < 3: return pts
        
        cleaned = [pts[0]]
        # ค่า Threshold สำหรับการกระโดด (0.01 degree ประมาณ 1.1 km)
        # ถ้า 1 วินาทีกระโดดเกิน 500 เมตร (0.0045 deg) ให้ถือว่า Error
        threshold = 0.0045 

        for i in range(1, len(pts)):
            prev = cleaned[-1]
            curr = pts[i]
            
            lat_diff = abs(curr[0] - prev[0])
            lon_diff = abs(curr[1] - prev[1])
            
            # ถ้าจุดใหม่กระโดดห่างจากจุดก่อนหน้ามากเกินไป ให้ข้ามจุดนั้นไปเลย
            if lat_diff < threshold and lon_diff < threshold:
                cleaned.append(curr)
            else:
                # กรณีจุดโดด ให้ข้ามไป (Skip Outlier)
                continue
                
        return cleaned

    def _to_dec(self, raw, is_lat):
        try:
            d_len = 2 if is_lat else 3
            deg = int(raw[:d_len])
            min_raw = raw[d_len:-1]
            # ตรวจสอบว่านาทีไม่ใช่ค่าว่าง
            minutes = float(min_raw) / 1000.0 if min_raw.strip() else 0.0
            dec = deg + (minutes / 60.0)
            return -dec if raw[-1] in ['S', 'W'] else dec
        except: return 0.0