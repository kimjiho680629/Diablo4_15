@echo off
chcp 65001 > nul
title 디아블로 IV 통합 매크로 실행기 (Windows 11)

echo ========================================================
echo    ⚔️ 디아블로 IV 통합 매크로 (PyQt6) 실행 준비 중...
echo ========================================================

:: 1. Python 설치 확인
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 환경변수 PATH에 등록되지 않았습니다.
    echo https://www.python.org 에서 Python 3.10 이상을 설치해주세요.
    echo 설치 시 반드시 "Add python.exe to PATH"에 체크해주세요.
    pause
    exit /b 1
)

:: 2. 필수 라이브러리 자동 점검 및 설치
echo [*] 필수 라이브러리(PyQt6, pynput) 점검 중...
python -c "import PyQt6, pynput" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] 필요한 패키지를 자동으로 설치합니다...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [오류] 패키지 설치 실패. 관리자 권한 또는 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
)

:: 3. 관리자 권한 권장 안내 (DirectX 게임 전역 훅 및 SendInput 안정성 보장)
echo [*] 디아블로 IV 통합 매크로를 실행합니다...
python d4_macro_qt.py

if %errorlevel% neq 0 (
    echo.
    echo [알림] 매크로가 종료되었습니다.
    pause
)
