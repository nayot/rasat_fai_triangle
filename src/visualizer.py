import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from .geo_logic import GeoLogic

class Visualizer:
    @staticmethod
    def plot_task_result(track_points, vertices, res, config):
        geo = GeoLogic()
        lats, lons = zip(*[p[:2] for p in track_points])
        
        # ปรับการลากเส้น Vertices: V1 -> V2 -> V3 -> FP
        v1, v2, v3 = vertices
        fp = res['finish_point']
        v_lats = [v1[0], v2[0], v3[0], fp[0]]
        v_lons = [v1[1], v2[1], v3[1], fp[1]]
        
        fig, ax = plt.subplots(figsize=(12, 9))
        plt.subplots_adjust(bottom=0.15)

        ax.plot(lons, lats, color='gray', alpha=0.3, label='Actual Track', zorder=1)
        
        # เส้นสามเหลี่ยม (Open Triangle)
        tri_color = 'green' if res['is_fai'] else 'orange'
        ax.plot(v_lons, v_lats, color=tri_color, linewidth=2, label="Open Triangle Path", zorder=2)
        
        # พล็อต Hidden Gates
        gate_radius_m = config['scoring_params']['hidden_gate_radius_meters']
        radius_deg = gate_radius_m / 111320.0 
        if res['gate_coords']:
            for gate in res['gate_coords']:
                is_passed = any(geo.is_within_radius(p[:2], gate, gate_radius_m) for p in track_points)
                gate_color = 'green' if is_passed else 'red'
                circle = Circle((gate[1], gate[0]), radius_deg, color=gate_color, fill=True, alpha=0.15, zorder=3)
                ax.add_patch(circle)
                ax.scatter(gate[1], gate[0], color=gate_color, s=15, alpha=0.6, zorder=4)

        sp = config['coordinates']['start_point']
        ax.scatter(sp[1], sp[0], color='blue', marker='X', s=150, label='Target SP', zorder=5)
        ax.scatter(fp[1], fp[0], color='red', marker='X', s=150, label='Target FP', zorder=5)
        
        # แสดงสถานะ Error เป็นสีแดงถ้าไม่ Valid
        status_color = "black" if res['is_valid'] else "red"
        stats_line = (
            f"Triangle: {res['triangle_km']} km | Mult: {res['multiplier']}x | "
            f"EFFECTIVE: {res['effective_km']} km | "
            f"Gates: {res['scored_gates']}/{res['total_gates']}"
        )
        
        fig.text(0.5, 0.05, stats_line, ha='center', fontsize=11, fontweight='bold', color=status_color,
                 bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=status_color, alpha=0.8))
        
        ax.set_title(f"RASAT/FAI Open Triangle Analysis: {config['task_name']}", pad=20)
        ax.legend(loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_aspect('equal')
        plt.show()