# ใช้ Python image ที่มีขนาดเล็กและเสถียร
FROM python:3.11-slim

# ติดตั้ง dependencies สำหรับ GUI (Tkinter) และ OpenGL สำหรับ Matplotlib
RUN apt-get update && apt-get install -y \
    python3-tk \
    libtk8.6 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# กำหนด working directory ใน container
WORKDIR /app

# คัดลอกไฟล์จัดการ dependencies (จากโปรเจค uv ของคุณ)
COPY pyproject.toml .
# หากมี uv.lock ให้ปลดคอมเมนต์บรรทัดล่าง
COPY uv.lock .

# ติดตั้ง Library ที่จำเป็น
RUN pip install --no-cache-dir .

# คัดลอกไฟล์ทั้งหมดในโปรเจคเข้าไป
COPY . .

# สั่งรัน GUI เป็นค่าเริ่มต้น
CMD ["python", "gui_app.py"]
