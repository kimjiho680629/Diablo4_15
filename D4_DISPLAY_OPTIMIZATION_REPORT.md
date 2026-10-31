# 디아블로 4 실행 문제 해결 및 모니터/디스플레이 최적화 보고서

작성 일시: 2026-10-27  
시스템 환경: Arch Linux (Kernel 7.2.11) / Hyprland (Wayland) / AMD Ryzen 9 5950X / MSI GeForce RTX 3090 24GB (Driver 615.78.08)

---

## 1. 디아블로 4 실행 불가 원인 및 해결 내역

### A. 증상
* Lutris 및 Battle.net에서 디아블로 4 실행을 눌렀으나, 배틀넷에는 "게임 실행 중"으로 표시되고 실제 게임 창은 전혀 뜨지 않음.
* 배틀넷에서 [검사 및 복구]를 눌렀으나 "검사 중" 표시만 뜨고 반응이 없거나 극도로 지연됨.

### B. 근본 원인 분석
1. **TACT/CASC 인덱스 병합 중 `Error 183` 충돌 발생**:
   * 인게임 로그(`FenrisDebug.txt`):
     ```text
     [Sigma] [tact] [:0]: Failed to rename group index after merge. Error (183): 파일이 이미 존재합니다
     ```
   * 블리자드의 스토리지 엔진(TACT)이 패치 인덱스를 병합하면서 임시 파일(`index_group.2912.1`, 116MB)을 생성한 뒤 최종 인덱스 파일명(`b66cf200747825a3eb2b29be4a5642fe.index`)으로 변경(`MoveFile`)을 시도함.
   * Linux/Wine 환경에서 동일한 크기(116MB)의 타겟 파일이 이미 존재하여 Windows 오류 183(`ERROR_ALREADY_EXISTS`)이 발생함.
   * 메인 스레드가 `ntsync_schedule` 및 `futex` 커널 동기화 객체에서 무한 대기 상태(Deadlock)에 빠져 그래픽 서브시스템 및 창 생성이 차단됨.
2. **배틀넷 에이전트(Agent) 자체 업데이트 대기열 지연**:
   * 사용자가 [검사 및 복구]를 요청했을 때 배틀넷 에이전트 프로그램 자체의 백그라운드 업데이트(`OP_UPDATE for 'agent'`)가 선행 진행 중이었음.
   * 에이전트 업데이트가 완료될 때까지 디아블로 4 검사 명령(`OP_REPAIR for 'fenris'`)이 대기열(`Pending Queue` / `Queued`)에 묶여 있어 겉보기에 먹통처럼 보임.

### C. 조치 결과
* 백그라운드에 갇혀 있던 프로세스 정리 및 배틀넷 재시작 과정에서 충돌 임시 파일(`index_group.2912.1`) 자동 삭제 완료.
* 본게임 데이터 무결성이 보장된 상태에서 정상 실행 복구 완료.

---

## 2. 워크스페이스 및 모니터 고정 자동실행 설정

### A. 목표 구성
* **워크스페이스 9 (`workspace 9`)**: **TouchDeck** (터치 스트림덱) 고정 실행 $\rightarrow$ **`DP-1`** (JTG 1920×1280 터치스크린 모니터)
* **워크스페이스 10 (`workspace 10`)**: **SysDash** (AIDA64 센서패널) 고정 실행 $\rightarrow$ **`DP-3`** (ARZOPA 2560×1440 180Hz 모니터)
* 시스템 부팅 및 Hyprland 시작 시 **자동 실행 및 전체화면 고정**.

### B. 수정된 설정 파일 목록

#### 1) `~/.config/hypr/workspaces.conf` & `workspaces.lua`
모니터와 워크스페이스의 기본 바인딩을 명확히 설정:
```ini
workspace=1,monitor:DP-2,default:true
workspace=2,monitor:DP-2
workspace=3,monitor:DP-2
workspace=4,monitor:DP-2
workspace=5,monitor:HDMI-A-1,default:true
workspace=6,monitor:HDMI-A-1
workspace=7,monitor:HDMI-A-1
workspace=8,monitor:HDMI-A-1
workspace=9,monitor:DP-1,default:true
workspace=10,monitor:DP-3,default:true
```

#### 2) `~/.config/hypr/custom.lua`
윈도우 규칙(`windowrulev2` 및 `hl.window_rule`)과 자동 실행 등록:
```lua
-- TouchDeck Window Rules for DP-1 Touch Screen (Always Fullscreen on Workspace 9)
"monitor DP-1, class:^(touchdeck)$",
"workspace 9, class:^(touchdeck)$",
"fullscreen, class:^(touchdeck)$",

-- SysDash HUD Window Rules for DP-3 Monitor (Always Fullscreen on Workspace 10)
"monitor DP-3, class:^(sys-dash)$",
"workspace 10, class:^(sys-dash)$",
"fullscreen, class:^(sys-dash)$",
"monitor DP-3, title:^(AIDA64 SENSOR PANEL.*)$",
"workspace 10, title:^(AIDA64 SENSOR PANEL.*)$",
"fullscreen, title:^(AIDA64 SENSOR PANEL.*)$",
```

#### 3) `~/.config/hypr/conf/autostart.lua`
시스템 부팅 시 실행 보장:
```lua
-- Start SysDash Telemetry Panel (DP-3 / Workspace 10)
hl.exec_cmd("/mnt/Data1/Gemini_Job/Sysdash/run_dashboard.sh")

-- Start TouchDeck Touch Screen (DP-1 / Workspace 9)
hl.exec_cmd("/mnt/Data1/Gemini_Job/Touch/run_touchdeck.sh")
```

#### 4) 스크립트 중복 실행 방지 보강
* `/mnt/Data1/Gemini_Job/Sysdash/run_dashboard.sh`: `pgrep` 기반 중복 실행 방지 가드 추가.
* `/mnt/Data1/Gemini_Job/Touch/run_touchdeck.sh`: 프로세스 활성 검사 가드 유지.

---

## 3. 디아블로 4 끊김(스터터링) 원인 및 최적화 적용

### A. 끊김의 주요 원인
1. **극단적인 주사율 혼용**: 180Hz 2대(DP-2, DP-3)와 60Hz 2대(HDMI-A-1, DP-1)를 단일 GPU(RTX 3090)에 연결하여 사용함에 따라, 60Hz 화면 갱신 시 Wayland 컴포지터 프레임 동기화 충돌로 인한 미세 끊김(Micro-stuttering) 발생.
2. **분수 스케일링(Fractional Scaling 1.25/1.5배)**: 4개 중 3개 모니터가 소수점 배율로 렌더링되어 GPU 오버헤드 증가.
3. **인게임 FPS 제한 불일치**: 180Hz 모니터에서 게임 내부 프레임이 **100 FPS**로 제한되어 있어 180Hz 주사율과 엇박자 발생(Judder).
4. **배틀넷 백그라운드 부하**: 게임 실행 중에도 크롬 렌더러가 GPU/CPU를 상시 소모.

### B. 적용 완료된 최적화 설정

| 대상 파일 | 수정 항목 | 이전 값 | 변경 적용 값 | 목적 및 효과 |
| :--- | :--- | :---: | :---: | :--- |
| `LocalPrefs.txt` | `MaxForegroundFPS` | `100` / `180` | **`175`** | G-Sync/VRR 가동 범위 내 완벽 고정, 티어링/인풋렉/스터터링 제거 |
| `LocalPrefs.txt` | `MaxBackgroundFPS` | `84` | **`60`** | 백그라운드 전환 시 불필요한 GPU 낭비 차단 |
| `Battle.net.config` | `GameLaunchWindowBehavior` | 미설정(`0`) | **`2`** | 게임 실행 시 배틀넷 런처 완전 자동 종료 (CPU/GPU 자원 독점 확보) |

---

## 4. 모니터 분리 및 권장 하드웨어 배치 가이드

### A. 게이밍 전용 PC (RTX 3090 + 5950X)
* **[최고 추천] 단일 모니터**: **`CMT GM34-CWQ2` (34인치 울트라와이드 21:9, 3440×1440 @ 180Hz, DP-2)**
  * 디아블로 4에서 좌우 시야각(FOV) 대폭 확장으로 게임 플레이 최적.
  * 다른 주사율 간섭 0%, 분수 스케일링 간섭 0%로 극강의 부드러움 제공.
* **[듀얼 구성 시]**: 서브 모니터가 필요할 경우 **`ARZOPA (2560×1440 @ 180Hz, DP-3)`** 만 함께 연결하여 **[180Hz + 180Hz] 동일 주사율**로 운영 (주사율 일치로 스터터링 방지).

### B. 보조/사무 작업용 PC
* **`Dell U2723QE` (27인치 4K 16:9, 3840×2160 @ 60Hz)**: 웹서핑, 문서 작업, 동영상 감상 시 선명한 가독성 제공.
* **`JTG S123` (1920×1280 @ 60Hz 터치스크린)**: TouchDeck/스트림덱 및 제어용 모니터로 활용.
