FROM python:3.11-slim

# ติดตั้ง System Dependencies สำหรับ GUI
RUN apt-get update && apt-get install -y \
    python3-tk \
    libtk8.6 \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง uv ใน Docker
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# คัดลอกไฟล์จัดการ Dependency
COPY pyproject.toml uv.lock ./

# ติดตั้ง Dependencies โดยใช้ uv (เร็วและแม่นยำกว่า pip)
RUN uv pip install --system .

# คัดลอก Code ที่เหลือ
COPY . .

CMD ["python", "gui_app.py"]
