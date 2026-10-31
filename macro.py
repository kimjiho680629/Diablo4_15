#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리눅스(Wayland / XWayland) 초고속 게이밍 듀얼 매크로 유틸리티
- 로지텍 G-HUB 스타일의 1ms 단위 초고속 키보드 및 마우스 연타 지원
- 매크로 1: F키 등 키보드 초고속 연타
- 매크로 2: 왼쪽 마우스 버튼(LMB) 등 마우스 초고속 연타
- evdev 기반 로지텍 게이밍 마우스 하드웨어 버튼(사이드 앞/뒤 버튼 등) 즉각 감지
- pynput 기반 키보드 단축키 및 전역 가상 입력 주입
"""

import os
import sys
import time
import json
import signal
import threading
import select
from pathlib import Path

try:
    import evdev
    from evdev import ecodes
except ImportError:
    print("[오류] evdev 모듈이 설치되어 있지 않습니다. (pip install evdev)")
    sys.exit(1)

try:
    from pynput.keyboard import Controller as KbController, Key, KeyCode, Listener as KeyListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("[오류] pynput 모듈이 설치되어 있지 않습니다. (pip install pynput)")
    sys.exit(1)

CONFIG_PATH = Path(__file__).parent / "config.json"

class Color:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def precise_sleep(seconds: float):
    """
    Sub-millisecond 정밀도를 보장하는 하이브리드 고정밀 슬립 함수.
    CPU를 과도하게 사용하지 않으면서도 정밀한 지연 시간을 보장합니다.
    """
    if seconds <= 0:
        return
    end_time = time.perf_counter() + seconds
    remaining = end_time - time.perf_counter()
    if remaining > 0.0015:
        time.sleep(remaining - 0.001)
    while time.perf_counter() < end_time:
        pass

class MacroUnit:
    """개별 매크로 동작 단위 (키보드 또는 마우스 연타)"""
    def __init__(self, unit_id: str, cfg: dict, kb: KbController, mouse: MouseController):
        self.unit_id = unit_id
        self.kb = kb
        self.mouse = mouse
        self.macro_active = False
        self.is_pressed = False
        self.stats = {"runs": 0, "actions": 0, "last_ms": 0.0}
        self.update_config(cfg)

    def update_config(self, cfg: dict):
        self.name = cfg.get("name", self.unit_id)
        self.enabled = bool(cfg.get("enabled", True))
        self.target_type = cfg.get("target_type", "keyboard")  # keyboard, mouse_right, mouse_left
        self.target_value = cfg.get("target_value", cfg.get("target_key", "f"))
        self.burst_count = int(cfg.get("burst_count", 100))
        self.press_delay = float(cfg.get("press_delay_ms", 1.0)) / 1000.0
        self.release_delay = float(cfg.get("release_delay_ms", 1.0)) / 1000.0
        self.mode = cfg.get("mode", "burst").lower()
        self.mouse_trigger = cfg.get("mouse_trigger", "none")
        self.keyboard_trigger = str(cfg.get("keyboard_trigger", "")).lower()
        self.high_precision = bool(cfg.get("high_precision", True))

    def _sleep(self, duration: float):
        if self.high_precision:
            precise_sleep(duration)
        else:
            time.sleep(duration)

    def _press_target(self):
        if self.target_type == "ctrl_mouse_left":
            self.mouse.press(Button.left)
        elif self.target_type == "ctrl_mouse_right":
            self.mouse.press(Button.right)
        elif self.target_type == "mouse_right":
            self.mouse.press(Button.right)
        elif self.target_type == "mouse_left":
            self.mouse.press(Button.left)
        else:
            self.kb.press(self.target_value)

    def _release_target(self):
        try:
            if self.target_type == "ctrl_mouse_left":
                self.mouse.release(Button.left)
            elif self.target_type == "ctrl_mouse_right":
                self.mouse.release(Button.right)
            elif self.target_type == "mouse_right":
                self.mouse.release(Button.right)
            elif self.target_type == "mouse_left":
                self.mouse.release(Button.left)
            else:
                self.kb.release(self.target_value)
        except Exception:
            pass

    def get_target_display_name(self) -> str:
        if self.target_type == "ctrl_mouse_left":
            return "Ctrl + 마우스 좌클릭 (아이템 버리기)"
        elif self.target_type == "ctrl_mouse_right":
            return "Ctrl + 마우스 우클릭"
        elif self.target_type == "mouse_right":
            return "마우스 우클릭 (RMB)"
        elif self.target_type == "mouse_left":
            return "마우스 좌클릭 (LMB)"
        return f"키보드 [{self.target_value.upper()}]"

    def execute_burst(self):
        """지정된 횟수만큼 초고속 연타 실행"""
        if self.macro_active:
            return
        self.macro_active = True

        def _run():
            target_name = self.get_target_display_name()
            start_time = time.perf_counter()
            count = 0
            is_ctrl = self.target_type in ("ctrl_mouse_left", "ctrl_mouse_right")
            try:
                print(f"{Color.YELLOW}⚡ [{self.name}] {target_name} {self.burst_count}회 연타 중...{Color.RESET}", end="\r", flush=True)
                if is_ctrl:
                    self.kb.press(Key.ctrl)
                    self._sleep(0.002)
                for _ in range(self.burst_count):
                    if not self.macro_active:
                        break
                    self._press_target()
                    self._sleep(self.press_delay)
                    self._release_target()
                    self._sleep(self.release_delay)
                    count += 1
            except Exception as e:
                print(f"\n{Color.RED}[실행 오류 - {self.name}] {e}{Color.RESET}")
            finally:
                self._release_target()
                if is_ctrl:
                    try:
                        self.kb.release(Key.ctrl)
                    except Exception:
                        pass
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                self.stats["runs"] += 1
                self.stats["actions"] += count
                self.stats["last_ms"] = duration_ms
                self.macro_active = False
                print(f"{Color.GREEN}✓ [{self.name}] {count}회 입력 완료 ({duration_ms:.1f}ms 소요) | 누적 {self.stats['runs']}회{Color.RESET}    ")

        threading.Thread(target=_run, daemon=True).start()

    def execute_hold(self):
        """Hold 모드: 버튼을 누르고 있는 동안 지속 연타"""
        if self.macro_active:
            return
        self.macro_active = True

        def _run_hold():
            target_name = self.get_target_display_name()
            start_time = time.perf_counter()
            count = 0
            is_ctrl = self.target_type in ("ctrl_mouse_left", "ctrl_mouse_right")
            print(f"{Color.YELLOW}⚡ [{self.name}] {target_name} 연타 유지 중 (버튼을 떼면 정지)...{Color.RESET}", end="\r", flush=True)
            try:
                if is_ctrl:
                    self.kb.press(Key.ctrl)
                    self._sleep(0.002)
                while self.macro_active and self.is_pressed:
                    self._press_target()
                    self._sleep(self.press_delay)
                    self._release_target()
                    self._sleep(self.release_delay)
                    count += 1
            finally:
                self._release_target()
                if is_ctrl:
                    try:
                        self.kb.release(Key.ctrl)
                    except Exception:
                        pass
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                self.stats["runs"] += 1
                self.stats["actions"] += count
                self.stats["last_ms"] = duration_ms
                self.macro_active = False
                print(f"{Color.GREEN}✓ [{self.name} 정지] 총 {count}회 입력 ({duration_ms:.1f}ms 소요){Color.RESET}    ")

        threading.Thread(target=_run_hold, daemon=True).start()

    def trigger(self, is_press: bool):
        if not self.enabled:
            return

        if not is_press:
            self.is_pressed = False
            return

        self.is_pressed = True

        if self.mode == "burst":
            self.execute_burst()
        elif self.mode == "hold":
            self.execute_hold()
        elif self.mode == "toggle":
            if self.macro_active:
                self.macro_active = False
                print(f"\n{Color.YELLOW}[{self.name} 토글 OFF] 정지{Color.RESET}")
            else:
                self.execute_burst()

    def stop(self):
        self.macro_active = False
        self.is_pressed = False
        self._release_target()
        if self.target_type in ("ctrl_mouse_left", "ctrl_mouse_right"):
            try:
                self.kb.release(Key.ctrl)
            except Exception:
                pass

class MacroEngine:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.keyboard = KbController()
        self.mouse = MouseController()
        self.running = True
        self.master_enabled = True
        self.units = {}
        self.load_config()

    def load_config(self):
        """설정 파일 로드 및 유닛 동기화"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"{Color.RED}[설정 오류] config.json 읽기 실패: {e}{Color.RESET}")
            data = {}

        self.master_enabled = bool(data.get("master_enabled", True))
        self.emergency_stop_key = str(data.get("emergency_stop_key", "f12")).lower()

        # 하위 호환성 체크: macro1 / macro2 구조가 없으면 변환
        if "macro1" not in data:
            data["macro1"] = {
                "name": "매크로 1 (Ctrl + 우클릭 연타)",
                "enabled": True,
                "target_type": "ctrl_mouse_right",
                "target_value": "ctrl_right",
                "burst_count": data.get("burst_count", 100),
                "press_delay_ms": data.get("press_delay_ms", 1.0),
                "release_delay_ms": data.get("release_delay_ms", 1.0),
                "mode": data.get("mode", "burst"),
                "mouse_trigger": data.get("mouse_trigger", "BTN_SIDE"),
                "keyboard_trigger": data.get("keyboard_trigger", "f8"),
                "high_precision": data.get("high_precision", True)
            }

        if "macro2" not in data:
            data["macro2"] = {
                "name": "매크로 2 (Ctrl + 좌클릭 연타)",
                "enabled": True,
                "target_type": "ctrl_mouse_left",
                "target_value": "ctrl_left",
                "burst_count": 50,
                "press_delay_ms": 2.0,
                "release_delay_ms": 2.0,
                "mode": "hold",
                "mouse_trigger": "BTN_EXTRA",
                "keyboard_trigger": "f7",
                "high_precision": True
            }

        for uid in ("macro1", "macro2"):
            u_cfg = data.get(uid, {})
            if uid in self.units:
                self.units[uid].update_config(u_cfg)
            else:
                self.units[uid] = MacroUnit(uid, u_cfg, self.keyboard, self.mouse)

    def print_status_banner(self):
        print(f"\n{Color.CYAN}{'='*65}{Color.RESET}")
        print(f"{Color.BOLD}   디아블로4 / 리눅스 초고속 듀얼 매크로 실행기{Color.RESET}")
        print(f"{Color.CYAN}{'='*65}{Color.RESET}")
        for uid, unit in self.units.items():
            status_color = Color.GREEN if unit.enabled else Color.RED
            status_text = "활성" if unit.enabled else "비활성"
            print(f" • {Color.BOLD}[{unit.name}]{Color.RESET} ({status_color}{status_text}{Color.RESET})")
            print(f"   - 대상(Target)   : {Color.YELLOW}{unit.get_target_display_name()}{Color.RESET}")
            print(f"   - 동작 모드      : {Color.YELLOW}{unit.mode}{Color.RESET} (1회: {unit.burst_count}회 | {unit.press_delay*1000:.1f}ms/{unit.release_delay*1000:.1f}ms)")
            print(f"   - 마우스 트리거  : {Color.CYAN}{unit.mouse_trigger}{Color.RESET}")
            print(f"   - 키보드 트리거  : {Color.CYAN}{unit.keyboard_trigger.upper() or '없음'}{Color.RESET}")
            print(f"{Color.CYAN}{'-'*65}{Color.RESET}")
        print(f" • 긴급 중지 단축키  : {Color.RED}{self.emergency_stop_key.upper()}{Color.RESET} / Ctrl+C")
        print(f"{Color.CYAN}{'='*65}{Color.RESET}\n")

    def emergency_stop(self):
        """모든 매크로 즉시 중지 및 릴리스"""
        for unit in self.units.values():
            unit.stop()
        print(f"\n{Color.RED}🛑 [긴급 정지] 모든 매크로 동작이 즉시 중단되었습니다.{Color.RESET}")

    def find_mouse_devices(self):
        """시스템에 연결된 마우스 장치 자동 탐색"""
        devices = []
        target_codes = {ecodes.BTN_SIDE, ecodes.BTN_EXTRA, ecodes.BTN_MIDDLE, ecodes.BTN_BACK, ecodes.BTN_FORWARD}
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps:
                    keys = caps[ecodes.EV_KEY]
                    if any(c in keys for c in target_codes) or "mouse" in dev.name.lower() or "g703" in dev.name.lower():
                        devices.append(dev)
            except Exception:
                continue
        return devices

    def start_mouse_listener(self):
        """evdev 하드웨어 마우스 및 pynput 듀얼 리스너"""
        devices = self.find_mouse_devices()
        code_to_name = {
            ecodes.BTN_SIDE: "BTN_SIDE",
            ecodes.BTN_BACK: "BTN_SIDE",
            ecodes.BTN_EXTRA: "BTN_EXTRA",
            ecodes.BTN_FORWARD: "BTN_EXTRA",
            ecodes.BTN_MIDDLE: "BTN_MIDDLE"
        }

        # 1. evdev 리스너
        if devices:
            print(f"{Color.CYAN}[장치 연결]{Color.RESET} 감지된 마우스 장치 목록:")
            for d in devices:
                print(f"  • {d.name} ({d.path})")

            def _evdev_monitor():
                dev_map = {d.fd: d for d in devices}
                while self.running:
                    try:
                        r, _, _ = select.select(list(dev_map.keys()), [], [], 0.5)
                        for fd in r:
                            dev = dev_map.get(fd)
                            if not dev:
                                continue
                            for event in dev.read():
                                if event.type == ecodes.EV_KEY and event.code in code_to_name:
                                    trigger_name = code_to_name[event.code]
                                    is_press = (event.value == 1)
                                    is_release = (event.value == 0)
                                    if is_press or is_release:
                                        self.dispatch_mouse_trigger(trigger_name, is_press)
                    except (OSError, select.error):
                        time.sleep(1)
                    except Exception:
                        if self.running:
                            time.sleep(0.1)

            threading.Thread(target=_evdev_monitor, daemon=True).start()

        # 2. pynput 마우스 보조 리스너
        def on_mouse_click(x, y, button, pressed):
            name = None
            if button == Button.x1:
                name = "BTN_SIDE"
            elif button == Button.x2:
                name = "BTN_EXTRA"
            elif button == Button.middle:
                name = "BTN_MIDDLE"
            if name:
                self.dispatch_mouse_trigger(name, pressed)

        m_listener = MouseListener(on_click=on_mouse_click)
        m_listener.daemon = True
        m_listener.start()

    def dispatch_mouse_trigger(self, trigger_name: str, is_press: bool):
        if not self.master_enabled:
            return
        for unit in self.units.values():
            if unit.mouse_trigger == trigger_name:
                unit.trigger(is_press)

    def dispatch_keyboard_trigger(self, key_str: str, is_press: bool):
        if not self.master_enabled:
            return
        for unit in self.units.values():
            if unit.keyboard_trigger and unit.keyboard_trigger == key_str:
                unit.trigger(is_press)

    def start_keyboard_listener(self):
        """pynput 전역 키보드 단축키 감지"""
        def _get_key_str(key):
            if isinstance(key, KeyCode):
                return key.char.lower() if key.char else str(key.vk)
            elif isinstance(key, Key):
                return key.name.lower()
            return str(key)

        def on_press(key):
            try:
                k_str = _get_key_str(key)
                if k_str == self.emergency_stop_key:
                    self.emergency_stop()
                    return
                self.dispatch_keyboard_trigger(k_str, True)
            except Exception:
                pass

        def on_release(key):
            try:
                k_str = _get_key_str(key)
                self.dispatch_keyboard_trigger(k_str, False)
            except Exception:
                pass

        listener = KeyListener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        return listener

    def run(self):
        self.print_status_banner()
        self.start_mouse_listener()
        self.start_keyboard_listener()

        print(f"{Color.GREEN}▶ 듀얼 매크로가 백그라운드에서 대기 중입니다.{Color.RESET}")
        print(f"  • 매크로 1: {self.units['macro1'].mouse_trigger} 또는 [{self.units['macro1'].keyboard_trigger.upper()}]")
        print(f"  • 매크로 2: {self.units['macro2'].mouse_trigger} 또는 [{self.units['macro2'].keyboard_trigger.upper()}]")
        print(f"  • 종료: {Color.BOLD}Ctrl+C{Color.RESET} / 설정 새로고침: {Color.BOLD}'r'{Color.RESET} 입력\n")

        while self.running:
            try:
                user_cmd = sys.stdin.readline()
                if not user_cmd:
                    time.sleep(0.5)
                    continue
                cmd = user_cmd.strip().lower()
                if cmd == "r":
                    print(f"{Color.CYAN}↻ config.json 설정을 다시 불러오는 중...{Color.RESET}")
                    self.load_config()
                    self.print_status_banner()
                elif cmd in ("1", "test1"):
                    print(f"{Color.YELLOW}[테스트] 매크로 1 실행{Color.RESET}")
                    self.units["macro1"].execute_burst()
                elif cmd in ("2", "test2"):
                    print(f"{Color.YELLOW}[테스트] 매크로 2 실행{Color.RESET}")
                    self.units["macro2"].execute_burst()
                elif cmd in ("s", "stop"):
                    self.emergency_stop()
                elif cmd in ("q", "quit", "exit"):
                    self.running = False
                    break
            except (KeyboardInterrupt, EOFError):
                self.running = False
                break

        print(f"\n{Color.YELLOW}[종료] 프로그램을 종료합니다.{Color.RESET}")

if __name__ == "__main__":
    engine = MacroEngine(CONFIG_PATH)
    try:
        engine.run()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[종료] 프로그램을 안전하게 종료했습니다.{Color.RESET}")
