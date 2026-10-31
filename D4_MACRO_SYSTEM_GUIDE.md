# 디아블로 4 리눅스 스킬 자동 연타 매크로 시스템 문서

이 문서는 리눅스(Hyprland / Wayland / X11) 환경에서 디아블로 4를 플레이할 때 로지텍 G-HUB의 전환(Toggle) 매크로를 대체할 수 있도록 제작된 전용 매크로 시스템의 전체 구성 및 인계 사항을 정리한 문서입니다.

---

## 1. 파일 구성 및 역할

| 파일명 | 절대 경로 | 역할 및 상세 설명 |
| :--- | :--- | :--- |
| **`d4_macro`** | `/mnt/Data1/Gemini_Job/Diablo4_15/d4_macro` | **최종 독립 실행 바이너리 (ELF)**. 파이썬 설치나 환경 의존성 없이 즉시 단독 실행 가능 |
| **`d4_macro.py`** | `/mnt/Data1/Gemini_Job/Diablo4_15/d4_macro.py` | 매크로 핵심 소스코드 (대화형 커스텀 메뉴, 1ms 초광속 지연시간, pynput 백그라운드 스레드, notify-send 연동) |
| **`config.json`** | `/mnt/Data1/Gemini_Job/Diablo4_15/config.json` | 사용자가 지정한 단축키, 연타 스킬 목록, 지연시간이 영구 저장되는 설정 파일 |
| **`run.sh`** | `/mnt/Data1/Gemini_Job/Diablo4_15/run.sh` | Kitty 터미널 창을 팝업하여 매크로를 원클릭 실행해 주는 런처 스크립트 |
| **`d4_macro.desktop`** | `~/.local/share/applications/d4_macro.desktop` | Rofi / Wofi 앱 검색기 및 데스크톱 애플리케이션 메뉴 등록 파일 |

---

## 2. 주요 기능 및 스펙

1. **단축키 토글 (ON / OFF)**:
   * 기본 토글 키: `F8` (1회 누르면 반복 시작, 다시 누르면 즉시 멈춤)
   * 완전 종료 키: `F12`
   * 대화형 메뉴 또는 `config.json`에서 `F1`~`F12`, `caps_lock`, `space`, `insert` 등 원하는 모든 키로 변경 가능
2. **연타 대상 스킬 키**:
   * 기본값: `1, 2, 3, 4, 5`
   * 원하는 스킬만 선택 가능 (예: `1 2 3 4` 또는 `1 2 q w` 등)
3. **지연시간 (1ms 초광속 ~ 느린 속도 프리셋 지원)**:
   * **[1] ⚡ 초광속 (1ms)**: `누름 1ms / 간격 1ms / 대기 1ms` (기본 적용)
   * **[2] 🚀 고속 (15ms)**: `누름 15ms / 간격 20ms / 대기 30ms`
   * **[3] 🎯 권장 표준 (35ms)**: `누름 30ms / 간격 40ms / 대기 80ms` (키 씹힘 방지 최적치)
   * **[4] 🛡️ 버프 유지 (80ms)**: `누름 50ms / 간격 80ms / 대기 150ms`
   * **[5] 🐢 느림 (150ms)**: `누름 80ms / 간격 150ms / 대기 250ms`
   * **[6] ✏️ 직접 ms 입력**: 누름, 간격, 대기 시간을 원하는 숫자로 직접 지정 가능 (소수점 지원)
4. **게임 내 OSD 알림 (`notify-send`)**:
   * 전체화면 게임 중에도 화면 우측 상단에 `[디아4 매크로] ▶ 작동 시작` / `■ 작동 정지` 팝업 표시

---

## 3. 실행 방법 3가지

1. **앱 런처 (Rofi / Wofi) 검색 실행 (권장)**:
   * Rofi 또는 Wofi에서 `디아` 또는 `d4` 검색 후 엔터
2. **원클릭 런처 스크립트 실행**:
   * 터미널: `/mnt/Data1/Gemini_Job/Diablo4_15/run.sh`
   * (파일 탐색기에서 `run.sh` 더블클릭 가능)
3. **터미널 직접 실행**:
   ```bash
   cd /mnt/Data1/Gemini_Job/Diablo4_15
   ./d4_macro
   ```

---

## 4. 다음에 이어서 수정할 때의 작업 가이드

1. **설정값만 바꾸고 싶을 때**:
   * 바이너리를 다시 컴파일할 필요 없이, [`config.json`](file:///mnt/Data1/Gemini_Job/Diablo4_15/config.json)을 수정하거나 `./d4_macro` 실행 후 `2`번(설정 메뉴)을 눌러 변경하면 즉시 반영됩니다.
2. **소스코드(`d4_macro.py`)를 수정한 뒤 바이너리를 재빌드할 때**:
   ```bash
   cd /mnt/Data1/Gemini_Job/Diablo4_15
   pyinstaller --onefile --name d4_macro d4_macro.py
   cp dist/d4_macro d4_macro
   chmod +x d4_macro
   rm -rf build dist d4_macro.spec
   ```
3. **추가 기능 아이디어 (향후 확장 가능)**:
   * 특정 스킬(예: 쿨타임이 긴 궁극기 5번)만 주기(예: 45초마다 1번)를 다르게 분리하는 기능
   * GUI 설정 창 (Tkinter/PyQt) 연동
   * 특정 마우스 버튼(측면 버튼 등) 클릭 연계
