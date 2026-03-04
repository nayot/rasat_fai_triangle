import os
import json
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, font as tkfont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import numpy as np

# นำเข้า Module ภายใน project
from src.igc_parser import IGCParser
from src.scorer import RASATScorer
from src.geo_logic import GeoLogic

class RASATGui:
    def __init__(self, root):
        self.root = root
        self.root.title("RASAT Analyzer v1.4.6")
        self.root.geometry("1150x900")
        self.geo = GeoLogic()
        self.copyright_text = "Copyright © Nayot Kurukitkoson (nayot@ieee.org)"
        
        try:
            self.default_font = tkfont.nametofont("TkDefaultFont")
            self.default_font.configure(size=10)
            self.root.option_add("*Font", self.default_font)
        except: pass

        self.config_path = "task_config.json"
        self.load_config()
        self.result_dir = tk.StringVar(value=os.path.join(os.getcwd(), "results"))
        self.preview_mode_var = tk.BooleanVar(value=False)
        
        plt.rcParams.update({'font.size': 8, 'font.family': 'sans-serif'})
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
            "max_altitude_ft": 3000, "min_altitude_ft": 500
        }

    def _setup_ui(self):
        main_f = ttk.Frame(self.root, padding=10); main_f.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(main_f); left.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(left, text="COMPETITION CONFIG", font=("Arial", 11, "bold")).pack(pady=10)
        self.ent_lat = self._add_input(left, "Start Lat:", self.config['coordinates']['start_point'][0])
        self.ent_lon = self._add_input(left, "Start Lon:", self.config['coordinates']['start_point'][1])
        self.ent_max_alt = self._add_input(left, "Max Limit(ft):", self.config.get("max_altitude_ft", 3000))
        self.ent_min_alt = self._add_input(left, "Min Limit(ft):", self.config.get("min_altitude_ft", 500))
        
        ttk.Button(left, text="Save Config", command=self.update_config).pack(fill=tk.X, pady=10)
        ttk.Checkbutton(left, text="Preview Mode Only", variable=self.preview_mode_var).pack(anchor=tk.W, pady=5)
        
        self.btn_process = tk.Button(left, text="ANALYZE IGC FILES", command=self.process_files, 
                                     bg="#1B5E20", fg="black", font=("Arial", 10, "bold"), pady=12)
        self.btn_process.pack(fill=tk.X, pady=20)
        self.status_label = ttk.Label(left, text="Ready", foreground="blue")
        self.status_label.pack(side=tk.BOTTOM, pady=20)

        right = ttk.LabelFrame(main_f, text=" ANALYSIS VISUALIZER ")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, (self.ax_map, self.ax_alt) = plt.subplots(2, 1, figsize=(7, 9), gridspec_kw={'height_ratios': [2.5, 1]})
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _add_input(self, parent, lbl, val):
        f = ttk.Frame(parent); f.pack(fill=tk.X, pady=3)
        ttk.Label(f, text=lbl, width=12).pack(side=tk.LEFT)
        e = ttk.Entry(f); e.insert(0, val); e.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        return e

    def update_config(self):
        try:
            self.config['coordinates']['start_point'] = [float(self.ent_lat.get()), float(self.ent_lon.get())]
            self.config['coordinates']['finish_point'] = self.config['coordinates']['start_point']
            self.config['max_altitude_ft'] = float(self.ent_max_alt.get())
            self.config['min_altitude_ft'] = float(self.ent_min_alt.get())
            with open(self.config_path, "w", encoding='utf-8') as f: json.dump(self.config, f, indent=4)
            messagebox.showinfo("Success", "Config Updated.")
        except: messagebox.showerror("Error", "Check Values.")

    def process_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("IGC files", "*.igc")])
        if not paths: return
        is_preview = self.preview_mode_var.get(); out_dir = self.result_dir.get()
        if not is_preview: os.makedirs(out_dir, exist_ok=True)
        
        summary_list = []
        for path in paths:
            try:
                pilot, track = IGCParser(path).parse()
                if not track: continue
                self.status_label.config(text=f"Analysing: {pilot}", foreground="green")
                self.root.update_idletasks()
                
                res = RASATScorer(track, self.config).calculate_results()
                
                # --- การคำนวณเพิ่มเติมสำหรับ CSV ---
                alts_ft = [p[2] * 3.28084 for p in track]
                max_alt = max(alts_ft) if alts_ft else 0
                
                total_dist = 0
                for i in range(1, len(track)):
                    total_dist += self.geo.calculate_distance(track[i-1][:2], track[i][:2])
                
                duration_h = res.get('duration_sec', 0) / 3600.0
                avg_speed = total_dist / duration_h if duration_h > 0 else 0
                
                h, r = divmod(res.get('duration_sec', 0), 3600); m, s = divmod(r, 60)
                dur_str = f"{int(h):02}:{int(m):02}:{s:04.1f}"
                
                save_p = os.path.join(out_dir, f"{pilot}_v146.png") if not is_preview else None
                self._draw_plot(track, res, pilot, dur_str, save_p)
                
                summary_list.append({
                    "Pilot": pilot,
                    "Type": "FAI" if res.get('is_fai') else "Flat",
                    "Raw_km": round(res.get('triangle_km', 0), 2),
                    "Multiplier": res.get('multiplier', 1.0),
                    "Effective_km": round(res.get('effective_km', 0), 2),
                    "Duration": dur_str,
                    "Avg_Speed_kmh": round(avg_speed, 1), # --- เพิ่มความเร็วเฉลี่ย ---
                    "Max_Alt_ft": int(max_alt),          # --- เพิ่มความสูงสูงสุด ---
                    "Scored_Gates": res.get('scored_gates', 0),
                    "Total_Gates": res.get('total_gates', 0),
                    "Status": res.get('status_message', 'OK')
                })
            except Exception as e: print(f"Error on {path}: {e}")

        if summary_list and not is_preview:
            summary_list.sort(key=lambda x: x['Effective_km'], reverse=True)
            with open(os.path.join(out_dir, "leaderboard_v146.csv"), 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=summary_list[0].keys()); w.writeheader(); w.writerows(summary_list)
            messagebox.showinfo("Done", "Analysis Complete. Leaderboard Generated!")

    def _draw_plot(self, track, res, pilot, dur, save_p):
        self.ax_map.clear(); self.ax_alt.clear()
        np_track = np.array([p[:2] for p in track]); lats, lons = np_track[:, 0], np_track[:, 1]
        alts_ft = [p[2] * 3.28084 for p in track]; times_min = np.arange(len(track)) / 60.0
        
        self.ax_map.plot(lons, lats, color='blue', alpha=0.3, lw=0.6)
        if res.get('gate_coords'):
            r_km = self.config['scoring_params']['hidden_gate_radius_meters'] / 1000.0
            r_deg_sq = (r_km / 111.0)**2
            for g in res['gate_coords']:
                dist_sq = np.min((lats - g[0])**2 + (lons - g[1])**2)
                color = 'green' if dist_sq <= r_deg_sq else 'red'
                self.ax_map.add_patch(patches.Circle((g[1], g[0]), r_km/111, color=color, alpha=0.2))
                self.ax_map.scatter(g[1], g[0], color=color, s=3)

        if res.get('is_valid'):
            v = list(res['vertices']); v_c = v + [v[0]]; vlats, vlons = zip(*v_c)
            self.ax_map.plot(vlons, vlats, color='darkorange', lw=2, zorder=10)
        
        self.ax_map.set_aspect('equal', adjustable='datalim')
        margin = 0.005
        self.ax_map.set_xlim(min(lons)-margin, max(lons)+margin)
        self.ax_map.set_ylim(min(lats)-margin, max(lats)+margin)

        self.ax_alt.plot(times_min, alts_ft, color='teal', lw=1)
        max_l, min_l = float(self.config.get("max_altitude_ft", 3000)), float(self.config.get("min_altitude_ft", 500))
        self.ax_alt.axhline(max_l, color='red', ls='--', lw=0.8, label=f"Max {int(max_l)}ft")
        self.ax_alt.axhline(min_l, color='orange', ls='--', lw=0.8, label=f"Min {int(min_l)}ft")
        self.ax_alt.set_ylim(0, max(max_l, max(alts_ft)) * 1.1)
        self.ax_alt.set_ylabel("Alt (ft)"); self.ax_alt.legend(loc='upper right', fontsize=6)

        v_msg = ""
        if any(a > max_l for a in alts_ft): v_msg += " [OVER MAX]"
        if any(a < min_l for a in alts_ft): v_msg += " [BELOW MIN]"
        
        title = (f"Pilot: {pilot} | Type: {'FAI' if res.get('is_fai') else 'Flat'}\n"
                 f"Eff: {res['effective_km']}km | Max Alt: {int(max(alts_ft))}ft | Gates: {res['scored_gates']}/{res['total_gates']}{v_msg}")
        self.fig.suptitle(title, fontsize=8, fontweight='bold')
        self.ax_alt.set_xlabel(f"Time (min) | {self.copyright_text}", fontsize=6)
        
        if save_p: self.fig.savefig(save_p, dpi=150, bbox_inches='tight')
        self.canvas.draw_idle()

if __name__ == "__main__":
    root = tk.Tk(); app = RASATGui(root); root.mainloop()