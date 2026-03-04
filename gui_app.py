import os
import json
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import numpy as np

from src.igc_parser import IGCParser
from src.scorer import RASATScorer
from src.geo_logic import GeoLogic

class RASATGui:
    def __init__(self, root):
        self.root = root
        self.root.title("RASAT Analyzer v1.4")
        self.root.geometry("1100x850")
        self.copyright_text = "Copyright © Nayot Kurukitkoson (nayot@ieee.org)"
        self.geo = GeoLogic()
        
        self.config_path = "task_config.json"
        self.load_config()
        self.result_dir = tk.StringVar(value=os.path.join(os.getcwd(), "results"))
        self.preview_mode_var = tk.BooleanVar(value=False)
        self._setup_ui()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    self.config = json.load(f)
            except: self._set_default_config()
        else: self._set_default_config()

    def _set_default_config(self):
        self.config = {
            "task_name": "Task 1",
            "coordinates": {"start_point": [14.422, 100.5], "finish_point": [14.422, 100.5], "sp_radius_meters": 200, "fp_radius_meters": 200},
            "scoring_params": {"hidden_gate_interval_km": 1.0, "hidden_gate_radius_meters": 200, "fai_multiplier": 1.5, "flat_multiplier": 1.0},
            "max_altitude_ft": 3000
        }

    def _setup_ui(self):
        plt.rcParams.update({'font.size': 6})
        main_f = ttk.Frame(self.root, padding=10); main_f.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (Settings)
        left = ttk.Frame(main_f); left.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(left, text="Settings", font=("Arial", 10, "bold")).pack(pady=5)
        
        self.ent_lat = self._add_input(left, "Lat:", self.config['coordinates']['start_point'][0])
        self.ent_lon = self._add_input(left, "Lon:", self.config['coordinates']['start_point'][1])
        self.ent_max_alt = self._add_input(left, "Max Alt(ft):", self.config.get("max_altitude_ft", 3000))
        
        # ใช้ ttk.Button ปกติสำหรับปุ่มตั้งค่า
        ttk.Button(left, text="Update Config", command=self.update_config).pack(fill=tk.X, pady=5)
        ttk.Checkbutton(left, text="Preview Only", variable=self.preview_mode_var).pack(anchor=tk.W, pady=5)
        
        # --- จุดแก้ไข: เปลี่ยนเป็น tk.Button เพื่อให้ใส่สี bg และ height ได้ ---
        self.btn_process = tk.Button(left, text="ANALYZE IGC", command=self.process_files, 
                                     bg="#4CAF50", fg="black", height=2, font=("Arial", 10, "bold"))
        self.btn_process.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(left, text="Ready", foreground="blue")
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # Plot Panel (Right)
        right = ttk.LabelFrame(main_f, text=" Analysis Plot ")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, (self.ax_map, self.ax_alt) = plt.subplots(2, 1, figsize=(7, 9), constrained_layout=True, gridspec_kw={'height_ratios': [2.5, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _add_input(self, parent, lbl, val):
        f = ttk.Frame(parent); f.pack(fill=tk.X, pady=2)
        ttk.Label(f, text=lbl, width=12).pack(side=tk.LEFT)
        e = ttk.Entry(f); e.insert(0, val); e.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        return e

    def update_config(self):
        try:
            self.config['coordinates']['start_point'] = [float(self.ent_lat.get()), float(self.ent_lon.get())]
            self.config['coordinates']['finish_point'] = self.config['coordinates']['start_point']
            self.config['max_altitude_ft'] = float(self.ent_max_alt.get())
            with open(self.config_path, "w", encoding='utf-8') as f: json.dump(self.config, f, indent=4)
            messagebox.showinfo("OK", "Config Saved")
        except: messagebox.showerror("Err", "Invalid Values")

    def process_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("IGC", "*.igc")])
        if not paths: return
        
        is_p = self.preview_mode_var.get()
        out = self.result_dir.get()
        if not is_p: os.makedirs(out, exist_ok=True)
        
        summary = []
        for path in paths:
            pilot = os.path.splitext(os.path.basename(path))[0]
            self.status_label.config(text=f"Analysing: {pilot}", foreground="green")
            self.root.update_idletasks()
            
            _, track = IGCParser(path).parse()
            if not track: continue
            res = RASATScorer(track, self.config).calculate_results()
            
            h, r = divmod(res.get('duration_sec', 0), 3600); m, s = divmod(r, 60)
            dur_str = f"{int(h):02}:{int(m):02}:{s:04.1f}"
            
            # ดึงข้อมูลเพิ่มเติมสำหรับแสดงผล
            tri_type = "FAI" if res.get('is_fai') else "Flat"
            mult = res.get('multiplier', 1.0)
            raw_dist = res.get('triangle_km', 0.0)
            
            save_p = os.path.join(out, f"{pilot}.png") if not is_p else None
            self._draw_plot(track, res, pilot, dur_str, save_p)
            
            # --- อัปเดต CSV ให้มีคอลัมน์ครบถ้วน ---
            summary.append({
                "Pilot": pilot,
                "Type": tri_type,
                "Raw_Dist_km": raw_dist,
                "Multiplier": mult,
                "Effective_km": res['effective_km'], 
                "Duration": dur_str, 
                "Scored_Gates": res['scored_gates'], 
                "Total_Gates": res['total_gates'],
                "Status": res.get('status_message', 'OK')
            })
            
        if summary and not is_p:
            summary.sort(key=lambda x: x['Effective_km'], reverse=True)
            csv_path = os.path.join(out, "competition_results_v141.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=summary[0].keys())
                w.writeheader(); w.writerows(summary)
            messagebox.showinfo("Success", f"Analysis Complete!\nLeaderboard saved to CSV.")

    def _draw_plot(self, track, res, pilot, dur, save_p):
        self.ax_map.clear(); self.ax_alt.clear()
        lats, lons = zip(*[p[:2] for p in track])
        alts_ft = [p[2] * 3.28084 for p in track]
        times_min = np.arange(len(track)) / 60.0
        
        # 1. Map Plot
        self.ax_map.plot(lons, lats, color='blue', alpha=0.3, lw=0.5)
        
        # Fast Gate Check for Visuals
        if res.get('gate_coords'):
            r_km = self.config['scoring_params']['hidden_gate_radius_meters'] / 1000.0
            track_np = np.array([p[:2] for p in track])
            for g in res['gate_coords']:
                dist_sq = np.min(np.sum((track_np - np.array(g))**2, axis=1))
                color = 'limegreen' if dist_sq <= (r_km/111)**2 else 'red'
                self.ax_map.add_patch(patches.Circle((g[1], g[0]), r_km/111, color=color, alpha=0.2))
                self.ax_map.scatter(g[1], g[0], color=color, s=2)

        if res.get('is_valid'):
            v = list(res['vertices']); v_c = v + [v[0]]
            vlats, vlons = zip(*v_c)
            self.ax_map.plot(vlons, vlats, color='orange', lw=1.5, zorder=10)
        
        self.ax_map.set_aspect('equal', adjustable='datalim')
        
        # 2. Altitude Plot
        self.ax_alt.plot(times_min, alts_ft, color='teal', lw=1)
        max_limit = float(self.config.get("max_altitude_ft", 3000))
        self.ax_alt.axhline(max_limit, color='red', ls='--', lw=0.8)
        self.ax_alt.set_ylim(0, max(max_limit, max(alts_ft) if alts_ft else 0) * 1.2)
        
        # --- ปรับปรุงการแสดงผล Summary Text ---
        tri_type = "FAI" if res.get('is_fai') else "Flat"
        mult = res.get('multiplier', 1.0)
        raw_dist = res.get('triangle_km', 0.0)
        
        title = (f"Pilot: {pilot} | Type: {tri_type} (x{mult}) | Raw: {raw_dist}km\n"
                 f"EFFECTIVE: {res['effective_km']}km | Time: {dur} | Gates: {res['scored_gates']}/{res['total_gates']}")
        
        self.fig.suptitle(title, fontsize=5.5, fontweight='bold')
        self.ax_alt.set_xlabel(f"Time (min) | {self.copyright_text}", fontsize=5)
        
        if save_p: self.fig.savefig(save_p, dpi=150, bbox_inches='tight')
        self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk(); app = RASATGui(root); root.mainloop()