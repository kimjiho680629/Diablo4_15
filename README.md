# ⚔️ 디아블로 IV 크로스플랫폼 통합 매크로 (Linux & Windows 11)

리눅스(Arch Linux, Hyprland, Wayland, Proton/Wine)와 **윈도우 11 / 10** 양쪽 환경 모두에서 완벽하게 동작하는 **PyQt6 기반 모던 통합 게이밍 매크로**입니다.

DirectX 12 기반 디아블로 IV 게임 내에서 입력이 씹히거나 지연되는 현상을 원천 방지하기 위해 **하드웨어 스캔코드 주입(Win32 SendInput / evdev)** 및 **적응형 큐 누적 방지 가드 (Anti-Bloat Guard)**가 탑재되어 있습니다.

---

## ✨ 핵심 기능

1. **⚡ 스킬 자동 순차 연타 (1~5번)**:
   * 지정된 단축키(`F4`) 또는 마우스 트리거를 누르면 1, 2, 3, 4, 5 스킬을 무한 고속 연타합니다.
   * **토글 모드 (Toggle)**: 1번 누르면 켜지고, 다시 누르면 칼정지.
   * **홀드 모드 (Hold)**: 누르고 있는 동안만 연타.
   * **속도 프리셋 원클릭 지원**: 초광속(1ms), 고속(15ms), 표준 권장(35ms), 여유 버프(80ms).
   * **적응형 큐 누적 방지 (Anti-Bloat Guard)**: 60Hz 게임 틱레이트 동기화로 큐 적체율 0% 및 즉각 중단(0.5ms 이내).

2. **🔵 매크로 1 (기본: Ctrl + 우클릭 연타 / F키 연타)**:
   * 마우스 사이드 뒤로가기 버튼(`BTN_SIDE`) 또는 `F1` 키로 발동.
   * 버스트(지정 횟수 연타), 홀드, 토글 지원.

3. **🔴 매크로 2 (기본: Ctrl + 좌클릭 아이템 버리기)**:
   * 마우스 사이드 앞으로가기 버튼(`BTN_EXTRA`) 또는 `F2` 키로 발동.
   * 인벤토리에서 버튼을 누른 채로 마우스를 훑으면 아이템들이 즉시 바닥으로 일괄 드롭됩니다.

4. **🛑 긴급 중지 (F12)**:
   * 위급 상황 시 `F12`를 누르면 즉시 모든 매크로와 Ctrl 키가 릴리스되며 완전 정지됩니다.

5. **실시간 설정 동기화 및 입력 테스트**:
   * 단축키 입력창을 수정하는 즉시 실시간으로 키가 반영되며, 하단 입력 테스트 창에서 포커스 후 즉각 확인 가능.

---

## 🚀 윈도우 11 (Windows 11) 사용 방법

### 1. 원클릭 실행 (Python 설치 환경)
```cmd
run_windows.bat
```
* 더블클릭 시 필요한 패키지(`PyQt6`, `pynput`)를 자동으로 확인 및 설치한 후 매크로를 실행합니다.

### 2. 단일 실행 파일 (.exe) 빌드
```cmd
build_windows.bat
```
* 더블클릭 한 번으로 `dist\Diablo4_Macro.exe` 단독 실행 파일이 생성됩니다.
* 생성된 `.exe` 파일은 파이썬이 없는 다른 PC에서도 더블클릭만으로 즉시 구동됩니다.
* *(게임 내 원활한 키 주입을 위해 '관리자 권한으로 실행'을 권장합니다.)*

---

## 🐧 리눅스 (Linux / Wayland / X11) 사용 방법

### 1. PyQt6 신규 통합 매크로 실행
```bash
./run_qt.sh
# 또는 독립 바이너리 직접 실행
./diablo4-macro-qt
```

### 2. 애플리케이션 런처 (.desktop) 실행
* 리눅스 데스크탑 환경의 프로그램 런처(Rofi, Wofi, Walker, GNOME/KDE 메뉴 등)에서 **"디아블로 IV 통합 매크로 (Qt)"** 또는 **"Diablo IV Macro (Qt)"**를 검색하여 클릭 한 번으로 실행할 수 있습니다.
* 런처 파일: `~/.local/share/applications/diablo4-macro-qt.desktop`

### 3. 기존 GTK4 매크로 실행 (유지됨)
```bash
./run.sh
# 또는
./diablo4-macro
```

---

## 🛠️ 기술 아키텍처 (크로스플랫폼 설계)

| 구성 요소 | Linux (Wayland / X11) | Windows 11 / 10 |
| :--- | :--- | :--- |
| **GUI 프레임워크** | PyQt6 (모던 다크 테마) | PyQt6 (윈도우 네이티브 렌더링) |
| **전역 입력 감지** | `evdev` (/dev/input/event* 커널) + `pynput` | Windows Low-Level Hook (`WH_KEYBOARD_LL`, `WH_MOUSE_LL`) |
| **게임 내 입력 주입** | `pynput` + `wtype` (Wayland 지원) | **Win32 `SendInput` (DirectX 12 하드웨어 스캔코드)** |
| **대기열 관리** | Anti-Bloat Guard (대기열 적체율 0%) | Anti-Bloat Guard (대기열 적체율 0%) |
| **설정 파일** | `config.json` 100% 호환 | `config.json` 100% 호환 |
