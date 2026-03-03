#!/bin/bash
echo "--- RASAT/FAI Analyzer Setup for Linux/Mac ---"

# 1. จัดการสิทธิ์ X11 สำหรับ GUI
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xhost +local:docker
elif [[ "$OSTYPE" == "darwin"* ]]; then
    xhost + localhost
fi

# 2. ตรวจสอบและสร้างโฟลเดอร์ที่จำเป็น
mkdir -p igcFiles results_track_analysis

# 3. รัน Docker
echo "Starting Docker Container..."
docker-compose up --build