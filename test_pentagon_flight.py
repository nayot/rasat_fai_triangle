import datetime
import random
import math
import os

# พิกัดรูปห้าเหลี่ยมด้านไม่เท่า
SP_FP = (14.34044, 100.61325)
ROUTE_POINTS = [
    SP_FP,                  # จุดเริ่ม
    (14.45000, 100.65000), # จุดเลี้ยว 1
    (14.50000, 100.50000), # จุดเลี้ยว 2
    (14.35000, 100.40000), # จุดเลี้ยว 3
    (14.25000, 100.55000), # จุดเลี้ยว 4
    SP_FP                   # จุดจบ
]

def to_igc_coord(val, is_lat):
    abs_val = abs(val)
    degrees = int(abs_val)
    minutes = (abs_val - degrees) * 60
    m_int = int(minutes)
    m_dec = int((minutes - m_int) * 1000)
    suffix = ('N' if val >= 0 else 'S') if is_lat else ('E' if val >= 0 else 'W')
    fmt = f"{degrees:02d}" if is_lat else f"{degrees:03d}"
    return f"{fmt}{m_int:02d}{m_dec:03d}{suffix}"

def generate_pentagon_igc(filename="data/test_pentagon.igc"):
    start_time = datetime.datetime.now().replace(hour=11, minute=0, second=0)
    current_time = start_time
    if not os.path.exists('data'): os.makedirs('data')

    with open(filename, "w") as f:
        f.write("AXXX001Pentagon Track Simulation\n")
        f.write(f"HFDTE{start_time.strftime('%d%m%y')}\n")
        
        for i in range(len(ROUTE_POINTS) - 1):
            p1, p2 = ROUTE_POINTS[i], ROUTE_POINTS[i+1]
            steps = 400 # จำลองการบิน Leg ละประมาณ 7 นาที
            
            for step in range(steps):
                frac = step / steps
                # ใส่ Noise และ Drift เล็กน้อย
                lat = p1[0] + (p2[0] - p1[0]) * frac + random.uniform(-0.0002, 0.0002)
                lon = p1[1] + (p2[1] - p1[1]) * frac + random.uniform(-0.0002, 0.0002)
                
                alt = 500 + random.randint(-20, 20)
                f.write(f"B{current_time.strftime('%H%M%S')}{to_igc_coord(lat, True)}{to_igc_coord(lon, False)}A{alt:05d}{alt:05d}\n")
                current_time += datetime.timedelta(seconds=1)

    print(f"Generated Pentagon Track IGC: {filename}")

if __name__ == "__main__":
    generate_pentagon_igc()