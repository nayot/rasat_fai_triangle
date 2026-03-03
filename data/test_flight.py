import datetime
import random
import math
import os

filename = "data/test_flat_triangle_with_errors.igc"
ROUTE_POINTS = [
    (14.340440, 100.613250), # FXC001 (SP)
    (14.345000, 100.590000), # FXC002
    (14.280000, 100.580000), # FXC003
    (14.340280, 100.613300)  # FXC004 (FP)
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

def generate_high_error_igc(filename="data/test_error_flight.igc"):
    start_time = datetime.datetime.now().replace(hour=10, minute=0, second=0)
    current_time = start_time
    
    if not os.path.exists('data'): os.makedirs('data')

    with open(filename, "w") as f:
        f.write("AXXX001Flight Error Simulation\n")
        f.write(f"HFDTE{start_time.strftime('%d%m%y')}\n")
        
        for i in range(len(ROUTE_POINTS) - 1):
            p1, p2 = ROUTE_POINTS[i], ROUTE_POINTS[i+1]
            steps = 400 
            
            # สุ่มค่าเบี่ยงเบนสำหรับ Leg นี้ (ทำให้บาง Leg บินตรง บาง Leg บินเบี้ยว)
            drift_factor = random.uniform(0.001, 0.004) 

            for step in range(steps):
                frac = step / steps
                # ใส่ Sine Drift เพื่อให้ Track โค้งออกจากเส้นตรง (มีโอกาส Miss Gates)
                offset = math.sin(frac * math.pi) * drift_factor
                
                lat = p1[0] + (p2[0] - p1[0]) * frac + offset
                lon = p1[1] + (p2[1] - p1[1]) * frac + (random.uniform(-0.0001, 0.0001))
                
                # จำลอง GPS Spike (Noise) ทุกๆ 150 วินาที
                if step > 0 and step % 150 == 0:
                    lat += 0.02 
                
                alt = 200 + random.randint(-5, 5)
                f.write(f"B{current_time.strftime('%H%M%S')}{to_igc_coord(lat, True)}{to_igc_coord(lon, False)}A{alt:05d}{alt:05d}\n")
                current_time += datetime.timedelta(seconds=1)

    print(f"Generated High Error IGC: {filename}")

if __name__ == "__main__":
    generate_high_error_igc(filename)