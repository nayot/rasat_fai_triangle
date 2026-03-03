import os
import json
import csv
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Import จากโฟลเดอร์ src
from src.igc_parser import IGCParser
from src.scorer import RASATScorer

class RASATGui:
    def __init__(self, root):
        self.root = root
        self.root.title("RASAT/FAI Batch Analyzer")
        self.root.geometry("400x250")

        # 1. เตรียมโครงสร้างโฟลเดอร์
        self.igc_dir = "igcFiles"
        self.result_dir = "results_track_analysis"
        os.makedirs(self.igc_dir, exist_ok=True)
        os.makedirs(self.result_dir, exist_ok=True)

        # 2. โหลด Config
        try:
            with open("task_config.json", "r") as f:
                self.config = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load task_config.json: {e}")

        # 3. ส่วนประกอบ GUI
        tk.Label(root, text="RASAT Competition Scoring System", font=("Arial", 14, "bold")).pack(pady=20)
        
        self.btn_upload = tk.Button(root, text="Select IGC Files & Process", 
                                    command=self.process_files, 
                                    width=30, height=2, bg="#4CAF50", fg="white")
        self.btn_upload.pack(pady=10)

        self.status_label = tk.Label(root, text="Ready", fg="blue")
        self.status_label.pack(pady=10)

    def process_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("IGC files", "*.igc")])
        if not file_paths:
            return

        summary_data = []
        count = 0

        for path in file_paths:
            filename = os.path.basename(path)
            dest_path = os.path.join(self.igc_dir, filename)
            shutil.copy(path, dest_path)

            try:
                # วิเคราะห์ไฟล์
                parser = IGCParser(dest_path)
                # ตรวจสอบว่า parser ของคุณส่งคืนค่ากี่ตัว (ป้องกัน unpacking error)
                parsed_data = parser.parse()
                if isinstance(parsed_data, tuple):
                    pilot_name_igc, track = parsed_data
                else:
                    track = parsed_data
                    pilot_name_igc = os.path.splitext(filename)[0]

                # คำนวณคะแนน
                scorer = RASATScorer(track, self.config)
                res = scorer.calculate_results()

                # บันทึกรูปกราฟแบบละเอียด
                self.save_plot(track, res, pilot_name_igc)

                # เก็บข้อมูลลงรายการสรุป
                summary_data.append({
                    "Pilot": pilot_name_igc,
                    "Status": res["status_message"],
                    "Triangle_km": res["triangle_km"],
                    "Effective_km": res["effective_km"],
                    "Type": "FAI" if res["is_fai"] else "Flat",
                    "Multiplier": res["multiplier"],
                    "Gates_Scored": res["scored_gates"],
                    "Gates_Total": res["total_gates"]
                })
                
                count += 1
                self.status_label.config(text=f"Processing: {count}/{len(file_paths)}")
                self.root.update()

            except Exception as e:
                print(f"Error processing {filename}: {e}")

        # บันทึกไฟล์ CSV
        if summary_data:
            csv_file = "competition_results.csv"
            keys = summary_data[0].keys()
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(summary_data)

            messagebox.showinfo("Done", f"Processed {count} files.\nResults saved to '{csv_file}'\nPlots saved to '{self.result_dir}'")
            self.status_label.config(text="Processing Complete", fg="green")
    def save_plot(self, track_points, res, pilot_name):
        """
        วาดกราฟแสดงผล:
        - Hidden Gates ที่เก็บได้ = สีเขียว
        - Hidden Gates ที่พลาดไป = สีแดง
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        import numpy as np
        import os

        plt.ioff()
        fig, ax = plt.subplots(figsize=(12, 10))
        plt.subplots_adjust(bottom=0.22)

        # ตั้งค่าพิกัด Decimal
        ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.4f'))
        
        # 1. วาดเส้นทางบิน (Track)
        lats, lons = zip(*[p[:2] for p in track_points])
        ax.plot(lons, lats, color='gray', alpha=0.3, label='Full Flight Path', zorder=1)

        # 2. คำนวณรัศมี
        deg_per_m = 1.0 / 111000.0
        sp_r = self.config['coordinates']['sp_radius_meters'] * deg_per_m
        fp_r = self.config['coordinates']['fp_radius_meters'] * deg_per_m
        gate_r = self.config['scoring_params']['hidden_gate_radius_meters'] * deg_per_m

        # 3. วาด Start/Finish Cylinders
        sp = self.config['coordinates']['start_point']
        fp = self.config['coordinates']['finish_point']
        ax.add_patch(patches.Circle((sp[1], sp[0]), sp_r, color='green', fill=True, alpha=0.1, zorder=2))
        ax.add_patch(patches.Circle((sp[1], sp[0]), sp_r, color='green', fill=False, linestyle='--', linewidth=2, zorder=3))
        ax.plot(sp[1], sp[0], 'go', markersize=8, label='START (SP)')

        ax.add_patch(patches.Circle((fp[1], fp[0]), fp_r, color='blue', fill=True, alpha=0.1, zorder=2))
        ax.add_patch(patches.Circle((fp[1], fp[0]), fp_r, color='blue', fill=False, linestyle='--', linewidth=2, zorder=3))
        ax.plot(fp[1], fp[0], 'bo', markersize=8, label='FINISH (FP)')

        # 4. วาด Hidden Gates แยกสี (เขียว = ผ่าน, แดง = ไม่ผ่าน)
        if 'gate_coords' in res and res['gate_coords']:
            # ดึง Track พิกัด (Lat, Lon) มาใช้ในการเช็คระยะ
            track_np = np.array([p[:2] for p in track_points])
            
            for g_pos in res['gate_coords']:
                # เช็คว่า Gate นี้ Scored หรือไม่ (ตรวจสอบระยะทางจากทุกลำดับของ track)
                # เราใช้ Logic เดียวกับใน Scorer เพื่อความแม่นยำในกราฟ
                dists = np.sqrt(np.sum((track_np - np.array(g_pos))**2, axis=1))
                is_passed = np.any(dists <= gate_r)
                
                gate_color = 'limegreen' if is_passed else 'red'
                gate_label = 'Gate Scored' if is_passed else 'Gate Missed'
                
                # วาดวงกลมรัศมี Gate
                ax.add_patch(patches.Circle((g_pos[1], g_pos[0]), gate_r, color=gate_color, 
                                            fill=False, alpha=0.5, linewidth=1.2, zorder=4))
                # วาดจุด x ตำแหน่ง Gate
                ax.plot(g_pos[1], g_pos[0], marker='x', color=gate_color, markersize=5, zorder=5)

            # เพิ่ม Legend เฉพาะสีของ Gates (วาดจุดหลอกเพื่อทำ Legend)
            ax.plot([], [], 'x', color='limegreen', label='Gate Scored')
            ax.plot([], [], 'x', color='red', label='Gate Missed')

        # 5. วาด Triangle
        if res['is_valid']:
            v = res['vertices']
            v_lats = [v[0][0], v[1][0], v[2][0], fp[0]]
            v_lons = [v[0][1], v[1][1], v[2][1], fp[1]]
            tri_color = 'limegreen' if res['is_fai'] else 'darkorange'
            ax.plot(v_lons, v_lats, color=tri_color, linewidth=2.5, marker='^', label='Scored Triangle', zorder=6)

        # 6. ตั้งค่ากราฟ
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(loc='upper right', fontsize='small')
        ax.set_title(f"FAI Triangle Task Analysis - {pilot_name}", pad=20, fontsize=14, fontweight='bold')

        # 7. Summary Box ด้านล่าง
        summary_text = (
            f"Pilot: {pilot_name} | Status: {res['status_message']} | Type: {'FAI' if res['is_fai'] else 'Flat'}\n"
            f"Triangle Dist: {res['triangle_km']:.2f} km | Multiplier: x{res['multiplier']} | Effective Dist: {res['effective_km']:.2f} km\n"
            f"Hidden Gates Scored: {res['scored_gates']} / {res['total_gates']}"
        )
        fig.text(0.5, 0.08, summary_text, ha='center', fontsize=11, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='whitesmoke', alpha=1.0, edgecolor='gray'), 
                 fontfamily='monospace')

        # 8. บันทึก
        save_path = os.path.join(self.result_dir, f"{pilot_name}_analysis.png")
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

if __name__ == "__main__":
    root = tk.Tk()
    app = RASATGui(root)
    root.mainloop()