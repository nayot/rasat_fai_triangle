@echo off
echo --- RASAT/FAI Analyzer Setup for Windows ---

:: 1. ตรวจสอบโฟลเดอร์
if not exist "igcFiles" mkdir igcFiles
if not exist "results_track_analysis" mkdir results_track_analysis

:: 2. คำเตือนเรื่อง X Server
echo IMPORTANT: Make sure VcXsrv (XLaunch) is running with "Disable access control" checked!
pause

:: 3. รัน Docker
docker-compose up --build
pause