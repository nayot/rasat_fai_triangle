import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class IGCCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("IGC Record Cleaner v1.0")
        self.root.geometry("500x350")
        
        self._setup_ui()

    def _setup_ui(self):
        # ส่วนแสดงคำแนะนำ
        main_f = ttk.Frame(self.root, padding=20)
        main_f.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(main_f, text="IGC File Cleaner", font=("Arial", 14, "bold"))
        label.pack(pady=(0, 10))

        desc = ttk.Label(main_f, text="โปรแกรมนี้จะลบบรรทัด:\n- I-record (I033638...)\n- Date Header (HFDTEDATE...)", 
                         justify=tk.LEFT)
        desc.pack(pady=10)

        # ปุ่มเลือกไฟล์
        self.btn_select = tk.Button(main_f, text="เลือกไฟล์ IGC และเริ่มแก้ไข", 
                                    command=self.process_files,
                                    bg="#0277BD", fg="white", font=("Arial", 10, "bold"),
                                    padx=20, pady=10)
        self.btn_select.pack(pady=20)

        # Progress bar และ Status
        self.progress = ttk.Progressbar(main_f, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress.pack(pady=10)

        self.status_var = tk.StringVar(value="สถานะ: พร้อมทำงาน")
        self.status_lbl = ttk.Label(main_f, textvariable=self.status_var, foreground="blue")
        self.status_lbl.pack()

    def process_files(self):
        # เลือกไฟล์
        file_paths = filedialog.askopenfilenames(
            title="เลือกไฟล์ IGC",
            filetypes=[("IGC files", "*.igc"), ("All files", "*.*")]
        )

        if not file_paths:
            return

        count = 0
        total = len(file_paths)
        self.progress['maximum'] = total

        for path in file_paths:
            try:
                # 1. กำหนด Folder ปลายทาง
                file_dir = os.path.dirname(path)
                target_dir = os.path.join(file_dir, "IGCCorrected")
                
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                file_name = os.path.basename(path)
                target_path = os.path.join(target_dir, file_name)

                # 2. อ่านไฟล์และกรองบรรทัด
                corrected_lines = []
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # เงื่อนไขการ Remove
                        if line.startswith('I'):
                            continue
                        if line.startswith('HFDTEDATE'):
                            continue
                        
                        corrected_lines.append(line)

                # 3. เขียนไฟล์ใหม่
                with open(target_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.writelines(corrected_lines)

                count += 1
                self.progress['value'] = count
                self.status_var.set(f"กำลังแก้ไข: {file_name}")
                self.root.update_idletasks()

            except Exception as e:
                print(f"Error processing {path}: {e}")

        self.status_var.set(f"เสร็จสมบูรณ์! แก้ไขทั้งหมด {count} ไฟล์")
        messagebox.showinfo("Success", f"แก้ไขไฟล์เรียบร้อยแล้ว {count} ไฟล์\nเก็บไว้ที่โฟลเดอร์ IGCCorrected")
        self.progress['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = IGCCleaner(root)
    root.mainloop()