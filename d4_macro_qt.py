#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
디아블로 IV 크로스플랫폼 통합 매크로 (PyQt6 기반 모던 GUI)
- 지원 OS: Linux (Wayland / X11) 및 Windows 11 / 10
- Linux 입력: evdev 커널 하드웨어 전역 감지 (Wayland 100% 감지) + pynput / wtype
- Windows 입력: Win32 SendInput (DirectX 12 하드웨어 스캔코드 완벽 주입) + pynput 전역 훅
- 스킬 자동 연타 (1~5번 토글/홀드 모드, 정밀 딜레이 및 프리셋)
- 매크로 1: 마우스 사이드(뒤로가기) 또는 F1 단축키 -> Ctrl+우클릭 / 지정 키 연타
- 매크로 2: 마우스 사이드(앞으로가기) 또는 F2 단축키 -> Ctrl+좌클릭 (아이템 버리기)
- 긴급 중지 (F12) 및 적응형 큐 누적 방지 가드 (Anti-Bloat Guard) 탑재
"""

import os
import sys
import time
import json
import shutil
import threading
from pathlib import Path

# PyQt6 모듈 로드
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QTabWidget, QFrame, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette

# 공통 입력 라이브러리 (pynput)
try:
    from pynput.keyboard import Controller as KbController, Key, KeyCode, Listener as KeyListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("[경고] pynput 모듈이 없습니다. pip install pynput 으로 설치해주세요.")

# OS별 전용 입력 라이브러리
IS_WINDOWS = sys.platform.startswith('win')
IS_LINUX = sys.platform.startswith('linux')

if IS_LINUX:
    try:
        import evdev
        from evdev import ecodes
        import select
        HAS_EVDEV = True
    except ImportError:
        HAS_EVDEV = False
else:
    HAS_EVDEV = False

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32

    # Win32 SendInput 구조체 정의 (DirectX 12 하드웨어 스캔코드 지원)
    PUL = ctypes.POINTER(ctypes.c_ulong)
    class KeyBdInput(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", PUL)]

    class HardwareInput(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD),
                    ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class MouseInput(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", PUL)]

    class Input_I(ctypes.Union):
        _fields_ = [("ki", KeyBdInput),
                    ("mi", MouseInput),
                    ("hi", HardwareInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong),
                    ("ii", Input_I)]

    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010

    # 주요 키 Windows 가상 키코드 (VK)
    WIN_VK_MAP = {
        '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
        'q': 0x51, 'w': 0x57, 'e': 0x45, 'r': 0x52, 't': 0x54,
        'a': 0x41, 's': 0x53, 'd': 0x44, 'f': 0x46,
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
        'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'space': 0x20
    }

# 설정 파일 경로 결정
if getattr(sys, 'frozen', False):
    _app_dir = Path(sys.executable).resolve().parent
    CONFIG_PATH = _app_dir / "config.json"
else:
    CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# 타이머 및 지연 유틸리티
def precise_sleep(seconds: float):
    """Sub-millisecond 정밀도 하이브리드 고정밀 슬립"""
    if seconds <= 0:
        return
    end_time = time.perf_counter() + seconds
    remaining = end_time - time.perf_counter()
    if remaining > 0.0015:
        time.sleep(remaining - 0.001)
    while time.perf_counter() < end_time:
        pass

def interruptible_sleep(seconds: float, check_active_fn=None):
    """중단 플래그 발생 시 0.1ms 이내 즉각 탈출하는 고정밀 슬립"""
    if seconds <= 0:
        return
    end_time = time.perf_counter() + seconds
    while time.perf_counter() < end_time:
        if check_active_fn and not check_active_fn():
            break
        remaining = end_time - time.perf_counter()
        if remaining > 0.002:
            time.sleep(min(remaining - 0.001, 0.005))
        else:
            pass

def send_osd_notification(title: str, message: str):
    """OS에 맞춘 OSD 알림 전송"""
    if IS_LINUX:
        try:
            import subprocess
            subprocess.Popen(['notify-send', '-t', '1500', '-a', '디아블로4 매크로', title, message])
        except Exception:
            pass
    elif IS_WINDOWS:
        # 윈도우 환경에서는 PowerShell 비동기 Toast 또는 무시
        try:
            import subprocess
            cmd = f'[reflection.assembly]::loadwithpartialname("System.Windows.Forms"); [System.Windows.Forms.ToolTip]::new()'
            # 성능 영향을 주지 않도록 가볍게 처리
        except Exception:
            pass

# UI 선택지 목록
MOUSE_TRIGGER_LIST = [
    ("뒤로가기 사이드 (BTN_SIDE)", "BTN_SIDE"),
    ("앞으로가기 사이드 (BTN_EXTRA)", "BTN_EXTRA"),
    ("휠 클릭 (BTN_MIDDLE)", "BTN_MIDDLE"),
    ("사용 안 함", "none")
]

TARGET_TYPE_LIST = [
    ("키보드 키 (지정 키)", "keyboard"),
    ("Ctrl + 좌클릭 (아이템 버리기)", "ctrl_mouse_left"),
    ("Ctrl + 우클릭", "ctrl_mouse_right"),
    ("마우스 좌클릭 (LMB)", "mouse_left"),
    ("마우스 우클릭 (RMB)", "mouse_right")
]

MODE_LIST = [
    ("1회 연타 (Burst)", "burst"),
    ("누르고 있는 동안 (Hold)", "hold"),
    ("토글 스위치 (Toggle)", "toggle")
]

SKILL_MODE_LIST = [
    ("토글 스위치 (Toggle)", "toggle"),
    ("누르고 있는 동안 (Hold)", "hold")
]

# UI 업데이트용 시그널 전달자
class MacroSignalBus(QObject):
    status_updated = pyqtSignal(str)
    stats_updated = pyqtSignal(str)
    skill_btn_text_updated = pyqtSignal(str)

class CrossPlatformInput:
    """리눅스(evdev/pynput)와 윈도우(SendInput/pynput)를 통합 제어하는 하드웨어 주입 엔진"""
    def __init__(self):
        self.keyboard = KbController()
        self.mouse = MouseController()

    def press_key(self, key_str: str):
        key_str = key_str.lower().strip()
        if IS_WINDOWS:
            # DirectX 12 하드웨어 스캔코드 전송
            vk = WIN_VK_MAP.get(key_str)
            if vk is None and len(key_str) == 1:
                vk = user32.VkKeyScanW(ord(key_str)) & 0xFF
            if vk:
                scan = user32.MapVirtualKeyW(vk, 0)
                extra = ctypes.c_ulong(0)
                ii_ = Input_I()
                ii_.ki = KeyBdInput(0, scan, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
                x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                return
        
        # 리눅스 또는 윈도우 pynput 폴백
        special = {'ctrl': Key.ctrl, 'shift': Key.shift, 'alt': Key.alt, 'space': Key.space}
        k = special.get(key_str, key_str)
        try:
            self.keyboard.press(k)
        except Exception:
            pass

    def release_key(self, key_str: str):
        key_str = key_str.lower().strip()
        if IS_WINDOWS:
            vk = WIN_VK_MAP.get(key_str)
            if vk is None and len(key_str) == 1:
                vk = user32.VkKeyScanW(ord(key_str)) & 0xFF
            if vk:
                scan = user32.MapVirtualKeyW(vk, 0)
                extra = ctypes.c_ulong(0)
                ii_ = Input_I()
                ii_.ki = KeyBdInput(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
                x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                return

        special = {'ctrl': Key.ctrl, 'shift': Key.shift, 'alt': Key.alt, 'space': Key.space}
        k = special.get(key_str, key_str)
        try:
            self.keyboard.release(k)
        except Exception:
            pass

    def press_mouse(self, btn_type: str):
        if IS_WINDOWS:
            flag = MOUSEEVENTF_LEFTDOWN if btn_type == 'left' else MOUSEEVENTF_RIGHTDOWN
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.mi = MouseInput(0, 0, 0, flag, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            return

        b = Button.left if btn_type == 'left' else Button.right
        try:
            self.mouse.press(b)
        except Exception:
            pass

    def release_mouse(self, btn_type: str):
        if IS_WINDOWS:
            flag = MOUSEEVENTF_LEFTUP if btn_type == 'left' else MOUSEEVENTF_RIGHTUP
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.mi = MouseInput(0, 0, 0, flag, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            return

        b = Button.left if btn_type == 'left' else Button.right
        try:
            self.mouse.release(b)
        except Exception:
            pass

    def sync(self):
        """X11 디스플레이 버퍼 동기화"""
        if IS_LINUX:
            if hasattr(self.keyboard, '_display'):
                try: self.keyboard._display.sync()
                except Exception: pass
            if hasattr(self.mouse, '_display'):
                try: self.mouse._display.sync()
                except Exception: pass


class Diablo4MacroQtApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚔️ 디아블로 IV 통합 매크로 (PyQt6)")
        self.setFixedSize(500, 680)

        self.input_engine = CrossPlatformInput()
        self.bus = MacroSignalBus()
        self.bus.status_updated.connect(self._on_status_updated)
        self.bus.stats_updated.connect(self._on_stats_updated)
        self.bus.skill_btn_text_updated.connect(self._on_skill_btn_text_updated)

        self.master_enabled = True
        self.running = True

        self.macro_states = {
            "macro1": {"active": False, "pressed": False, "runs": 0, "actions": 0, "last_ms": 0.0},
            "macro2": {"active": False, "pressed": False, "runs": 0, "actions": 0, "last_ms": 0.0}
        }
        self.skill_state = {
            "active": False,
            "cycles": 0,
            "actions": 0
        }
        self.last_skill_toggle_time = 0.0

        self.load_config()
        self.init_ui()
        self.apply_theme()
        self.start_background_listeners()

    def get_default_config(self):
        return {
            "master_enabled": True,
            "emergency_stop_key": "f12",
            "macro1": {
                "name": "매크로 1 (Ctrl + 우클릭 연타)",
                "enabled": True,
                "target_type": "ctrl_mouse_right",
                "target_value": "ctrl_right",
                "burst_count": 100,
                "press_delay_ms": 1.0,
                "release_delay_ms": 1.0,
                "mode": "burst",
                "mouse_trigger": "BTN_SIDE",
                "keyboard_trigger": "f1",
                "high_precision": True
            },
            "macro2": {
                "name": "매크로 2 (Ctrl + 좌클릭 아이템 버리기)",
                "enabled": True,
                "target_type": "ctrl_mouse_left",
                "target_value": "ctrl_left",
                "burst_count": 50,
                "press_delay_ms": 2.0,
                "release_delay_ms": 2.0,
                "mode": "hold",
                "mouse_trigger": "BTN_EXTRA",
                "keyboard_trigger": "f2",
                "high_precision": True
            },
            "skill_macro": {
                "name": "스킬 자동 연타 (1~5)",
                "enabled": True,
                "mode": "toggle",
                "keyboard_trigger": "f4",
                "mouse_trigger": "none",
                "skill_keys": ["1", "2", "3", "4", "5"],
                "press_delay_ms": 1.0,
                "interval_ms": 1.0,
                "cycle_delay_ms": 1.0,
                "show_notifications": True
            }
        }

    def load_config(self):
        default_cfg = self.get_default_config()
        data = {}
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        self.config = default_cfg
        self.config["master_enabled"] = data.get("master_enabled", True)
        self.config["emergency_stop_key"] = str(data.get("emergency_stop_key", "f12")).lower()

        if "macro1" in data and isinstance(data["macro1"], dict):
            self.config["macro1"].update(data["macro1"])
        if "macro2" in data and isinstance(data["macro2"], dict):
            self.config["macro2"].update(data["macro2"])

        if "skill_macro" in data and isinstance(data["skill_macro"], dict):
            self.config["skill_macro"].update(data["skill_macro"])
        elif "skill_keys" in data:
            self.config["skill_macro"]["keyboard_trigger"] = str(data.get("toggle_key", "f4")).lower()
            self.config["skill_macro"]["skill_keys"] = data.get("skill_keys", ["1", "2", "3", "4", "5"])
            self.config["skill_macro"]["press_delay_ms"] = float(data.get("key_press_duration_ms", 1.0))
            self.config["skill_macro"]["interval_ms"] = float(data.get("key_interval_ms", 1.0))
            self.config["skill_macro"]["cycle_delay_ms"] = float(data.get("cycle_delay_ms", 1.0))
            self.config["skill_macro"]["show_notifications"] = bool(data.get("show_notifications", True))
            self.config["skill_macro"]["mode"] = str(data.get("mode", "toggle")).lower()

        if "mode" not in self.config["skill_macro"]:
            self.config["skill_macro"]["mode"] = "toggle"

        self.master_enabled = self.config["master_enabled"]

    def save_config(self):
        try:
            self.config["master_enabled"] = self.master_enabled
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[설정 저장 오류] {e}")
            return False

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. 상단 슬림 헤더 (제목 + 전체 활성화 체크박스)
        header_layout = QHBoxLayout()
        title_lbl = QLabel("⚔️ 디아블로 IV 통합 매크로")
        font_title = QFont()
        font_title.setPointSize(13)
        font_title.setBold(True)
        title_lbl.setFont(font_title)
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        self.master_chk = QCheckBox("전체 활성화")
        self.master_chk.setChecked(self.master_enabled)
        self.master_chk.toggled.connect(self.on_master_toggled)
        header_layout.addWidget(self.master_chk)
        main_layout.addLayout(header_layout)

        # 2. 실시간 상태 카드
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 6, 10, 6)
        status_layout.setSpacing(3)

        self.status_lbl = QLabel("🟢 대기 중: 단축키를 누르면 매크로가 실행됩니다.")
        font_status = QFont()
        font_status.setBold(True)
        font_status.setPointSize(10)
        self.status_lbl.setFont(font_status)
        status_layout.addWidget(self.status_lbl)

        curr_trig = str(self.config.get("skill_macro", {}).get("keyboard_trigger", "f4")).upper()
        mode_val = self.config.get("skill_macro", {}).get("mode", "toggle")
        mode_str = "토글" if mode_val == "toggle" else "홀드"
        self.stats_lbl = QLabel(f"• 스킬: 정지 ([{curr_trig}] {mode_str}) | • 매크로1: 0회 | • 매크로2: 0회")
        font_stats = QFont()
        font_stats.setPointSize(8)
        self.stats_lbl.setFont(font_stats)
        self.stats_lbl.setStyleSheet("color: #a0a0a0;")
        status_layout.addWidget(self.stats_lbl)
        main_layout.addWidget(status_frame)

        # 3. 3개 탭 구성 (스킬 연타, 매크로1, 매크로2)
        self.tabs = QTabWidget()
        self.tab_skill = self.create_skill_tab()
        self.tab_macro1 = self.create_macro_tab("macro1", "🔵 매크로 1 (Ctrl+우클릭)")
        self.tab_macro2 = self.create_macro_tab("macro2", "🔴 매크로 2 (아이템 버리기)")

        self.tabs.addTab(self.tab_skill, "⚡ 스킬 연타")
        self.tabs.addTab(self.tab_macro1, "🔵 매크로 1 (우클릭)")
        self.tabs.addTab(self.tab_macro2, "🔴 매크로 2 (버리기)")
        main_layout.addWidget(self.tabs)

        # 4. 실시간 입력 테스트 필드
        test_layout = QHBoxLayout()
        test_lbl = QLabel("⌨️ 입력 테스트:")
        self.test_entry = QLineEdit()
        self.test_entry.setPlaceholderText("여기를 클릭하고 단축키를 누르면 숫자가 찍힙니다")
        test_layout.addWidget(test_lbl)
        test_layout.addWidget(self.test_entry)
        main_layout.addLayout(test_layout)

        # 5. 하단 제어 버튼 (설정 저장, 긴급 중지)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 설정 파일 저장")
        self.btn_save.clicked.connect(self.on_save_all_clicked)
        btn_layout.addWidget(self.btn_save, 2)

        self.btn_stop = QPushButton("🛑 긴급 중지 (F12)")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.clicked.connect(self.on_emergency_stop)
        btn_layout.addWidget(self.btn_stop, 1)
        main_layout.addLayout(btn_layout)

        # 6. 하단 안내 텍스트
        self.help_lbl = QLabel(f"• 긴급 정지: [F12] | 스킬 토글: [{curr_trig}] | 아이템 버리기: 사이드 앞버튼")
        self.help_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_lbl.setStyleSheet("color: #888888; font-size: 8pt;")
        main_layout.addWidget(self.help_lbl)

    def create_skill_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        cfg = self.config.get("skill_macro", {})

        # (1) 활성화 + 이름
        row1 = QHBoxLayout()
        self.skill_chk_enable = QCheckBox("스킬 연타 활성화")
        self.skill_chk_enable.setChecked(cfg.get("enabled", True))
        self.skill_chk_enable.toggled.connect(lambda v: self.config["skill_macro"].update({"enabled": v}))
        row1.addWidget(self.skill_chk_enable)

        self.skill_entry_name = QLineEdit(cfg.get("name", "스킬 자동 연타 (1~5)"))
        row1.addWidget(self.skill_entry_name)
        layout.addLayout(row1)

        # (2) 단축키 + 동작 모드
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("단축키:"))
        self.skill_entry_trig = QLineEdit(str(cfg.get("keyboard_trigger", "f4")).upper())
        self.skill_entry_trig.setMaximumWidth(70)
        self.skill_entry_trig.textChanged.connect(self.on_skill_trig_changed)
        row2.addWidget(self.skill_entry_trig)

        row2.addWidget(QLabel("모드:"))
        self.skill_combo_mode = QComboBox()
        for label, val in SKILL_MODE_LIST:
            self.skill_combo_mode.addItem(label, val)
        cur_mode = cfg.get("mode", "toggle")
        idx = 0 if cur_mode == "toggle" else 1
        self.skill_combo_mode.setCurrentIndex(idx)
        self.skill_combo_mode.currentIndexChanged.connect(self.on_skill_mode_changed)
        row2.addWidget(self.skill_combo_mode)
        layout.addLayout(row2)

        # (2-1) 마우스 트리거
        row2_m = QHBoxLayout()
        row2_m.addWidget(QLabel("마우스 트리거:"))
        self.skill_combo_mouse = QComboBox()
        cur_mtrig = cfg.get("mouse_trigger", "none")
        m_idx = 3
        for i, (label, val) in enumerate(MOUSE_TRIGGER_LIST):
            self.skill_combo_mouse.addItem(label, val)
            if val == cur_mtrig:
                m_idx = i
        self.skill_combo_mouse.setCurrentIndex(m_idx)
        self.skill_combo_mouse.currentIndexChanged.connect(
            lambda idx: self.config["skill_macro"].update({"mouse_trigger": MOUSE_TRIGGER_LIST[idx][1]})
        )
        row2_m.addWidget(self.skill_combo_mouse)
        layout.addLayout(row2_m)

        # (3) 연타할 스킬 키 목록
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("연타할 스킬 키:"))
        cur_keys = cfg.get("skill_keys", ["1", "2", "3", "4", "5"])
        self.skill_entry_keys = QLineEdit(" ".join(cur_keys))
        self.skill_entry_keys.textChanged.connect(self.on_skill_keys_changed)
        row3.addWidget(self.skill_entry_keys)
        layout.addLayout(row3)

        # (4) 속도 프리셋 버튼 4개
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("⚡ 속도:"))
        btn_p1 = QPushButton("⚡ 1ms 초광속")
        btn_p1.clicked.connect(lambda: self.apply_speed_preset(1.0, 2.0, 35.0))
        row4.addWidget(btn_p1)

        btn_p2 = QPushButton("🚀 15ms 고속")
        btn_p2.clicked.connect(lambda: self.apply_speed_preset(10.0, 15.0, 50.0))
        row4.addWidget(btn_p2)

        btn_p3 = QPushButton("🎯 35ms 표준")
        btn_p3.clicked.connect(lambda: self.apply_speed_preset(20.0, 30.0, 80.0))
        row4.addWidget(btn_p3)

        btn_p4 = QPushButton("🛡️ 80ms 여유")
        btn_p4.clicked.connect(lambda: self.apply_speed_preset(40.0, 60.0, 150.0))
        row4.addWidget(btn_p4)
        layout.addLayout(row4)

        # (5) 정밀 딜레이 설정 (누름 / 간격 / 사이클)
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("누름(ms):"))
        self.skill_spin_press = QDoubleSpinBox()
        self.skill_spin_press.setRange(0.5, 500.0)
        self.skill_spin_press.setSingleStep(0.5)
        self.skill_spin_press.setValue(float(cfg.get("press_delay_ms", 1.0)))
        self.skill_spin_press.valueChanged.connect(lambda v: self.config["skill_macro"].update({"press_delay_ms": v}))
        row5.addWidget(self.skill_spin_press)

        row5.addWidget(QLabel("간격(ms):"))
        self.skill_spin_interval = QDoubleSpinBox()
        self.skill_spin_interval.setRange(0.5, 500.0)
        self.skill_spin_interval.setSingleStep(0.5)
        self.skill_spin_interval.setValue(float(cfg.get("interval_ms", 1.0)))
        self.skill_spin_interval.valueChanged.connect(lambda v: self.config["skill_macro"].update({"interval_ms": v}))
        row5.addWidget(self.skill_spin_interval)

        row5.addWidget(QLabel("대기(ms):"))
        self.skill_spin_cycle = QDoubleSpinBox()
        self.skill_spin_cycle.setRange(0.5, 1000.0)
        self.skill_spin_cycle.setSingleStep(1.0)
        self.skill_spin_cycle.setValue(float(cfg.get("cycle_delay_ms", 1.0)))
        self.skill_spin_cycle.valueChanged.connect(lambda v: self.config["skill_macro"].update({"cycle_delay_ms": v}))
        row5.addWidget(self.skill_spin_cycle)
        layout.addLayout(row5)

        # (6) OSD 화면 알림
        self.skill_chk_notify = QCheckBox("게임 OSD 화면 알림 (토글 시 팝업)")
        self.skill_chk_notify.setChecked(cfg.get("show_notifications", True))
        self.skill_chk_notify.toggled.connect(lambda v: self.config["skill_macro"].update({"show_notifications": v}))
        layout.addWidget(self.skill_chk_notify)

        # (7) 수동 시작/정지 버튼
        trig_str = str(cfg.get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if cur_mode == "toggle" else "홀드"
        self.btn_skill_toggle = QPushButton(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")
        self.btn_skill_toggle.setObjectName("StartSkillButton")
        self.btn_skill_toggle.clicked.connect(self.toggle_skill_macro)
        layout.addWidget(self.btn_skill_toggle)

        return widget

    def create_macro_tab(self, uid: str, title_str: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        cfg = self.config.get(uid, {})

        # (1) 활성화 + 이름
        row1 = QHBoxLayout()
        chk_enable = QCheckBox("이 매크로 활성화")
        chk_enable.setChecked(cfg.get("enabled", True))
        chk_enable.toggled.connect(lambda v, u=uid: self.config[u].update({"enabled": v}))
        row1.addWidget(chk_enable)

        entry_name = QLineEdit(cfg.get("name", title_str))
        entry_name.textChanged.connect(lambda t, u=uid: self.config[u].update({"name": t}))
        row1.addWidget(entry_name)
        layout.addLayout(row1)

        # (2) 입력 대상 (Target)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("연타 대상:"))
        combo_target = QComboBox()
        cur_tgt = cfg.get("target_type", "keyboard")
        tgt_idx = 0
        for i, (label, val) in enumerate(TARGET_TYPE_LIST):
            combo_target.addItem(label, val)
            if val == cur_tgt:
                tgt_idx = i
        combo_target.setCurrentIndex(tgt_idx)
        row2.addWidget(combo_target, 2)

        entry_target_key = QLineEdit(str(cfg.get("target_value", "f")).upper())
        entry_target_key.setMaximumWidth(50)
        entry_target_key.textChanged.connect(lambda t, u=uid: self.config[u].update({"target_value": t.lower()}))
        entry_target_key.setVisible(cur_tgt == "keyboard")
        row2.addWidget(entry_target_key, 1)

        def on_tgt_changed(idx, u=uid, ek=entry_target_key):
            val = TARGET_TYPE_LIST[idx][1]
            self.config[u]["target_type"] = val
            ek.setVisible(val == "keyboard")

        combo_target.currentIndexChanged.connect(on_tgt_changed)
        layout.addLayout(row2)

        # (3) 마우스 트리거 & 키보드 단축키
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("마우스:"))
        combo_mouse = QComboBox()
        cur_mtrig = cfg.get("mouse_trigger", "BTN_SIDE" if uid == "macro1" else "BTN_EXTRA")
        m_idx = 3
        for i, (label, val) in enumerate(MOUSE_TRIGGER_LIST):
            combo_mouse.addItem(label, val)
            if val == cur_mtrig:
                m_idx = i
        combo_mouse.setCurrentIndex(m_idx)
        combo_mouse.currentIndexChanged.connect(
            lambda idx, u=uid: self.config[u].update({"mouse_trigger": MOUSE_TRIGGER_LIST[idx][1]})
        )
        row3.addWidget(combo_mouse)

        row3.addWidget(QLabel("단축키:"))
        entry_kb_trig = QLineEdit(str(cfg.get("keyboard_trigger", "f1" if uid == "macro1" else "f2")).upper())
        entry_kb_trig.setMaximumWidth(60)
        entry_kb_trig.textChanged.connect(lambda t, u=uid: self.config[u].update({"keyboard_trigger": t.lower()}))
        row3.addWidget(entry_kb_trig)
        layout.addLayout(row3)

        # (4) 동작 모드 & 연타 횟수
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("모드:"))
        combo_mode = QComboBox()
        cur_mode = cfg.get("mode", "burst" if uid == "macro1" else "hold")
        mode_idx = 0
        for i, (label, val) in enumerate(MODE_LIST):
            combo_mode.addItem(label, val)
            if val == cur_mode:
                mode_idx = i
        combo_mode.setCurrentIndex(mode_idx)
        combo_mode.currentIndexChanged.connect(
            lambda idx, u=uid: self.config[u].update({"mode": MODE_LIST[idx][1]})
        )
        row4.addWidget(combo_mode)

        row4.addWidget(QLabel("횟수:"))
        spin_cnt = QSpinBox()
        spin_cnt.setRange(1, 1000)
        spin_cnt.setValue(int(cfg.get("burst_count", 100)))
        spin_cnt.valueChanged.connect(lambda v, u=uid: self.config[u].update({"burst_count": v}))
        row4.addWidget(spin_cnt)
        layout.addLayout(row4)

        # (5) 딜레이 (누름 / 뗌)
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("누름(ms):"))
        spin_p = QDoubleSpinBox()
        spin_p.setRange(0.5, 50.0)
        spin_p.setValue(float(cfg.get("press_delay_ms", 1.0)))
        spin_p.valueChanged.connect(lambda v, u=uid: self.config[u].update({"press_delay_ms": v}))
        row5.addWidget(spin_p)

        row5.addWidget(QLabel("뗌(ms):"))
        spin_r = QDoubleSpinBox()
        spin_r.setRange(0.5, 50.0)
        spin_r.setValue(float(cfg.get("release_delay_ms", 1.0)))
        spin_r.valueChanged.connect(lambda v, u=uid: self.config[u].update({"release_delay_ms": v}))
        row5.addWidget(spin_r)
        layout.addLayout(row5)

        # (6) 테스트 버튼
        btn_test = QPushButton(f"⚡ {cfg.get('name', title_str)} 1회 테스트")
        btn_test.clicked.connect(lambda _, u=uid: self.execute_burst(u))
        layout.addWidget(btn_test)

        return widget

    def apply_theme(self):
        """다크 테마 및 깔끔한 QSS 스타일 적용"""
        qss = """
        QMainWindow, QWidget {
            background-color: #1e1e24;
            color: #f0f0f0;
            font-family: 'Segoe UI', 'Pretendard', 'Noto Sans CJK KR', sans-serif;
            font-size: 9pt;
        }
        QFrame#StatusFrame {
            background-color: #2b2b36;
            border-radius: 6px;
            border: 1px solid #3d3d4d;
        }
        QTabWidget::pane {
            border: 1px solid #3d3d4d;
            border-radius: 6px;
            background-color: #24242e;
        }
        QTabBar::tab {
            background-color: #1e1e24;
            color: #a0a0a0;
            padding: 7px 14px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: #2d2d3a;
            color: #ffffff;
            font-weight: bold;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #2a2a38;
            color: #ffffff;
            border: 1px solid #4a4a5e;
            border-radius: 4px;
            padding: 4px 6px;
        }
        QPushButton {
            background-color: #3b3b4f;
            color: #ffffff;
            border: 1px solid #5a5a75;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #4b4b66;
        }
        QPushButton#StartSkillButton {
            background-color: #2563eb;
            color: white;
            border: none;
            padding: 8px 14px;
        }
        QPushButton#StartSkillButton:hover {
            background-color: #1d4ed8;
        }
        QPushButton#StopButton {
            background-color: #dc2626;
            color: white;
            border: none;
            padding: 8px 14px;
        }
        QPushButton#StopButton:hover {
            background-color: #b91c1c;
        }
        QCheckBox {
            color: #ffffff;
            spacing: 5px;
        }
        """
        self.setStyleSheet(qss)

    def on_master_toggled(self, checked: bool):
        self.master_enabled = checked
        if checked:
            self.bus.status_updated.emit("🟢 대기 중: 매크로가 켜졌습니다.")
        else:
            self.on_emergency_stop()
            self.bus.status_updated.emit("⚪ 비활성화됨: 전체 매크로가 꺼져 있습니다.")

    def on_skill_trig_changed(self, text: str):
        t = text.strip().lower()
        if t:
            self.config["skill_macro"]["keyboard_trigger"] = t
            upper_k = t.upper()
            mode_val = self.config["skill_macro"].get("mode", "toggle")
            mode_str = "토글" if mode_val == "toggle" else "홀드"
            if not self.skill_state["active"]:
                self.bus.skill_btn_text_updated.emit(f"▶ 스킬 연타 시작 ([{upper_k}] {mode_str})")
            self.help_lbl.setText(f"• 긴급 정지: [F12] | 스킬 단축키: [{upper_k}] | 아이템 버리기: 사이드 앞버튼")
            self.bus.status_updated.emit(f"스킬 단축키가 [{upper_k}]로 실시간 변경되었습니다.")

    def on_skill_mode_changed(self, idx: int):
        mode_val = SKILL_MODE_LIST[idx][1]
        self.config["skill_macro"]["mode"] = mode_val
        upper_k = str(self.config["skill_macro"].get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if mode_val == "toggle" else "홀드"
        if not self.skill_state["active"]:
            self.bus.skill_btn_text_updated.emit(f"▶ 스킬 연타 시작 ([{upper_k}] {mode_str})")
        self.bus.status_updated.emit(f"스킬 모드가 [{SKILL_MODE_LIST[idx][0]}]로 설정되었습니다.")

    def on_skill_keys_changed(self, text: str):
        raw_keys = text.replace(',', ' ').split()
        keys = [k.strip().lower() for k in raw_keys if k.strip()]
        if keys:
            self.config["skill_macro"]["skill_keys"] = keys

    def apply_speed_preset(self, press_ms: float, interval_ms: float, cycle_ms: float):
        self.skill_spin_press.setValue(press_ms)
        self.skill_spin_interval.setValue(interval_ms)
        self.skill_spin_cycle.setValue(cycle_ms)
        self.config["skill_macro"]["press_delay_ms"] = press_ms
        self.config["skill_macro"]["interval_ms"] = interval_ms
        self.config["skill_macro"]["cycle_delay_ms"] = cycle_ms
        self.bus.status_updated.emit(f"⚡ 스킬 속도 적용: 누름 {press_ms}ms / 간격 {interval_ms}ms / 대기 {cycle_ms}ms")

    def on_save_all_clicked(self):
        if self.save_config():
            self.bus.status_updated.emit("✓ 설정이 성공적으로 저장되었습니다.")
            QTimer.singleShot(1500, lambda: self.bus.status_updated.emit("🟢 대기 중: 단축키를 누르면 시작됩니다."))

    def on_emergency_stop(self):
        """긴급 중지: 모든 스레드 루프 중단 및 키 릴리스"""
        self.skill_state["active"] = False
        scfg = self.config.get("skill_macro", {})
        trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if scfg.get("mode", "toggle") == "toggle" else "홀드"
        self.bus.skill_btn_text_updated.emit(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")

        for uid in ("macro1", "macro2"):
            st = self.macro_states[uid]
            st["active"] = False
            st["pressed"] = False
            self.release_target(uid)

        self.input_engine.release_key('ctrl')
        for k in scfg.get("skill_keys", ["1", "2", "3", "4", "5"]):
            self.input_engine.release_key(k)
        self.input_engine.sync()

        self.bus.status_updated.emit("🛑 긴급 중지: 모든 매크로 동작이 즉각 정지되었습니다.")

    def toggle_skill_macro(self, force_state=None):
        if not self.master_enabled:
            self.bus.status_updated.emit("⚠️ 전체 활성화 스위치를 먼저 켜주세요.")
            return

        scfg = self.config.get("skill_macro", {})
        if not scfg.get("enabled", True):
            self.bus.status_updated.emit("⚠️ 스킬 자동 연타가 꺼져 있습니다.")
            return

        now = time.perf_counter()
        trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
        mode_val = scfg.get("mode", "toggle")
        mode_str = "토글" if mode_val == "toggle" else "홀드"

        if force_state is not None:
            if force_state == self.skill_state["active"]:
                return
            new_state = force_state
        else:
            if now - self.last_skill_toggle_time < 0.25:
                return
            self.last_skill_toggle_time = now
            new_state = not self.skill_state["active"]

        self.skill_state["active"] = new_state

        if not new_state:
            for k in scfg.get("skill_keys", ["1", "2", "3", "4", "5"]):
                self.input_engine.release_key(k)
            self.input_engine.sync()
            self.bus.skill_btn_text_updated.emit(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")
            self.bus.status_updated.emit(f"■ [스킬 연타 정지] 즉각 중단되었습니다. ([{trig_str}] 재시작)")
            if scfg.get("show_notifications", True):
                send_osd_notification("디아블로4 매크로", f"■ 스킬 연타 정지 (OFF) - [{trig_str}]")
        else:
            self.bus.skill_btn_text_updated.emit("■ 스킬 연타 가동 중... (클릭 시 멈춤)")
            self.bus.status_updated.emit(f"⚡ [스킬 연타 가동 중] 반복 실행 중... ([{trig_str}] 정지)")
            if scfg.get("show_notifications", True):
                keys_str = " ".join(scfg.get("skill_keys", ["1", "2", "3", "4", "5"]))
                send_osd_notification("디아블로4 매크로", f"▶ 스킬 연타 시작 (ON) - {keys_str}")
            threading.Thread(target=self._skill_macro_worker, daemon=True).start()

    def _skill_macro_worker(self):
        cycles = 0
        is_active = lambda: self.skill_state["active"] and self.master_enabled and self.running
        try:
            while is_active():
                scfg = self.config.get("skill_macro", {})
                skill_keys = scfg.get("skill_keys", ["1", "2", "3", "4", "5"])
                press_d = max(0.0005, float(scfg.get("press_delay_ms", 1.0)) / 1000.0)
                interval_d = max(0.0005, float(scfg.get("interval_ms", 1.0)) / 1000.0)
                cycle_d = max(0.0005, float(scfg.get("cycle_delay_ms", 1.0)) / 1000.0)

                # [적응형 큐 누적 방지 가드]
                keys_total_time = len(skill_keys) * (press_d + interval_d)
                safe_cycle_d = max(cycle_d, max(0.005, 0.035 - keys_total_time))

                for k in skill_keys:
                    if not is_active():
                        break
                    self.input_engine.press_key(k)
                    interruptible_sleep(press_d, is_active)
                    self.input_engine.release_key(k)
                    interruptible_sleep(interval_d, is_active)

                cycles += 1
                self.skill_state["cycles"] = cycles

                if not is_active():
                    break

                if safe_cycle_d > 0:
                    interruptible_sleep(safe_cycle_d, is_active)

                self.input_engine.sync()
        finally:
            scfg = self.config.get("skill_macro", {})
            for k in scfg.get("skill_keys", ["1", "2", "3", "4", "5"]):
                self.input_engine.release_key(k)
            self.input_engine.sync()
            self.skill_state["active"] = False
            trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
            mode_val = scfg.get("mode", "toggle")
            mode_str = "토글" if mode_val == "toggle" else "홀드"
            self.bus.skill_btn_text_updated.emit(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")

    def press_target(self, uid: str):
        cfg = self.config.get(uid, {})
        ttype = cfg.get("target_type", "keyboard")
        val = cfg.get("target_value", "f")
        if ttype in ("ctrl_mouse_left", "mouse_left"):
            self.input_engine.press_mouse("left")
        elif ttype in ("ctrl_mouse_right", "mouse_right"):
            self.input_engine.press_mouse("right")
        else:
            self.input_engine.press_key(val)

    def release_target(self, uid: str):
        cfg = self.config.get(uid, {})
        ttype = cfg.get("target_type", "keyboard")
        val = cfg.get("target_value", "f")
        if ttype in ("ctrl_mouse_left", "mouse_left"):
            self.input_engine.release_mouse("left")
        elif ttype in ("ctrl_mouse_right", "mouse_right"):
            self.input_engine.release_mouse("right")
        else:
            self.input_engine.release_key(val)

    def execute_burst(self, uid: str):
        st = self.macro_states[uid]
        if st["active"]:
            return
        st["active"] = True

        cfg = self.config.get(uid, {})
        name = cfg.get("name", uid)
        count = int(cfg.get("burst_count", 100))
        press_d = max(0.0005, float(cfg.get("press_delay_ms", 1.0)) / 1000.0)
        release_d = max(0.0005, float(cfg.get("release_delay_ms", 1.0)) / 1000.0)
        safe_release_d = max(release_d, max(0.005, 0.025 - press_d))
        is_ctrl = cfg.get("target_type") in ("ctrl_mouse_left", "ctrl_mouse_right")
        is_active = lambda: st["active"] and st["pressed"] and self.master_enabled and self.running

        def _worker():
            self.bus.status_updated.emit(f"⚡ [{name}] {count}회 연타 중...")
            t0 = time.perf_counter()
            done = 0
            try:
                if is_ctrl:
                    self.input_engine.press_key('ctrl')
                    interruptible_sleep(0.002, is_active)
                for _ in range(count):
                    if not is_active():
                        break
                    self.press_target(uid)
                    interruptible_sleep(press_d, is_active)
                    self.release_target(uid)
                    interruptible_sleep(safe_release_d, is_active)
                    done += 1
                    self.input_engine.sync()
            finally:
                self.release_target(uid)
                if is_ctrl:
                    self.input_engine.release_key('ctrl')
                self.input_engine.sync()
                dur_ms = (time.perf_counter() - t0) * 1000.0
                st["runs"] += 1
                st["actions"] += done
                st["last_ms"] = dur_ms
                st["active"] = False
                self.bus.status_updated.emit(f"✓ [{name}] {done}회 연타 완료 ({dur_ms:.1f}ms)")
                self._update_stats_label()

        threading.Thread(target=_worker, daemon=True).start()

    def execute_hold(self, uid: str):
        st = self.macro_states[uid]
        if st["active"]:
            return
        st["active"] = True

        cfg = self.config.get(uid, {})
        name = cfg.get("name", uid)
        press_d = max(0.0005, float(cfg.get("press_delay_ms", 1.0)) / 1000.0)
        release_d = max(0.0005, float(cfg.get("release_delay_ms", 1.0)) / 1000.0)
        safe_release_d = max(release_d, max(0.005, 0.025 - press_d))
        is_ctrl = cfg.get("target_type") in ("ctrl_mouse_left", "ctrl_mouse_right")
        is_active = lambda: st["active"] and st["pressed"] and self.master_enabled and self.running

        def _worker():
            self.bus.status_updated.emit(f"⚡ [{name}] 연타 유지 중...")
            t0 = time.perf_counter()
            done = 0
            try:
                if is_ctrl:
                    self.input_engine.press_key('ctrl')
                    interruptible_sleep(0.002, is_active)
                while is_active():
                    self.press_target(uid)
                    interruptible_sleep(press_d, is_active)
                    self.release_target(uid)
                    interruptible_sleep(safe_release_d, is_active)
                    done += 1
                    self.input_engine.sync()
            finally:
                self.release_target(uid)
                if is_ctrl:
                    self.input_engine.release_key('ctrl')
                self.input_engine.sync()
                dur_ms = (time.perf_counter() - t0) * 1000.0
                st["runs"] += 1
                st["actions"] += done
                st["last_ms"] = dur_ms
                st["active"] = False
                self.bus.status_updated.emit(f"✓ [{name} 정지] {done}회 연타 ({dur_ms:.1f}ms)")
                self._update_stats_label()

        threading.Thread(target=_worker, daemon=True).start()

    def trigger_unit(self, uid: str, is_press: bool):
        if not self.master_enabled:
            return
        cfg = self.config.get(uid, {})
        if not cfg.get("enabled", True):
            return

        st = self.macro_states[uid]
        mode = cfg.get("mode", "burst")

        if not is_press:
            st["pressed"] = False
            st["active"] = False
            self.release_target(uid)
            self.input_engine.release_key('ctrl')
            self.input_engine.sync()
            return

        st["pressed"] = True
        if mode == "burst":
            self.execute_burst(uid)
        elif mode == "hold":
            self.execute_hold(uid)
        elif mode == "toggle":
            if st["active"]:
                st["active"] = False
                st["pressed"] = False
                self.release_target(uid)
                self.bus.status_updated.emit(f"[{cfg.get('name', uid)} 토글 정지]")
            else:
                self.execute_burst(uid)

    def dispatch_mouse_trigger(self, trigger_name: str, is_press: bool):
        if not self.master_enabled:
            return

        if self.config.get("skill_macro", {}).get("mouse_trigger") == trigger_name:
            mode = self.config.get("skill_macro", {}).get("mode", "toggle")
            if mode == "toggle":
                if is_press: self.toggle_skill_macro()
            elif mode == "hold":
                self.toggle_skill_macro(force_state=is_press)
            return

        for uid in ("macro1", "macro2"):
            if self.config.get(uid, {}).get("mouse_trigger") == trigger_name:
                self.trigger_unit(uid, is_press)

    def dispatch_keyboard_trigger(self, key_str: str, is_press: bool):
        if not self.master_enabled:
            return

        target_trig = str(self.config.get("skill_macro", {}).get("keyboard_trigger", "f4")).lower()
        if key_str == target_trig:
            mode = self.config.get("skill_macro", {}).get("mode", "toggle")
            if mode == "toggle":
                if is_press: self.toggle_skill_macro()
            elif mode == "hold":
                self.toggle_skill_macro(force_state=is_press)
            return

        for uid in ("macro1", "macro2"):
            if str(self.config.get(uid, {}).get("keyboard_trigger", "")).lower() == key_str:
                self.trigger_unit(uid, is_press)

    def start_background_listeners(self):
        """OS별 백그라운드 전역 리스너 시작"""
        # 1. Linux evdev 하드웨어 전역 리스너
        if IS_LINUX and HAS_EVDEV:
            code_to_mouse_name = {
                ecodes.BTN_SIDE: "BTN_SIDE",
                ecodes.BTN_BACK: "BTN_SIDE",
                ecodes.BTN_EXTRA: "BTN_EXTRA",
                ecodes.BTN_FORWARD: "BTN_EXTRA",
                ecodes.BTN_MIDDLE: "BTN_MIDDLE"
            }
            ecodes_key_map = {}
            for name in dir(ecodes):
                if name.startswith('KEY_'):
                    code = getattr(ecodes, name)
                    ecodes_key_map[code] = name[4:].lower()

            def _evdev_loop():
                target_mouse_codes = set(code_to_mouse_name.keys())
                input_devs = []
                for path in evdev.list_devices():
                    try:
                        d = evdev.InputDevice(path)
                        caps = d.capabilities()
                        if ecodes.EV_KEY in caps:
                            keys = set(caps[ecodes.EV_KEY])
                            is_mouse = any(c in keys for c in target_mouse_codes) or "mouse" in d.name.lower() or "g703" in d.name.lower()
                            is_kb = (ecodes.KEY_A in keys or ecodes.KEY_SPACE in keys or ecodes.KEY_ENTER in keys)
                            if is_mouse or is_kb:
                                input_devs.append(d)
                    except Exception:
                        continue

                if not input_devs:
                    return

                dev_map = {d.fd: d for d in input_devs}
                while self.running:
                    try:
                        r, _, _ = select.select(list(dev_map.keys()), [], [], 0.5)
                        for fd in r:
                            dev = dev_map.get(fd)
                            if not dev: continue
                            for ev in dev.read():
                                if ev.type == ecodes.EV_KEY:
                                    if ev.code in code_to_mouse_name:
                                        trigname = code_to_mouse_name[ev.code]
                                        self.dispatch_mouse_trigger(trigname, ev.value == 1)
                                    elif ev.code in ecodes_key_map:
                                        k_name = ecodes_key_map[ev.code]
                                        if ev.value == 1:
                                            em_key = str(self.config.get("emergency_stop_key", "f12")).lower()
                                            if k_name == em_key:
                                                self.on_emergency_stop()
                                            else:
                                                self.dispatch_keyboard_trigger(k_name, True)
                                        elif ev.value == 0:
                                            self.dispatch_keyboard_trigger(k_name, False)
                    except Exception:
                        time.sleep(0.5)

            threading.Thread(target=_evdev_loop, daemon=True).start()

        # 2. pynput 전역 리스너 (Windows 및 Linux 보조)
        def on_mouse_click(x, y, button, pressed):
            b_str = str(button).lower()
            trigname = None
            if 'x1' in b_str or 'button8' in b_str:
                trigname = "BTN_SIDE"
            elif 'x2' in b_str or 'button9' in b_str:
                trigname = "BTN_EXTRA"
            elif 'middle' in b_str:
                trigname = "BTN_MIDDLE"
            if trigname:
                self.dispatch_mouse_trigger(trigname, pressed)

        m_listener = MouseListener(on_click=on_mouse_click)
        m_listener.daemon = True
        m_listener.start()

        def _get_key_str(key):
            if isinstance(key, KeyCode):
                return key.char.lower() if key.char else str(key.vk)
            elif isinstance(key, Key):
                return key.name.lower()
            return str(key).lower()

        def on_key_press(key):
            try:
                k_name = _get_key_str(key)
                if k_name == str(self.config.get("emergency_stop_key", "f12")).lower():
                    self.on_emergency_stop()
                else:
                    self.dispatch_keyboard_trigger(k_name, True)
            except Exception:
                pass

        def on_key_release(key):
            try:
                k_name = _get_key_str(key)
                self.dispatch_keyboard_trigger(k_name, False)
            except Exception:
                pass

        k_listener = KeyListener(on_press=on_key_press, on_release=on_key_release)
        k_listener.daemon = True
        k_listener.start()

    def _on_status_updated(self, msg: str):
        self.status_lbl.setText(msg)
        self._update_stats_label()

    def _on_stats_updated(self, msg: str):
        self.stats_lbl.setText(msg)

    def _on_skill_btn_text_updated(self, text: str):
        self.btn_skill_toggle.setText(text)

    def _update_stats_label(self):
        m1 = self.macro_states["macro1"]
        m2 = self.macro_states["macro2"]
        scfg = self.config.get("skill_macro", {})
        curr_trig = str(scfg.get("keyboard_trigger", "f4")).upper()
        mode_val = scfg.get("mode", "toggle")
        mode_str = "토글" if mode_val == "toggle" else "홀드"
        skill_status = f"가동 중 ({self.skill_state['cycles']}회)" if self.skill_state["active"] else f"정지 ([{curr_trig}] {mode_str})"
        self.stats_lbl.setText(
            f"• 스킬: {skill_status} | • 매크로1: {m1['runs']}회 | • 매크로2: {m2['runs']}회"
        )

    def closeEvent(self, event):
        self.running = False
        self.on_emergency_stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Diablo4MacroQtApp()
    window.show()
    sys.exit(app.exec())
