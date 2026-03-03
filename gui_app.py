import os
import json
import csv
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt

# Import ของเราจากโฟลเดอร์ src
from src.igc_parser import IGCParser
from src.scorer import RASATScorer
from src.visualizer import Visualizer

class RASATGui:
    def __init__(self, root):
        self.root = root
        self.root.title("RASAT/FAI Batch Analyzer")
        self.root.geometry("400x250")

        # สร้างโฟลเดอร์ที่จำเป็น
        self.igc_dir = "igcFiles"
        self.result_dir = "results_track_analysis"
        os.makedirs(self.igc_dir, exist_ok=True)
        os.makedirs(self.result_dir, exist_ok=True)

        # โหลดคอนฟิก
        with open("task_config.json", "r") as f:
            self.config = json.load(f)

        # ส่วน GUI
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
            pilot_name = os.path.splitext(filename)[0]
            
            # 1. คัดลอกไฟล์ไปที่ igcFiles
            dest_path = os.path.join(self.igc_dir, filename)
            shutil.copy(path, dest_path)

            try:
                # 2. ประมวลผล
                points = IGCParser(dest_path).parse()
                res = RASATScorer(points, self.config).calculate_results()

                # 3. เซฟรูป Plot (ใช้ฟังก์ชันเดิมแต่เปลี่ยนโหมดเป็น Save)
                self.save_plot(points, res, pilot_name)

                # 4. เก็บข้อมูลลง CSV
                summary_data.append({
                    "Pilot": pilot_name,
                    "Status": res["status_message"],
                    "Triangle_km": res["triangle_km"],
                    "Effective_km": res["effective_km"],
                    "FAI_Type": "FAI" if res["is_fai"] else "Flat",
                    "Multiplier": res["multiplier"],
                    "Gates_Scored": f"{res['scored_gates']}/{res['total_gates']}"
                })
                count += 1
                self.status_label.config(text=f"Processing: {count}/{len(file_paths)}")
                self.root.update()

            except Exception as e:
                print(f"Error processing {filename}: {e}")

        # 5. เขียนไฟล์ CSV
        csv_file = "competition_results.csv"
        keys = summary_data[0].keys() if summary_data else []
        with open(csv_file, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(summary_data)

        messagebox.showinfo("Done", f"Processed {count} files.\nResults saved to '{csv_file}'\nPlots saved to '{self.result_dir}'")
        self.status_label.config(text="Processing Complete", fg="green")

    def save_plot(self, track_points, res, pilot_name):
        """ดัดแปลงจาก Visualizer.plot_task_result เพื่อ Save ลงไฟล์"""
        # ปิดการแสดงผลหน้าต่าง Pop-up ของ Matplotlib
        plt.ioff() 
        
        # เรียกใช้ Logic การวาดจากที่เรามี แต่เปลี่ยน plt.show() เป็น plt.savefig()
        # เพื่อความรวดเร็ว ผมจะเขียนสั้นๆ ตรงนี้ หรือคุณจะย้าย Logic ไปไว้ใน Visualizer ก็ได้
        from src.geo_logic import GeoLogic
        geo = GeoLogic()
        
        fig, ax = plt.subplots(figsize=(12, 9))
        plt.subplots_adjust(bottom=0.15)
        
        lats, lons = zip(*[p[:2] for p in track_points])
        v1, v2, v3 = res['vertices']
        fp = res['finish_point']
        v_lats = [v1[0], v2[0], v3[0], fp[0]]
        v_lons = [v1[1], v2[1], v3[1], fp[1]]

        ax.plot(lons, lats, color='gray', alpha=0.3)
        tri_color = 'green' if res['is_fai'] else 'orange'
        ax.plot(v_lons, v_lats, color=tri_color, linewidth=2)
        
        # ใส่ชื่อนักกีฬาในกราฟ
        ax.text(0.02, 0.95, f"Pilot: {pilot_name}", transform=ax.transAxes, fontsize=12, fontweight='bold')

        # บันทึกไฟล์
        save_path = os.path.join(self.result_dir, f"{pilot_name}_analysis.png")
        plt.savefig(save_path)
        plt.close(fig) # ปิดเพื่อคืนค่า Memory

if __name__ == "__main__":
    root = tk.Tk()
    app = RASATGui(root)
    root.mainloop()