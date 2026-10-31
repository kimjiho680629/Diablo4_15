@echo off
chcp 65001 > nul
title 디아블로 IV 통합 매크로 윈도우용 EXE 빌더

echo ========================================================
echo    ⚔️ 디아블로 IV 통합 매크로 (.exe) 원클릭 빌더
echo ========================================================

:: 1. Python 설치 확인
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다. Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

:: 2. 빌드 필수 패키지 설치
echo [*] 빌드 패키지 점검 및 설치 중...
python -m pip install --upgrade pip
python -m pip install PyQt6 pynput pyinstaller

:: 3. 기존 빌드 캐시 정리
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 4. PyInstaller를 통한 단일 실행 파일(.exe) 빌드
echo.
echo [*] Diablo4_Macro.exe 빌드 시작 (콘솔 숨김, 단일 파일 모드)...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "Diablo4_Macro" ^
    --add-data "config.json;." ^
    d4_macro_qt.py

if %errorlevel% neq 0 (
    echo.
    echo [오류] EXE 빌드에 실패했습니다. 로그를 확인해주세요.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [성공] dist\Diablo4_Macro.exe 생성이 완료되었습니다!
echo 해당 파일을 원하는 폴더로 복사하여 게임 실행 중 실행하시면 됩니다.
echo (주의: 게임 내 원활한 키 주입을 위해 '관리자 권한으로 실행'을 권장합니다.)
echo ========================================================
pause
