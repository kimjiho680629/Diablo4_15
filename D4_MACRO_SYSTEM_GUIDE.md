# ⚔️ 디아블로 4 크로스플랫폼 스킬 자동 연타 & 마우스 매크로 시스템 사용자 가이드

이 문서는 리눅스(Hyprland / Wayland / X11) 및 윈도우 11/10 환경에서 디아블로 4를 플레이할 때 로지텍 G-HUB의 토글/홀드 매크로를 완벽히 대체하고 능가할 수 있도록 제작된 **PyQt6 기반 고성능 통합 매크로 시스템**의 사용법 및 구성 안내서입니다.

---

## 1. 파일 구성 및 역할

| 파일명 | 절대 경로 | 역할 및 상세 설명 |
| :--- | :--- | :--- |
| **`diablo4-macro-qt`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/diablo4-macro-qt`](file:///mnt/Data1/Gemini_Job/Diablo4_15/diablo4-macro-qt) | **최신 PyQt6 독립 실행 바이너리 (ELF)**. 환경 의존성 없이 리눅스에서 즉시 단독 실행 가능 |
| **`d4_macro_qt.py`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/d4_macro_qt.py`](file:///mnt/Data1/Gemini_Job/Diablo4_15/d4_macro_qt.py) | PyQt6 크로스플랫폼 GUI 메인 소스코드 (다크 테마, Anti-Bloat 가드, Win32 SendInput 연동) |
| **`run_qt.sh`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/run_qt.sh`](file:///mnt/Data1/Gemini_Job/Diablo4_15/run_qt.sh) | 리눅스에서 PyQt6 매크로를 원클릭 실행해 주는 스크립트 |
| **`run_windows.bat`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/run_windows.bat`](file:///mnt/Data1/Gemini_Job/Diablo4_15/run_windows.bat) | 윈도우 11 환경에서 더블클릭 한 번으로 의존성 점검 후 즉시 실행하는 배치 파일 |
| **`build_windows.bat`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/build_windows.bat`](file:///mnt/Data1/Gemini_Job/Diablo4_15/build_windows.bat) | 윈도우 11 환경에서 단일 실행 파일(`dist\Diablo4_Macro.exe`)을 원클릭 빌드하는 스크립트 |
| **`config.json`** | [`/mnt/Data1/Gemini_Job/Diablo4_15/config.json`](file:///mnt/Data1/Gemini_Job/Diablo4_15/config.json) | 사용자가 GUI에서 설정한 단축키, 연타 스킬 목록, 지연시간이 영구 저장되는 설정 파일 |
| **`diablo4-macro-qt.desktop`**| `~/.local/share/applications/diablo4-macro-qt.desktop` | Rofi, Wofi, Walker 등 리눅스 데스크탑 앱 런처 등록 파일 |

---

## 2. 3대 핵심 매크로 기능 및 단축키

### 1. ⚡ 스킬 자동 순차 연타 (1~5번)
* **기본 단축키**: `F4` (또는 마우스 사이드 버튼 연동 가능)
* **모드 선택**:
  * **토글 모드 (Toggle)**: 1번 누르면 연타 시작, 다시 누르면 1.3ms 이내 칼정지.
  * **홀드 모드 (Hold)**: 누르고 있는 동안만 연타 작동, 손을 떼는 즉시 중단.
* **원클릭 속도 프리셋**:
  * ⚡ **초광속 (1ms)**: `누름 1ms / 간격 1ms / 대기 1ms`
  * 🚀 **고속 (15ms)**: `누름 15ms / 간격 20ms / 대기 30ms`
  * 🎯 **권장 표준 (35ms)**: `누름 30ms / 간격 40ms / 대기 80ms` (키 씹힘 방지 최적치)
  * 🛡️ **버프 유지 (80ms)**: `누름 50ms / 간격 80ms / 대기 150ms`

### 2. 🔵 매크로 1 (기본: Ctrl + 우클릭 초고속 연타 / 대화 F키)
* **기본 단축키**: 마우스 사이드 뒤로가기 버튼(`BTN_SIDE`) 또는 `F1` 키
* **용도**: 상인 물품 일괄 구매, 겜블 일괄 교환, 또는 `F`키로 설정하여 NPC 대화 넘기기 초고속 연타.

### 3. 🔴 매크로 2 (기본: Ctrl + 좌클릭 아이템 일괄 버리기)
* **기본 단축키**: 마우스 사이드 앞으로가기 버튼(`BTN_EXTRA`) 또는 `F2` 키
* **용도**: 인벤토리 정리가 필요할 때 버튼을 누른 채 마우스 커서만 훑으면 아이템들이 바닥으로 즉시 연속 드롭됩니다.

### 4. 🛑 비상 정지 (F12)
* 예기치 않은 상황이나 긴급 상황 시 `F12`를 누르면 즉시 모든 매크로가 강제 차단되고 Ctrl 및 모든 키가 릴리스됩니다.

---

## 3. 실행 방법

### A. 리눅스 환경
1. **프로그램 런처 검색 실행 (가장 추천)**:
   * Rofi, Wofi, Walker 등에서 `디아` 또는 `diablo` 검색 후 **`디아블로 IV 통합 매크로 (Qt)`** 클릭.
2. **원클릭 실행 스크립트**:
   ```bash
   /mnt/Data1/Gemini_Job/Diablo4_15/run_qt.sh
   ```
3. **독립 실행 바이너리 직접 실행**:
   ```bash
   /mnt/Data1/Gemini_Job/Diablo4_15/diablo4-macro-qt
   ```

### B. 윈도우 11 환경
1. 저장소 폴더에서 [`run_windows.bat`](file:///mnt/Data1/Gemini_Job/Diablo4_15/run_windows.bat) 더블클릭 (파이썬 환경)
2. 또는 [`build_windows.bat`](file:///mnt/Data1/Gemini_Job/Diablo4_15/build_windows.bat) 더블클릭으로 생성된 `dist\Diablo4_Macro.exe` 실행
