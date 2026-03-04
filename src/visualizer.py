import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from .geo_logic import GeoLogic

class Visualizer:
    @staticmethod
    def plot_task_result(track_points, res, config, pilot_name="Unknown"):
        """
        Standalone Plotting สำหรับสร้างรูปภาพสรุปผลคุณภาพสูง (DPI สูง)
        """
        geo = GeoLogic()
        # ข้อมูล Track: (lat, lon, alt_m, time_str)
        lats, lons = zip(*[p[:2] for p in track_points])
        alts_ft = [p[2] * 3.28084 for p in track_points]
        
        # สร้าง Layout แบบ 2 แถว (Map และ Altitude)
        fig, (ax_map, ax_alt) = plt.subplots(2, 1, figsize=(10, 12), 
                                            gridspec_kw={'height_ratios': [3, 1]})
        plt.subplots_adjust(bottom=0.15, hspace=0.3)

        # --- 1. Map Plot ---
        # วาดเส้นทางบิน (Dark Blue)
        ax_map.plot(lons, lats, color='darkblue', alpha=0.4, linewidth=1, label='Actual Track', zorder=1)
        
        # วาดเส้น Open Triangle (Orange)
        v = res['vertices']
        fp = res['finish_point']
        v_lats = [v[0][0], v[1][0], v[2][0], fp[0]]
        v_lons = [v[0][1], v[1][1], v[2][1], fp[1]]
        tri_color = 'green' if res['is_fai'] else 'darkorange'
        ax_map.plot(v_lons, v_lats, color=tri_color, linewidth=2.5, label="Scored Triangle Path", zorder=2)
        
        # พล็อต Hidden Gates (เขียว/แดง)
        gate_radius_m = config['scoring_params']['hidden_gate_radius_meters']
        radius_deg = gate_radius_m / 111320.0 
        if res.get('gate_coords'):
            track_np = np.array([p[:2] for p in track_points])
            for gate in res['gate_coords']:
                # ตรวจสอบการผ่าน Gate
                dist = np.sqrt(np.sum((track_np - np.array(gate))**2, axis=1))
                is_passed = np.any(dist <= (gate_radius_m / 1000.0))
                
                gate_color = 'limegreen' if is_passed else 'red'
                circle = Circle((gate[1], gate[0]), radius_deg, color=gate_color, fill=True, alpha=0.15, zorder=3)
                ax_map.add_patch(circle)
                ax_map.scatter(gate[1], gate[0], color=gate_color, s=10, alpha=0.6, zorder=4)

        # จุด Start / Finish
        sp = config['coordinates']['start_point']
        ax_map.scatter(sp[1], sp[0], color='blue', marker='X', s=100, label='Start Point', zorder=5)
        ax_map.scatter(fp[1], fp[0], color='red', marker='X', s=100, label='Finish Point', zorder=5)
        
        ax_map.set_title(f"RASAT Analysis: {pilot_name} - {config['task_name']}", fontsize=12, fontweight='bold')
        ax_map.legend(loc='upper right', fontsize='small')
        ax_map.set_aspect('equal')
        ax_map.grid(True, linestyle='--', alpha=0.4)

        # --- 2. Altitude Plot (Feet) ---
        ax_alt.plot(alts_ft, color='teal', linewidth=1, label='Altitude')
        ax_alt.fill_between(range(len(alts_ft)), alts_ft, color='teal', alpha=0.1)
        ax_alt.set_ylabel("Altitude (ft)", fontsize=9)
        ax_alt.set_xlabel("Track Points Index", fontsize=9)
        ax_alt.grid(True, linestyle=':', alpha=0.5)

        # --- 3. Summary Statistics & Copyright ---
        dur_sec = res.get('duration_sec', 0)
        h = int(dur_sec // 3600); m = int((dur_sec % 3600) // 60); s = dur_sec % 60
        duration_str = f"{h:02}:{m:02}:{s:04.1f}"

        stats_text = (
            f"Triangle: {res['triangle_km']:.2f} km | Multiplier: {res['multiplier']}x | "
            f"EFFECTIVE DISTANCE: {res['effective_km']:.2f} km\n"
            f"Duration: {duration_str} | Gates Scored: {res['scored_gates']}/{res['total_gates']}\n"
            f"Copyright © Nayot Kurukitkoson (nayot@ieee.org)"
        )
        
        fig.text(0.5, 0.04, stats_text, ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.6", fc="whitesmoke", ec="gray", alpha=0.9))
        
        plt.show() # หรือ plt.savefig() ตามต้องการ