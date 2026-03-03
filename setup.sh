#!/bin/bash

# ตรวจสอบระบบปฏิบัติการ
OS_TYPE="$(uname)"

echo "--- RASAT/FAI Analyzer Setup for $OS_TYPE ---"

# 1. จัดการเรื่อง Display ตาม OS
if [ "$OS_TYPE" == "Linux" ]; then
    # สำหรับ Linux (Arch/CachyOS/Ubuntu)
    if command -v xhost > /dev/null; then
        xhost +local:docker
    else
        echo "Warning: xhost not found. Please install it using 'sudo pacman -S xorg-xhost'"
    fi
    export DISPLAY_VAL=$DISPLAY
    export DOCKER_VOLUMES="-v /tmp/.X11-unix:/tmp/.X11-unix"

elif [ "$OS_TYPE" == "Darwin" ]; then
    # สำหรับ Mac
    echo "Checking XQuartz..."
    xhost + 127.0.0.1 > /dev/null 2>&1
    xhost + localhost > /dev/null 2>&1
    
    # ดึง IP ของเครื่อง Mac เพื่อส่งให้ Docker
    IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
    export DISPLAY_VAL="$IP:0"
    export DOCKER_VOLUMES="" # Mac ใช้ Network Socket ไม่ต้อง Mount Volume
    
    echo "Make sure XQuartz is running with 'Allow connections from network clients' enabled."
fi

# 2. สร้างโฟลเดอร์ผลลัพธ์และล้างข้อมูลเก่า (Optional)
mkdir -p igcFiles results_track_analysis
# rm -f results_track_analysis/*.png  # ปลดคอมเมนต์ถ้าต้องการล้างรูปเก่าทุกครั้ง

# 3. รัน Docker Compose โดยส่งค่า Environment ไปให้
DISPLAY=$DISPLAY_VAL docker compose up --build
