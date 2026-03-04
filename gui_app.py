import os
import json
import csv
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import numpy as np

# Import custom modules
from src.igc_parser import IGCParser
from src.scorer import RASATScorer

class RASATGui:
    def __init__(self, root):
        self.root = root
        self.root.title("RASAT/FAI Stand-alone Analyzer v1.1")
        self.root.geometry("1200x850") 
        
        self.config_path = "task_config.json"
        self.load_config()
        
        self.result_dir = tk.StringVar(value=os.path.abspath("results_track_analysis"))
        self.preview_mode_var = tk.BooleanVar(value=False) 
        
        self._setup_ui()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self._set_default_config()
        else:
            self._set_default_config()

    def _set_default_config(self):
        self.config = {
            "task_name": "New Task",
            "coordinates": {
                "start_point": [14.422020, 100.499577],
                "finish_point": [14.422020, 100.499577],
                "sp_radius_meters": 200,
                "fp_radius_meters": 200
            },
            "scoring_params": {
                "hidden_gate_interval_km": 1.0,
                "hidden_gate_radius_meters": 200,
                "fai_multiplier": 1.5,
                "flat_multiplier": 1.0
            }
        }

    def _setup_ui(self):
        # Header Section
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=15, pady=10)
        ttk.Label(header_frame, text="RASAT/FAI Triangle Analyzer", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="v1.1", font=("Arial", 10, "italic"), foreground="gray").pack(side=tk.LEFT, padx=10, pady=5)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- ฝั่งซ้าย: Control Panel (50%) ---
        left_frame = ttk.Frame(paned, padding=15)
        paned.add(left_frame, weight=1)

        # Config Editor
        conf_frame = ttk.LabelFrame(left_frame, text=" Task Configuration ", padding=10)
        conf_frame.pack(fill=tk.X, pady=5)

        ttk.Label(conf_frame, text="Task Name:").grid(row=0, column=0, sticky=tk.W)
        self.ent_task_name = ttk.Entry(conf_frame, width=25)
        self.ent_task_name.insert(0, self.config['task_name'])
        self.ent_task_name.grid(row=0, column=1, columnspan=2, pady=2)

        ttk.Label(conf_frame, text="Start Lat:").grid(row=1, column=0, sticky=tk.W)
        self.ent_sp_lat = ttk.Entry(conf_frame, width=15)
        self.ent_sp_lat.insert(0, self.config['coordinates']['start_point'][0])
        self.ent_sp_lat.grid(row=1, column=1, pady=2)

        ttk.Label(conf_frame, text="Start Lon:").grid(row=2, column=0, sticky=tk.W)
        self.ent_sp_lon = ttk.Entry(conf_frame, width=15)
        self.ent_sp_lon.insert(0, self.config['coordinates']['start_point'][1])
        self.ent_sp_lon.grid(row=2, column=1, pady=2)

        ttk.Label(conf_frame, text="Radius (m):").grid(row=3, column=0, sticky=tk.W)
        self.ent_sp_r = ttk.Entry(conf_frame, width=15)
        self.ent_sp_r.insert(0, self.config['coordinates']['sp_radius_meters'])
        self.ent_sp_r.grid(row=3, column=1, pady=2)

        ttk.Button(conf_frame, text="Save & Update Config", command=self.update_config_from_ui).grid(row=4, column=0, columnspan=3, pady=10)

        # Settings
        settings_frame = ttk.LabelFrame(left_frame, text=" Execution Settings ", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        self.chk_preview = ttk.Checkbutton(settings_frame, text="Preview Mode (No Files Saved)", variable=self.preview_mode_var)
        self.chk_preview.pack(anchor=tk.W, pady=5)

        ttk.Label(settings_frame, text="Output Folder:").pack(anchor=tk.W)
        path_sub = ttk.Frame(settings_frame)
        path_sub.pack(fill=tk.X)
        ttk.Entry(path_sub, textvariable=self.result_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_sub, text="...", width=3, command=self.browse_folder).pack(side=tk.LEFT)

        # Main Button (Black Text)
        self.btn_process = tk.Button(left_frame, text="SELECT IGC & START ANALYSIS", 
                                     command=self.process_files, 
                                     bg="#4CAF50", fg="black", 
                                     font=("Arial", 12, "bold"), height=3)
        self.btn_process.pack(fill=tk.X, pady=20)
        
        self.status_label = ttk.Label(left_frame, text="Status: Ready", foreground="blue")
        self.status_label.pack(pady=5)

        # --- ฝั่งขวา: Visual Analysis (50%) ---
        right_frame = ttk.LabelFrame(paned, text=" Visual Analysis ", padding=5)
        paned.add(right_frame, weight=1)

        # Font Scale Reduction
        plt.rcParams.update({'font.size': 5.5, 'axes.labelsize': 6, 'axes.titlesize': 7})
        
        self.fig, self.ax = plt.subplots(figsize=(6, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.result_dir.set(os.path.abspath(folder))

    def update_config_from_ui(self):
        try:
            self.config['task_name'] = self.ent_task_name.get()
            lat, lon = float(self.ent_sp_lat.get()), float(self.ent_sp_lon.get())
            self.config['coordinates']['start_point'] = [lat, lon]
            self.config['coordinates']['finish_point'] = [lat, lon]
            self.config['coordinates']['sp_radius_meters'] = int(self.ent_sp_r.get())
            self.config['coordinates']['fp_radius_meters'] = int(self.ent_sp_r.get())
            
            with open(self.config_path, "w", encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")

    def process_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("IGC files", "*.igc")])
        if not file_paths: return

        is_preview = self.preview_mode_var.get()
        if not is_preview:
            os.makedirs(self.result_dir.get(), exist_ok=True)
            
        summary_data = []
        
        for i, path in enumerate(file_paths):
            try:
                parser = IGCParser(path)
                parsed_data = parser.parse()
                track = parsed_data[1] if isinstance(parsed_data, tuple) else parsed_data
                pilot_name = parsed_data[0] if isinstance(parsed_data, tuple) else os.path.basename(path)

                res = RASATScorer(track, self.config).calculate_results()
                
                save_path = os.path.join(self.result_dir.get(), f"{pilot_name}_analysis.png") if not is_preview else None
                self._draw_plot(track, res, pilot_name, save_path)

                summary_data.append({
                    "Pilot": pilot_name, "Status": res["status_message"],
                    "Triangle_km": res["triangle_km"], "Effective_km": res["effective_km"],
                    "Type": "FAI" if res["is_fai"] else "Flat", 
                    "Scored_Gates": res['scored_gates'],
                    "Total_Gates": res['total_gates']
                })
                
                self.status_label.config(text=f"Processed: {i+1}/{len(file_paths)}")
                self.root.update()

            except Exception as e:
                print(f"Error processing {path}: {e}")

        if summary_data and not is_preview:
            csv_path = os.path.join(self.result_dir.get(), "competition_results.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=summary_data[0].keys())
                writer.writeheader()
                writer.writerows(summary_data)
            messagebox.showinfo("Done", f"Results saved in:\n{csv_path}")
        elif summary_data:
            messagebox.showinfo("Done", "Analysis Complete (Preview Mode)")

    def _draw_plot(self, track_points, res, pilot, save_to_file=None):
        self.ax.clear()
        f_size = 5.5 
        
        # Axis Decimals
        self.ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        self.ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        self.ax.tick_params(axis='both', labelsize=f_size)
        
        # Track (Dark Blue)
        lats, lons = zip(*[p[:2] for p in track_points])
        self.ax.plot(lons, lats, color='darkblue', alpha=0.6, linewidth=0.7, zorder=1)

        # Radius Calculations
        deg_m = 1.0 / 111000.0
        sp = self.config['coordinates']['start_point']
        fp = self.config['coordinates']['finish_point']
        sp_r = self.config['coordinates']['sp_radius_meters'] * deg_m
        fp_r = self.config['coordinates']['fp_radius_meters'] * deg_m
        gate_r = self.config['scoring_params']['hidden_gate_radius_meters'] * deg_m

        # Start/Finish Cylinders
        self.ax.add_patch(patches.Circle((sp[1], sp[0]), sp_r, color='green', fill=True, alpha=0.1, zorder=2))
        self.ax.add_patch(patches.Circle((sp[1], sp[0]), sp_r, color='green', fill=False, linestyle='--', linewidth=1, zorder=3))
        self.ax.plot(sp[1], sp[0], 'go', markersize=4)

        self.ax.add_patch(patches.Circle((fp[1], fp[0]), fp_r, color='blue', fill=True, alpha=0.1, zorder=2))
        self.ax.add_patch(patches.Circle((fp[1], fp[0]), fp_r, color='blue', fill=False, linestyle='--', linewidth=1, zorder=3))
        self.ax.plot(fp[1], fp[0], 'bo', markersize=4)

        # Hidden Gates - Color Coded
        if 'gate_coords' in res:
            track_np = np.array([p[:2] for p in track_points])
            for g in res['gate_coords']:
                dist = np.sqrt(np.sum((track_np - np.array(g))**2, axis=1))
                is_passed = np.any(dist <= gate_r)
                c = 'limegreen' if is_passed else 'red'
                self.ax.add_patch(patches.Circle((g[1], g[0]), gate_r, color=c, fill=False, alpha=0.4, linewidth=0.6, zorder=4))
                self.ax.plot(g[1], g[0], '.', color=c, markersize=1, zorder=5)

        # Triangle
        if res['is_valid']:
            v = res['vertices']
            v_lats = [v[0][0], v[1][0], v[2][0], fp[0]]
            v_lons = [v[0][1], v[1][1], v[2][1], fp[1]]
            self.ax.plot(v_lons, v_lats, color='darkorange', linewidth=1.5, marker='^', markersize=3, zorder=10)

        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle=':', alpha=0.5)

        # Summary Info
        summary_text = (
            f"Pilot: {pilot} | Status: {res['status_message']} | Type: {'FAI' if res['is_fai'] else 'Flat'}\n"
            f"Triangle Distance: {res['triangle_km']:.2f} km | Multiplier: x{res['multiplier']}\n"
            f"Effective Distance: {res['effective_km']:.2f} km | Gates Scored: {res['scored_gates']} / {res['total_gates']}"
        )

        if not save_to_file:
            self.ax.set_title(f"Preview: {pilot}", fontsize=f_size + 2)
            self.ax.text(0.5, -0.15, summary_text, ha='center', transform=self.ax.transAxes, 
                         fontsize=f_size, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            self.fig.tight_layout()
            self.canvas.draw()
        else:
            # Special formatting for saved files
            self.fig.subplots_adjust(bottom=0.22)
            self.ax.set_title(f"RASAT Analysis - {pilot}", fontsize=f_size + 3)
            self.fig.text(0.5, 0.06, summary_text, ha='center', fontsize=f_size + 1, fontweight='bold',
                         bbox=dict(boxstyle='round', facecolor='whitesmoke', edgecolor='gray'), fontfamily='monospace')
            self.fig.savefig(save_to_file, dpi=200, bbox_inches='tight')
            # Reset layout after save to prevent UI distortion
            self.fig.subplots_adjust(bottom=0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = RASATGui(root)
    root.mainloop()