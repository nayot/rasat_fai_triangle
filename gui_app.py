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
        self.root.title("RASAT/FAI Analyzer v1.2")
        self.root.geometry("1200x950")
        self.copyright_text = "Copyright © Nayot Kurukitkoson (nayot@ieee.org)"
        self.geo = GeoLogic()
        
        self.config_path = "task_config.json"
        self.load_config()
        
        self.result_dir = tk.StringVar(value=os.path.abspath("results_track_analysis"))
        self.preview_mode_var = tk.BooleanVar(value=False)
        self._set_matplotlib_font()
        self._setup_ui()

    def _set_matplotlib_font(self):
        plt.rcParams.update({'font.size': 7})
        for f in ['Tahoma', 'Ayuthaya', 'Thonburi', 'Sans-serif']:
            try:
                plt.rcParams['font.family'] = f
                break
            except: continue

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    self.config = json.load(f)
            except: self._set_default_config()
        else: self._set_default_config()

    def _set_default_config(self):
        self.config = {
            "task_name": "New Task",
            "coordinates": {"start_point": [14.422, 100.5], "finish_point": [14.422, 100.5], "sp_radius_meters": 200, "fp_radius_meters": 200},
            "scoring_params": {"hidden_gate_interval_km": 1.0, "hidden_gate_radius_meters": 200, "fai_multiplier": 1.5, "flat_multiplier": 1.0},
            "max_altitude_ft": 3000
        }

    def _setup_ui(self):
        # --- UI Layout ---
        header = ttk.Frame(self.root); header.pack(fill=tk.X, padx=15, pady=5)
        ttk.Label(header, text="RASAT/FAI Analyzer v1.2", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL); paned.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(paned, padding=10); paned.add(left, weight=1)
        
        conf = ttk.LabelFrame(left, text=" Task Config "); conf.pack(fill=tk.X, pady=5)
        ttk.Label(conf, text="Lat:").grid(row=0, column=0); self.ent_lat = ttk.Entry(conf); self.ent_lat.insert(0, self.config['coordinates']['start_point'][0]); self.ent_lat.grid(row=0, column=1)
        ttk.Label(conf, text="Lon:").grid(row=1, column=0); self.ent_lon = ttk.Entry(conf); self.ent_lon.insert(0, self.config['coordinates']['start_point'][1]); self.ent_lon.grid(row=1, column=1)
        ttk.Label(conf, text="Max Alt(ft):").grid(row=2, column=0); self.ent_max_alt = ttk.Entry(conf); self.ent_max_alt.insert(0, self.config.get("max_altitude_ft", 3000)); self.ent_max_alt.grid(row=2, column=1)
        ttk.Button(conf, text="Update Config", command=self.update_config_from_ui).grid(row=3, columnspan=2, pady=5)

        sett = ttk.LabelFrame(left, text=" Output Settings "); sett.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(sett, text="Preview Mode", variable=self.preview_mode_var).pack(anchor=tk.W)
        ttk.Entry(sett, textvariable=self.result_dir).pack(fill=tk.X, padx=5, pady=5)

        self.btn_process = tk.Button(left, text="ANALYZE IGC FILES", command=self.process_files, bg="#4CAF50", font=("Arial", 12, "bold"), height=2)
        self.btn_process.pack(fill=tk.X, pady=20)
        self.status_label = ttk.Label(left, text="Ready", foreground="green"); self.status_label.pack()

        # --- Plot Area (สร้าง Axes ไว้รอเลยเพื่อลดการกระพริบ) ---
        right = ttk.LabelFrame(paned, text=" Analysis Plot "); paned.add(right, weight=3)
        self.fig, (self.ax_map, self.ax_alt) = plt.subplots(2, 1, figsize=(8, 10), constrained_layout=True, gridspec_kw={'height_ratios': [2.5, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_config_from_ui(self):
        try:
            self.config['coordinates']['start_point'] = [float(self.ent_lat.get()), float(self.ent_lon.get())]
            self.config['coordinates']['finish_point'] = self.config['coordinates']['start_point']
            self.config['max_altitude_ft'] = float(self.ent_max_alt.get())
            with open(self.config_path, "w", encoding='utf-8') as f: json.dump(self.config, f, indent=4)
            messagebox.showinfo("Success", "Config Updated")
        except: messagebox.showerror("Error", "Invalid values")

    def process_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("IGC files", "*.igc")])
        if not paths: return
        
        is_p = self.preview_mode_var.get()
        if not is_p: os.makedirs(self.result_dir.get(), exist_ok=True)
        
        summary_list = []
        for path in paths:
            try:
                # --- จุดแก้ไข: ดึงชื่อนักบินจากชื่อไฟล์ (ไม่รวมนามสกุล) ---
                pilot_filename = os.path.splitext(os.path.basename(path))[0]
                
                # ใช้ Parser ดึงแค่พิกัด Track (ข้ามชื่อนักบินในไฟล์)
                _, track = IGCParser(path).parse()
                if not track: continue
                
                res = RASATScorer(track, self.config).calculate_results()
                
                h, r = divmod(res.get('duration_sec', 0), 3600); m, s = divmod(r, 60)
                dur_str = f"{int(h):02}:{int(m):02}:{s:04.1f}"
                
                # บันทึกรูปภาพโดยใช้ชื่อไฟล์เป็นชื่อนักบิน
                save_path = None if is_p else os.path.join(self.result_dir.get(), f"{pilot_filename}_analysis.png")
                self._draw_plot(track, res, pilot_filename, dur_str, save_path)
                
                summary_list.append({
                    "Pilot": pilot_filename,
                    "Status": res.get("status_message"),
                    "Triangle_km": round(res.get("triangle_km", 0), 2),
                    "Effective_km": round(res.get("effective_km", 0), 2),
                    "Duration": dur_str,
                    "Scored_Gates": res.get("scored_gates", 0),
                    "Total_Gates": res.get("total_gates", 0),
                    "Type": "FAI" if res.get("is_fai") else "Flat"
                })
                self.status_label.config(text=f"Processed: {pilot_filename}")
                self.root.update()
            except Exception as e: 
                print(f"Error processing {path}: {e}")

        if summary_list and not is_p:
            summary_list.sort(key=lambda x: x['Effective_km'], reverse=True)
            csv_p = os.path.join(self.result_dir.get(), "competition_results_v139.csv")
            with open(csv_p, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=summary_list[0].keys()); w.writeheader(); w.writerows(summary_list)
            messagebox.showinfo("Done", "CSV Leaderboard Generated using Filenames!")
            
    def _draw_plot(self, track, res, pilot, dur_str, save_p):
        self.ax_map.clear(); self.ax_alt.clear()
        
        lats, lons = zip(*[p[:2] for p in track])
        alts_ft = [p[2] * 3.28084 for p in track]
        
        # --- คำนวณเวลา (นาที) สำหรับแกน X ---
        # สมมติว่า IGC บันทึกทุก 1 วินาที (หากไม่ใช่ โปรแกรมจะคำนวณจากจำนวนจุด)
        times_min = np.arange(len(track)) / 60.0 
        
        # 1. Map Plot (เหมือนเดิม)
        self.ax_map.plot(lons, lats, color='blue', alpha=0.3, linewidth=0.7)
        if 'gate_coords' in res:
            r_km = self.config['scoring_params']['hidden_gate_radius_meters'] / 1000.0
            for g in res['gate_coords']:
                passed = any(self.geo.calculate_distance(p[:2], g) <= r_km for p in track)
                c = 'limegreen' if passed else 'red'
                self.ax_map.add_patch(patches.Circle((g[1], g[0]), r_km/111, color=c, alpha=0.2))
                self.ax_map.scatter(g[1], g[0], color=c, s=12, zorder=5)

        if res.get('is_valid'):
            v = list(res['vertices']); p = v + [v[0]]; vlats, vlons = zip(*p)
            self.ax_map.plot(vlons, vlats, color='darkorange', linewidth=2, zorder=10)

        self.ax_map.set_aspect('equal', adjustable='datalim'); self.ax_map.grid(True, alpha=0.15)

        # 2. Altitude Plot (เปลี่ยนแกน X เป็น Time)
        self.ax_alt.plot(times_min, alts_ft, color='teal', linewidth=1)
        self.ax_alt.fill_between(times_min, alts_ft, color='teal', alpha=0.1)
        
        max_limit = float(self.config.get("max_altitude_ft", 3000))
        self.ax_alt.axhline(y=max_limit, color='red', linestyle='--', linewidth=1, label=f"Limit {int(max_limit)}ft")
        
        self.ax_alt.set_ylim(0, max(max_limit, max(alts_ft) if alts_ft else 0) * 1.2)
        self.ax_alt.set_ylabel("Alt (ft)")
        self.ax_alt.set_xlabel("Time (Minutes)", fontsize=7) # ระบุหน่วยเป็นนาที
        self.ax_alt.grid(True, alpha=0.2)

        # Summary Text (Small Font 5.5)
        title = (f"Pilot: {pilot} | Dist: {res['triangle_km']:.2f} km | Eff: {res['effective_km']:.2f} km\n"
                 f"Time: {dur_str} | Gates: {res['scored_gates']}/{res['total_gates']}")
        self.fig.suptitle(title, fontsize=5.5, fontweight='bold', y=0.98)

        if save_p: self.fig.savefig(save_p, dpi=200, bbox_inches='tight')
        self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk(); app = RASATGui(root); root.mainloop()