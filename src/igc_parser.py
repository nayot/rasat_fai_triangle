class IGCParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        points = []
        pilot_name = "Unknown Pilot"
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # ดึงชื่อนักบินจาก Header (H-Record)
                    if line.startswith('HFPLTPILOT') or line.startswith('HFPILOT'):
                        parts = line.split(':')
                        if len(parts) > 1:
                            pilot_name = parts[-1].strip()
                        else:
                            # กรณีไม่มีเครื่องหมาย : ให้ตัดคำแรกออก
                            pilot_name = line[10:].strip()

                    # แกะข้อมูลพิกัดและความสูงจาก B-Record
                    if line.startswith('B') and len(line) >= 35:
                        time_str = line[1:7]
                        lat = self._to_dec(line[7:15], True)
                        lon = self._to_dec(line[15:24], False)
                        
                        # ลองดึง GPS Altitude (30-35) ถ้าเป็น 0 ให้ลอง Baro Altitude (25-30)
                        try:
                            gps_alt = int(line[30:35])
                            baro_alt = int(line[25:30])
                            # เลือกใช้ค่าที่ไม่เป็น 0 (ลำดับความสำคัญ: GPS > Baro)
                            alt = gps_alt if gps_alt > 0 else baro_alt
                        except:
                            alt = 0
                            
                        points.append((lat, lon, alt, time_str))
            
            return pilot_name, points
        except Exception as e:
            print(f"Parser Error: {e}")
            return pilot_name, []

    def _to_dec(self, raw, is_lat):
        try:
            # Latitude: DDMMmmmN (8 chars) | Longitude: DDDMMmmmE (9 chars)
            d_len = 2 if is_lat else 3
            deg = int(raw[:d_len])
            minutes = float(raw[d_len:-1]) / 1000.0
            dec = deg + (minutes / 60.0)
            return -dec if raw[-1] in ['S', 'W'] else dec
        except:
            return 0.0