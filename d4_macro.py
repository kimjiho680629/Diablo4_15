#!/usr/bin/env python3
"""
디아블로 4 리눅스 스킬 자동 연타 매크로
- 모든 설정(단축키, 연타 키, 지연시간) 대화형 커스텀 지정 지원
- 속도: 1ms 초광속부터 느린 속도까지 프리셋 및 직접 입력 지원
- 독립 실행 바이너리 및 config.json 자동 관리
"""

import os
import sys
import json
import time
import select
import threading
import subprocess
from pynput import keyboard
from pynput.keyboard import Controller, Key, KeyCode

# 기본 설정값
DEFAULT_CONFIG = {
    "toggle_key": "F8",
    "exit_key": "F12",
    "skill_keys": ["1", "2", "3", "4", "5"],
    "speed_preset_name": "초광속 (1ms)",
    "key_press_duration_ms": 1.0,
    "key_interval_ms": 1.0,
    "cycle_delay_ms": 1.0,
    "show_notifications": True
}

# 속도 프리셋 목록 (ms 단위)
SPEED_PRESETS = {
    "1": ("⚡ 초광속 (1ms)", 1.0, 1.0, 1.0),
    "2": ("🚀 고속 (15ms)", 15.0, 20.0, 30.0),
    "3": ("🎯 권장 표준 (35ms)", 30.0, 40.0, 80.0),
    "4": ("🛡️ 버프/여유 (80ms)", 50.0, 80.0, 150.0),
    "5": ("🐢 느림 (150ms)", 80.0, 150.0, 250.0),
}

def get_base_dir():
    """실행 파일 또는 스크립트가 위치한 실제 디렉토리 반환"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(get_base_dir(), "config.json")

def load_config():
    """config.json 로드 또는 기본값 반환"""
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    """config.json 저장"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[오류] 설정 저장 실패: {e}")

def parse_key(key_str: str):
    """문자열을 pynput Key 객체 또는 키 문자로 변환"""
    if not isinstance(key_str, str):
        return str(key_str)
    
    k = key_str.strip().lower()
    special = {
        'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
        'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
        'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        'space': Key.space, 'tab': Key.tab, 'enter': Key.enter,
        'esc': Key.esc, 'escape': Key.esc, 'backspace': Key.backspace,
        'caps_lock': Key.caps_lock, 'capslock': Key.caps_lock,
        'shift': Key.shift, 'ctrl': Key.ctrl, 'alt': Key.alt,
        'insert': Key.insert, 'delete': Key.delete,
        'home': Key.home, 'end': Key.end,
        'page_up': Key.page_up, 'pageup': Key.page_up,
        'page_down': Key.page_down, 'pagedown': Key.page_down,
        'scroll_lock': Key.scroll_lock, 'pause': Key.pause,
        'print_screen': Key.print_screen,
        'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    }
    return special.get(k, key_str.strip())

def is_same_key(event_key, target_key):
    """감지된 키 이벤트와 타깃 키 비교"""
    if isinstance(target_key, Key):
        return event_key == target_key
    if isinstance(target_key, str):
        if hasattr(event_key, 'char') and event_key.char is not None:
            return event_key.char.lower() == target_key.lower()
        if hasattr(event_key, 'name') and event_key.name is not None:
            return event_key.name.lower() == target_key.lower()
    return False

def key_to_string(k):
    """키를 화면에 표시할 수 있는 문자열로 변환"""
    if isinstance(k, Key):
        return k.name.upper()
    return str(k).upper()

def format_ms(val):
    val = float(val)
    return f"{int(val)}ms" if val.is_integer() else f"{val:.1f}ms"

# 전역 상태 변수
kb = Controller()
is_active = False
lock = threading.Lock()

def send_notification(title, message, enabled):
    """게임 중 화면에 켜짐/꺼짐 OSD 알림 전송"""
    if not enabled:
        return
    try:
        subprocess.Popen(['notify-send', '-t', '1500', '-a', '디아블로4 매크로', title, message])
    except Exception:
        pass

def macro_worker(skill_keys, press_dur, interval, cycle_delay):
    """백그라운드에서 키를 순차적으로 반복 입력하는 작업 스레드"""
    global is_active
    while True:
        with lock:
            active = is_active
            
        if active:
            for key_item in skill_keys:
                with lock:
                    if not is_active:
                        break
                
                try:
                    kb.press(key_item)
                    if press_dur > 0:
                        time.sleep(press_dur)
                    kb.release(key_item)
                except Exception:
                    pass
                
                if interval > 0:
                    time.sleep(interval)
            
            if cycle_delay > 0:
                time.sleep(cycle_delay)
        else:
            time.sleep(0.05)

def interactive_settings_menu(config):
    """터미널에서 직접 키 및 속도를 변경할 수 있는 대화형 설정 메뉴"""
    while True:
        print("\n" + "=" * 60)
        print("          🛠️  디아블로 4 매크로 커스텀 설정  🛠️")
        print("=" * 60)
        print(f" [1] 토글 시작/정지 키 변경 : 현재 [ {config['toggle_key']} ]")
        print(f" [2] 프로그램 종료 키 변경   : 현재 [ {config['exit_key']} ]")
        print(f" [3] 연타할 스킬 키 변경     : 현재 [ {', '.join(config['skill_keys'])} ]")
        
        spd_name = config.get('speed_preset_name', '직접 설정')
        p_ms = format_ms(config['key_press_duration_ms'])
        i_ms = format_ms(config['key_interval_ms'])
        c_ms = format_ms(config['cycle_delay_ms'])
        print(f" [4] 속도(지연시간) 설정     : {spd_name} (누름 {p_ms} / 간격 {i_ms} / 대기 {c_ms})")
        print(f" [5] 화면 알림(OSD) 연동     : {'켜짐' if config['show_notifications'] else '꺼짐'}")
        print(" [0] 설정 저장 및 매크로 시작")
        print("=" * 60)
        
        choice = input("변경할 번호를 선택하세요 [0-5]: ").strip()
        
        if choice == '1':
            new_key = input("새로운 토글 키 입력 (예: F8, F7, F6, Caps_Lock, Space 등): ").strip()
            if new_key:
                config['toggle_key'] = new_key
                save_config(config)
                print(f"✔️ 토글 키가 [ {new_key} ]로 변경되었습니다.")
                
        elif choice == '2':
            new_key = input("새로운 종료 키 입력 (기본: F12): ").strip()
            if new_key:
                config['exit_key'] = new_key
                save_config(config)
                print(f"✔️ 종료 키가 [ {new_key} ]로 변경되었습니다.")
                
        elif choice == '3':
            print("연타할 키들을 공백 또는 쉼표로 구분하여 입력하세요.")
            print("예시: 1 2 3 4 5  또는  1 2 3 4  또는  1 2 q w")
            new_keys_str = input("입력: ").strip()
            if new_keys_str:
                parts = [p.strip() for p in new_keys_str.replace(',', ' ').split() if p.strip()]
                if parts:
                    config['skill_keys'] = parts
                    save_config(config)
                    print(f"✔️ 연타할 키가 [ {', '.join(parts)} ]로 변경되었습니다.")
                    
        elif choice == '4':
            print("\n--- [ 속도 (지연시간) 선택 ] ---")
            print(" [1] ⚡ 초광속   (1ms)   : 극단적인 1ms 연타 (사용자 요청 속도)")
            print(" [2] 🚀 고속     (15ms)  : 매우 빠른 반응 속도")
            print(" [3] 🎯 권장표준 (35ms)  : 키 씹힘 없는 안정적인 고속")
            print(" [4] 🛡️ 버프유지 (80ms)  : 여유로운 자원/버프 관리")
            print(" [5] 🐢 느림     (150ms) : 아주 느리고 여유로운 입력")
            print(" [6] ✏️ 직접 ms 입력    : 누름 시간/간격/사이클을 원하는 숫자로 직접 입력")
            spd_choice = input("속도 번호 선택 [1-6]: ").strip()
            
            if spd_choice in SPEED_PRESETS:
                name, p, i, c = SPEED_PRESETS[spd_choice]
                config['speed_preset_name'] = name
                config['key_press_duration_ms'] = p
                config['key_interval_ms'] = i
                config['cycle_delay_ms'] = c
                save_config(config)
                print(f"✔️ 속도가 '{name}'으로 적용되었습니다.")
            elif spd_choice == '6':
                try:
                    p = float(input("1. 키를 누르고 있는 시간 (ms, 예: 1): "))
                    i = float(input("2. 키와 키 사이 간격 (ms, 예: 1): "))
                    c = float(input("3. 1사이클 완료 후 대기 시간 (ms, 예: 1): "))
                    config['speed_preset_name'] = f"사용자 정의 ({format_ms(p)})"
                    config['key_press_duration_ms'] = max(0.0, p)
                    config['key_interval_ms'] = max(0.0, i)
                    config['cycle_delay_ms'] = max(0.0, c)
                    save_config(config)
                    print("✔️ 사용자 정의 지연시간이 적용되었습니다.")
                except ValueError:
                    print("❌ 잘못된 숫자입니다. 변경되지 않았습니다.")
                    
        elif choice == '5':
            config['show_notifications'] = not config['show_notifications']
            save_config(config)
            print(f"✔️ 화면 알림이 {'켜졌습니다' if config['show_notifications'] else '꺼졌습니다'}.")
            
        elif choice == '0':
            print("\n설정을 저장하고 매크로를 시작합니다...\n")
            break

def run_macro_loop(config):
    """매크로 메인 감시 및 실행 루프"""
    global is_active
    
    toggle_key_str = config.get("toggle_key", "F8")
    exit_key_str = config.get("exit_key", "F12")
    raw_skill_keys = config.get("skill_keys", ["1", "2", "3", "4", "5"])
    
    press_ms = float(config.get("key_press_duration_ms", 1.0))
    interval_ms = float(config.get("key_interval_ms", 1.0))
    cycle_ms = float(config.get("cycle_delay_ms", 1.0))

    press_dur = max(0.0, press_ms / 1000.0)
    interval = max(0.0, interval_ms / 1000.0)
    cycle_delay = max(0.0, cycle_ms / 1000.0)
    show_notifications = config.get("show_notifications", True)
    
    parsed_toggle_key = parse_key(toggle_key_str)
    parsed_exit_key = parse_key(exit_key_str)
    parsed_skill_keys = [parse_key(k) for k in raw_skill_keys]

    print("=" * 64)
    print("      ⚔️  디아블로 4 리눅스 스킬 자동 연타 매크로  ⚔️")
    print("=" * 64)
    print(f" [토글 시작/정지] : [ {key_to_string(parsed_toggle_key)} ] 키")
    print(f" [프로그램 종료 ] : [ {key_to_string(parsed_exit_key)} ] 키")
    print(f" [연타 대상 키  ] : {', '.join([key_to_string(k) for k in parsed_skill_keys])}")
    print(f" [적용된 속도   ] : {config.get('speed_preset_name', '커스텀')} (누름 {format_ms(press_ms)} / 간격 {format_ms(interval_ms)} / 대기 {format_ms(cycle_ms)})")
    print(f" [화면 알림 연동] : {'활성화 (notify-send)' if show_notifications else '비활성화'}")
    print("=" * 64)
    print("💡 게임 화면으로 전환한 뒤 토글 키를 눌러 켜고 끌 수 있습니다.")
    print("💡 터미널에서 Ctrl+C 또는 종료 키(F12)를 누르면 프로그램이 종료됩니다.\n")

    # 워커 스레드 시작
    worker = threading.Thread(
        target=macro_worker,
        args=(parsed_skill_keys, press_dur, interval, cycle_delay),
        daemon=True
    )
    worker.start()

    def on_press(key):
        global is_active
        
        # 토글 키 감지
        if is_same_key(key, parsed_toggle_key):
            with lock:
                is_active = not is_active
                current_state = is_active
                
            if current_state:
                print(f"[{time.strftime('%H:%M:%S')}] ▶ [ON] 스킬 자동 연타 시작 (토글 키를 누르면 정지)")
                send_notification("디아블로 4 매크로", f"▶ 작동 시작 (ON) - {', '.join([key_to_string(k) for k in parsed_skill_keys])}", show_notifications)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ■ [OFF] 스킬 자동 연타 정지 (토글 키를 누르면 시작)")
                send_notification("디아블로 4 매크로", "■ 작동 정지 (OFF)", show_notifications)

        # 프로그램 완전 종료 키 감지
        elif is_same_key(key, parsed_exit_key):
            print(f"\n[{time.strftime('%H:%M:%S')}] 🛑 프로그램을 완전히 종료합니다.")
            send_notification("디아블로 4 매크로", "프로그램 완전 종료", show_notifications)
            return False

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def main():
    config = load_config()

    # 인자로 바로 옵션 준 경우 처리
    if "--setup" in sys.argv:
        interactive_settings_menu(config)
        run_macro_loop(config)
        return
    elif "--run" in sys.argv:
        run_macro_loop(config)
        return

    # 시작 메뉴 표시 (3초 대기 후 기본 실행)
    print("\n" + "=" * 64)
    print("      ⚔️  디아블로 4 리눅스 스킬 자동 연타 매크로  ⚔️")
    print("=" * 64)
    print(" [1] 바로 매크로 시작 (엔터 또는 3초 후 자동 시작)")
    print(" [2] 설정 변경 (단축키 / 스킬 키 / 1ms~느린 속도 조절)")
    print(" [3] 프로그램 종료")
    print("=" * 64)
    sys.stdout.write("선택 [1/2/3] (3초 후 자동시작): ")
    sys.stdout.flush()

    # 3초 동안 사용자 입력 대기 (Non-blocking)
    rlist, _, _ = select.select([sys.stdin], [], [], 3.0)
    
    if rlist:
        user_input = sys.stdin.readline().strip()
        if user_input == '2':
            interactive_settings_menu(config)
        elif user_input == '3':
            print("프로그램을 종료합니다.")
            return
        else:
            print("\n매크로를 바로 시작합니다...\n")
    else:
        print("\n\n⏱️  3초가 경과하여 현재 설정으로 매크로를 자동 시작합니다...\n")

    run_macro_loop(config)

if __name__ == '__main__':
    main()
