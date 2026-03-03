#!/bin/bash

# ตรวจสอบระบบปฏิบัติการ
OS_TYPE="$(uname)"
echo "--- RASAT/FAI Analyzer Setup for $OS_TYPE ---"

# 1. การจัดการพิกัดหน้าจอ (Display Handling)
if [ "$OS_TYPE" == "Linux" ]; then
    # สำหรับ Linux (Arch/CachyOS/Ubuntu)
    xhost +local:docker > /dev/null 2>&1
    export DISPLAY_VAL=$DISPLAY
    export VOLUMES_EXT="-v /tmp/.X11-unix:/tmp/.X11-unix"
    echo "[+] Linux Display detected: $DISPLAY_VAL"

elif [ "$OS_TYPE" == "Darwin" ]; then
    # สำหรับ Mac
    echo "[+] Configuring XQuartz for Mac..."
    
    # เปิด XQuartz อัตโนมัติ
    open -a XQuartz
    
    # ปลดล็อกสิทธิ์ (ใช้ Full Path เพื่อป้องกัน Command not found)
    /opt/X11/bin/xhost +localhost > /dev/null 2>&1
    /opt/X11/bin/xhost +127.0.0.1 > /dev/null 2>&1
    
    # หา IP ของเครื่อง Mac (en0 คือ Wi-Fi ปกติ)
    IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}' | head -n 1)
    
    # ตั้งค่า DISPLAY ส่งให้ Docker
    export DISPLAY_VAL="$IP:0"
    export VOLUMES_EXT="" # Mac ใช้ Network Socket ไม่ต้องแชร์ไฟล์ระบบ
    echo "[+] Mac Display redirected to: $DISPLAY_VAL"
fi

# 2. เตรียมความพร้อมของโฟลเดอร์
mkdir -p igcFiles results_track_analysis

# 3. รัน Docker Compose โดยส่งตัวแปร Environment เข้าไป
# เราใช้ --build เพื่อให้มั่นใจว่า Code ล่าสุดถูกนำไปใช้
DISPLAY=$DISPLAY_VAL docker compose up --build
