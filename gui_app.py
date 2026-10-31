#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
디아블로4 리눅스 전용 통합 게이밍 매크로 GUI 애플리케이션 (검증 및 실시간 반영 강화판)
- wtype (Wayland virtual-keyboard-v1) + pynput (X11 XTest) 하이브리드 듀얼 주입
- evdev 기반 커널 레벨 하드웨어 전역 감지 (어떤 창에 포커스가 있든 100% 감지)
- 단축키 및 스킬 키 변경 시 '설정 저장' 버튼 없이도 타이핑 즉시 실시간 자동 동기화
- 매크로 1: 마우스 사이드(뒤로가기) 버튼 또는 키보드 단축키 감지 시 Ctrl+우클릭 / F키 초고속 연타
- 매크로 2: 마우스 사이드(앞으로가기) 버튼 또는 키보드 단축키 감지 시 Ctrl+좌클릭(아이템 버리기) 연타
- 매크로 3 (스킬 자동 연타): 토글 단축키 감지 시 스킬 키(1~5 등)를 무한 순차 연타
"""

import os
import sys
import time
import json
import shutil
import threading
import select
import subprocess
from pathlib import Path

# GTK4 로드
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio, Pango

# 입력 라이브러리
try:
    import evdev
    from evdev import ecodes
except ImportError:
    print("[오류] evdev 모듈이 필요합니다.")
    sys.exit(1)

try:
    from pynput.keyboard import Controller as KbController, Key, KeyCode, Listener as KeyListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("[오류] pynput 모듈이 필요합니다.")
    sys.exit(1)

if getattr(sys, 'frozen', False):
    _app_dir = Path(sys.executable).resolve().parent
    CONFIG_PATH = _app_dir / "config.json"
else:
    CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

def get_wtype_path():
    """Wayland 가상 키보드 주입기 wtype 바이너리 경로 탐색"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            p = Path(sys._MEIPASS) / "wtype"
            if p.exists() and os.access(p, os.X_OK):
                return str(p)
        p = Path(sys.executable).resolve().parent / "wtype"
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    
    local_p = Path(__file__).resolve().parent / "wtype"
    if local_p.exists() and os.access(local_p, os.X_OK):
        return str(local_p)
    
    user_p = Path.home() / ".local" / "bin" / "wtype"
    if user_p.exists() and os.access(user_p, os.X_OK):
        return str(user_p)
    
    w = shutil.which("wtype")
    if w:
        return w
    
    return None

def precise_sleep(seconds: float):
    """Sub-millisecond 정밀도를 보장하는 하이브리드 고정밀 슬립"""
    if seconds <= 0:
        return
    end_time = time.perf_counter() + seconds
    remaining = end_time - time.perf_counter()
    if remaining > 0.0015:
        time.sleep(remaining - 0.001)
    while time.perf_counter() < end_time:
        pass

def interruptible_sleep(seconds: float, check_active_fn=None):
    """Sub-millisecond 정밀도를 보장하되 중단 플래그 발생 시 0.1ms 이내 즉각 탈출하는 고정밀 슬립"""
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
    """게임 중 화면 우측 상단 OSD 알림 전송"""
    try:
        subprocess.Popen(['notify-send', '-t', '1500', '-a', '디아블로4 매크로', title, message])
    except Exception:
        pass

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

class MacroTabWidgets:
    """각 마우스/키보드 매크로 탭의 UI 컨트롤 위젯 홀더"""
    def __init__(self):
        self.enable_check = None
        self.entry_name = None
        self.dropdown_target = None
        self.entry_target_key = None
        self.key_box = None
        self.dropdown_mouse_trigger = None
        self.entry_kb_trigger = None
        self.dropdown_mode = None
        self.spin_count = None
        self.spin_press = None
        self.spin_release = None

class SkillMacroTabWidgets:
    """스킬 자동 연타 탭 전용 UI 컨트롤 위젯 홀더"""
    def __init__(self):
        self.enable_check = None
        self.entry_name = None
        self.entry_kb_trigger = None
        self.dropdown_mouse_trigger = None
        self.dropdown_mode = None
        self.entry_skill_keys = None
        self.spin_press = None
        self.spin_interval = None
        self.spin_cycle = None
        self.check_notify = None
        self.btn_toggle_action = None

class MacroApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.diablo4.macro",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.keyboard = KbController()
        self.mouse = MouseController()
        self.master_enabled = True
        self.running = True

        # 상태 관리
        self.macro_states = {
            "macro1": {"active": False, "pressed": False, "runs": 0, "actions": 0, "last_ms": 0.0},
            "macro2": {"active": False, "pressed": False, "runs": 0, "actions": 0, "last_ms": 0.0}
        }
        self.skill_state = {
            "active": False,
            "cycles": 0,
            "actions": 0
        }

        self.tab_widgets = {
            "macro1": MacroTabWidgets(),
            "macro2": MacroTabWidgets()
        }
        self.skill_tab_widgets = SkillMacroTabWidgets()
        self.last_skill_toggle_time = 0.0  # evdev/pynput 중복 호출 방지용 디바운스
        self.help_lbl = None
        self.test_entry = None

        self.load_config()

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
        """설정 파일 로드 및 구버전 마이그레이션"""
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
        """현재 UI 설정을 config.json에 영구 저장"""
        try:
            self.config["master_enabled"] = self.master_enabled
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[설정 저장 오류] {e}")
            return False

    def do_activate(self):
        """GTK 창 생성 및 초기화 (콤팩트 미니 창)"""
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("디아블로 IV 통합 매크로")
        self.window.set_default_size(480, 620)
        self.window.set_resizable(False)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)

        # 1. 상단 슬림 헤더 영역
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        title_lbl = Gtk.Label(label="⚔️ 디아블로 IV 통합 매크로")
        title_lbl.set_halign(Gtk.Align.START)
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        attrs.insert(Pango.attr_scale_new(1.15))
        title_lbl.set_attributes(attrs)
        header_box.append(title_lbl)

        # 마스터 활성화 스위치
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        switch_box.set_hexpand(True)
        switch_box.set_halign(Gtk.Align.END)
        self.master_switch = Gtk.Switch()
        self.master_switch.set_active(self.master_enabled)
        self.master_switch.connect("state-set", self.on_master_switch_toggled)
        switch_lbl = Gtk.Label(label="전체 활성화")
        switch_box.append(switch_lbl)
        switch_box.append(self.master_switch)
        header_box.append(switch_box)

        main_box.append(header_box)
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # 2. 실시간 상태 슬림 카드
        status_frame = Gtk.Frame()
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        status_box.set_margin_top(5)
        status_box.set_margin_bottom(5)
        status_box.set_margin_start(8)
        status_box.set_margin_end(8)

        self.status_indicator = Gtk.Label(label="🟢 대기 중: 토글 단축키를 누르면 매크로가 실행됩니다.")
        self.status_indicator.set_halign(Gtk.Align.START)
        attrs_stat = Pango.AttrList()
        attrs_stat.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
        self.status_indicator.set_attributes(attrs_stat)

        curr_trig = str(self.config.get("skill_macro", {}).get("keyboard_trigger", "f4")).upper()
        mode_val = self.config.get("skill_macro", {}).get("mode", "toggle")
        mode_str = "토글" if mode_val == "toggle" else "홀드"
        self.stats_label = Gtk.Label(label=f"• 스킬: 정지 ([{curr_trig}] {mode_str}) | • 매크로1: 0회 | • 매크로2: 0회")
        self.stats_label.set_halign(Gtk.Align.START)
        attrs_st = Pango.AttrList()
        attrs_st.insert(Pango.attr_scale_new(0.85))
        self.stats_label.set_attributes(attrs_st)

        status_box.append(self.status_indicator)
        status_box.append(self.stats_label)
        status_frame.set_child(status_box)
        main_box.append(status_frame)

        # 3. 3개 탭 구성 (Gtk.Notebook)
        self.notebook = Gtk.Notebook()
        
        tab_skill_content = self.create_skill_macro_tab_content()
        tab_skill_label = Gtk.Label(label="⚡ 스킬 연타")
        self.notebook.append_page(tab_skill_content, tab_skill_label)

        tab1_content = self.create_macro_tab_content("macro1", "🔵 매크로 1 (Ctrl+우클릭)")
        tab1_label = Gtk.Label(label="🔵 매크로 1 (우클릭)")
        self.notebook.append_page(tab1_content, tab1_label)

        tab2_content = self.create_macro_tab_content("macro2", "🔴 매크로 2 (아이템 버리기)")
        tab2_label = Gtk.Label(label="🔴 매크로 2 (버리기)")
        self.notebook.append_page(tab2_content, tab2_label)

        main_box.append(self.notebook)

        # 4. 실시간 입력 테스트 필드
        test_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        test_lbl = Gtk.Label(label="⌨️ 입력 테스트:")
        self.test_entry = Gtk.Entry()
        self.test_entry.set_placeholder_text("여기를 클릭하고 단축키를 누르면 숫자가 찍힙니다")
        self.test_entry.set_hexpand(True)
        test_box.append(test_lbl)
        test_box.append(self.test_entry)
        main_box.append(test_box)

        # 5. 하단 공통 제어 버튼
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        save_btn = Gtk.Button(label="💾 설정 파일 저장")
        save_btn.set_hexpand(True)
        save_btn.connect("clicked", self.on_save_all_clicked)
        btn_box.append(save_btn)

        stop_btn = Gtk.Button(label="🛑 긴급 중지 (F12)")
        stop_btn.connect("clicked", self.on_emergency_stop)
        btn_box.append(stop_btn)

        main_box.append(btn_box)

        # 6. 하단 안내 텍스트
        self.help_lbl = Gtk.Label(
            label=f"• 긴급 정지: [F12] | 스킬 토글: [{curr_trig}] | 아이템 버리기: 사이드 앞버튼"
        )
        self.help_lbl.set_halign(Gtk.Align.CENTER)
        attrs_h = Pango.AttrList()
        attrs_h.insert(Pango.attr_scale_new(0.8))
        self.help_lbl.set_attributes(attrs_h)
        main_box.append(self.help_lbl)

        self.window.set_child(main_box)
        self.window.present()

        # 백그라운드 리스너 시작
        self.start_background_listeners()

    def create_skill_macro_tab_content(self) -> Gtk.Widget:
        """스킬 자동 연타 탭 전용 콤팩트 UI"""
        cfg = self.config.get("skill_macro", {})
        w = self.skill_tab_widgets

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # (1) 활성화 체크박스 + 이름
        row_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        w.enable_check = Gtk.CheckButton(label="스킬 연타 활성화")
        w.enable_check.set_active(cfg.get("enabled", True))
        w.enable_check.set_hexpand(True)
        w.enable_check.connect("toggled", lambda b: self._sync_skill_enabled(b.get_active()))

        w.entry_name = Gtk.Entry()
        w.entry_name.set_text(cfg.get("name", "스킬 자동 연타 (1~5)"))
        w.entry_name.set_size_request(150, -1)

        row_top.append(w.enable_check)
        row_top.append(w.entry_name)
        box.append(row_top)
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # (2) 시작/정지 단축키 & 동작 모드 (토글 vs 홀드)
        row_trig = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        lbl_ktrig = Gtk.Label(label="단축키:")
        w.entry_kb_trigger = Gtk.Entry()
        initial_trig = str(cfg.get("keyboard_trigger", "f4")).upper()
        w.entry_kb_trigger.set_text(initial_trig)
        w.entry_kb_trigger.set_max_length(8)
        w.entry_kb_trigger.set_size_request(60, -1)
        w.entry_kb_trigger.connect("changed", self.on_skill_trigger_changed)

        row_trig.append(lbl_ktrig)
        row_trig.append(w.entry_kb_trigger)

        lbl_mode = Gtk.Label(label="모드:")
        lbl_mode.set_margin_start(8)
        mode_labels = [item[0] for item in SKILL_MODE_LIST]
        w.dropdown_mode = Gtk.DropDown.new_from_strings(mode_labels)
        cur_mode = cfg.get("mode", "toggle")
        mode_idx = 0 if cur_mode == "toggle" else 1
        w.dropdown_mode.set_selected(mode_idx)
        w.dropdown_mode.connect("notify::selected", self.on_skill_mode_changed)
        row_trig.append(lbl_mode)
        row_trig.append(w.dropdown_mode)
        box.append(row_trig)

        # (2-1) 마우스 트리거
        row_mtrig = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_mtrig = Gtk.Label(label="마우스 트리거:")
        mtrig_labels = [item[0] for item in MOUSE_TRIGGER_LIST]
        w.dropdown_mouse_trigger = Gtk.DropDown.new_from_strings(mtrig_labels)
        cur_mtrig = cfg.get("mouse_trigger", "none")
        mtrig_idx = 3
        for i, item in enumerate(MOUSE_TRIGGER_LIST):
            if item[1] == cur_mtrig:
                mtrig_idx = i
                break
        w.dropdown_mouse_trigger.set_selected(mtrig_idx)
        w.dropdown_mouse_trigger.connect("notify::selected", self.on_skill_mouse_trigger_changed)
        w.dropdown_mouse_trigger.set_hexpand(True)
        row_mtrig.append(lbl_mtrig)
        row_mtrig.append(w.dropdown_mouse_trigger)
        box.append(row_mtrig)

        # (3) 연타할 스킬 키 목록
        row_skeys = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_skeys = Gtk.Label(label="연타할 스킬 키:")
        lbl_skeys.set_halign(Gtk.Align.START)
        w.entry_skill_keys = Gtk.Entry()
        cur_keys = cfg.get("skill_keys", ["1", "2", "3", "4", "5"])
        w.entry_skill_keys.set_text(" ".join(cur_keys))
        w.entry_skill_keys.set_hexpand(True)
        # 스킬 키 변경 즉시 실시간 동기화
        w.entry_skill_keys.connect("changed", self.on_skill_keys_changed)
        row_skeys.append(lbl_skeys)
        row_skeys.append(w.entry_skill_keys)
        box.append(row_skeys)

        # (4) 속도 원클릭 프리셋 버튼 4개
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lbl_preset = Gtk.Label(label="⚡ 프리셋:")
        preset_box.append(lbl_preset)

        btn_p1 = Gtk.Button(label="⚡ 1ms 초광속")
        btn_p1.connect("clicked", lambda b: self.apply_skill_speed_preset(1.0, 2.0, 35.0))
        preset_box.append(btn_p1)

        btn_p2 = Gtk.Button(label="🚀 15ms 고속")
        btn_p2.connect("clicked", lambda b: self.apply_skill_speed_preset(10.0, 15.0, 50.0))
        preset_box.append(btn_p2)

        btn_p3 = Gtk.Button(label="🎯 35ms 표준")
        btn_p3.connect("clicked", lambda b: self.apply_skill_speed_preset(20.0, 30.0, 80.0))
        preset_box.append(btn_p3)

        btn_p4 = Gtk.Button(label="🛡️ 80ms 여유")
        btn_p4.connect("clicked", lambda b: self.apply_skill_speed_preset(40.0, 60.0, 150.0))
        preset_box.append(btn_p4)

        box.append(preset_box)

        # (5) 정밀 지연시간 (누름 / 간격 / 사이클)
        delays_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        
        lbl_p = Gtk.Label(label="누름(ms):")
        w.spin_press = Gtk.SpinButton.new_with_range(0.5, 500.0, 0.5)
        w.spin_press.set_digits(1)
        w.spin_press.set_value(float(cfg.get("press_delay_ms", 1.0)))
        w.spin_press.set_size_request(60, -1)
        w.spin_press.connect("value-changed", lambda s: self._sync_skill_timing("press_delay_ms", s.get_value()))
        delays_box.append(lbl_p)
        delays_box.append(w.spin_press)

        lbl_i = Gtk.Label(label="간격(ms):")
        w.spin_interval = Gtk.SpinButton.new_with_range(0.5, 500.0, 0.5)
        w.spin_interval.set_digits(1)
        w.spin_interval.set_value(float(cfg.get("interval_ms", 1.0)))
        w.spin_interval.set_size_request(60, -1)
        w.spin_interval.connect("value-changed", lambda s: self._sync_skill_timing("interval_ms", s.get_value()))
        delays_box.append(lbl_i)
        delays_box.append(w.spin_interval)

        lbl_c = Gtk.Label(label="대기(ms):")
        w.spin_cycle = Gtk.SpinButton.new_with_range(0.5, 1000.0, 1.0)
        w.spin_cycle.set_digits(1)
        w.spin_cycle.set_value(float(cfg.get("cycle_delay_ms", 1.0)))
        w.spin_cycle.set_size_request(60, -1)
        w.spin_cycle.connect("value-changed", lambda s: self._sync_skill_timing("cycle_delay_ms", s.get_value()))
        delays_box.append(lbl_c)
        delays_box.append(w.spin_cycle)

        box.append(delays_box)

        # (6) OSD 알림 여부
        row_noti = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        w.check_notify = Gtk.CheckButton(label="게임 OSD 화면 알림 (notify-send 팝업)")
        w.check_notify.set_active(cfg.get("show_notifications", True))
        w.check_notify.connect("toggled", lambda b: self._sync_skill_notify(b.get_active()))
        row_noti.append(w.check_notify)
        box.append(row_noti)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # (7) 수동 토글 버튼 (GUI에서 직접 켜고 끄기)
        trig_str = str(cfg.get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if cur_mode == "toggle" else "홀드"
        w.btn_toggle_action = Gtk.Button(label=f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")
        w.btn_toggle_action.connect("clicked", lambda b: self.toggle_skill_macro())
        box.append(w.btn_toggle_action)

        return box

    def _sync_skill_enabled(self, val: bool):
        self.config["skill_macro"]["enabled"] = val

    def _sync_skill_timing(self, key_name: str, val: float):
        self.config["skill_macro"][key_name] = round(val, 2)

    def _sync_skill_notify(self, val: bool):
        self.config["skill_macro"]["show_notifications"] = val

    def on_skill_mode_changed(self, dropdown, param):
        sel = dropdown.get_selected()
        mode_val = SKILL_MODE_LIST[sel][1]
        self.config["skill_macro"]["mode"] = mode_val
        trig_str = str(self.config["skill_macro"].get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if mode_val == "toggle" else "홀드"
        if self.skill_tab_widgets.btn_toggle_action and not self.skill_state["active"]:
            self.skill_tab_widgets.btn_toggle_action.set_label(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")
        self.update_status_ui(f"스킬 동작 모드가 [{SKILL_MODE_LIST[sel][0]}]로 설정되었습니다.")

    def on_skill_trigger_changed(self, entry):
        """단축키 입력창 변경 시 실시간으로 즉각 반영"""
        txt = entry.get_text().strip().lower()
        if txt:
            self.config["skill_macro"]["keyboard_trigger"] = txt
            upper_k = txt.upper()
            mode_val = self.config["skill_macro"].get("mode", "toggle")
            mode_str = "토글" if mode_val == "toggle" else "홀드"
            if self.skill_tab_widgets.btn_toggle_action and not self.skill_state["active"]:
                self.skill_tab_widgets.btn_toggle_action.set_label(f"▶ 스킬 연타 시작 ([{upper_k}] {mode_str})")
            if self.help_lbl:
                self.help_lbl.set_text(f"• 긴급 정지: [F12] | 스킬 단축키: [{upper_k}] | 아이템 버리기: 사이드 앞버튼")
            self.update_status_ui(f"스킬 단축키가 [{upper_k}]로 실시간 변경되었습니다.")

    def on_skill_mouse_trigger_changed(self, dropdown, param):
        sel = dropdown.get_selected()
        self.config["skill_macro"]["mouse_trigger"] = MOUSE_TRIGGER_LIST[sel][1]
        sel = dropdown.get_selected()
        self.config["skill_macro"]["mouse_trigger"] = MOUSE_TRIGGER_LIST[sel][1]

    def on_skill_keys_changed(self, entry):
        """스킬 키 목록 입력창 변경 시 실시간으로 즉각 반영"""
        raw_keys = entry.get_text().replace(',', ' ').split()
        keys = [k.strip().lower() for k in raw_keys if k.strip()]
        if keys:
            self.config["skill_macro"]["skill_keys"] = keys

    def apply_skill_speed_preset(self, press_ms: float, interval_ms: float, cycle_ms: float):
        """속도 프리셋 버튼 클릭 시 스핀 버튼 값 일괄 적용"""
        w = self.skill_tab_widgets
        w.spin_press.set_value(press_ms)
        w.spin_interval.set_value(interval_ms)
        w.spin_cycle.set_value(cycle_ms)
        self.config["skill_macro"]["press_delay_ms"] = press_ms
        self.config["skill_macro"]["interval_ms"] = interval_ms
        self.config["skill_macro"]["cycle_delay_ms"] = cycle_ms
        self.update_status_ui(f"⚡ 스킬 속도 적용: 누름 {press_ms}ms / 간격 {interval_ms}ms / 대기 {cycle_ms}ms")

    def create_macro_tab_content(self, uid: str, title_str: str) -> Gtk.Widget:
        """기존 매크로 1 및 매크로 2 탭 콤팩트 UI"""
        cfg = self.config.get(uid, {})
        widgets = self.tab_widgets[uid]

        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form_box.set_margin_top(6)
        form_box.set_margin_bottom(6)
        form_box.set_margin_start(8)
        form_box.set_margin_end(8)

        # (1) 활성화 체크박스 + 이름
        row_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        widgets.enable_check = Gtk.CheckButton(label="이 매크로 활성화")
        widgets.enable_check.set_active(cfg.get("enabled", True))
        widgets.enable_check.set_hexpand(True)

        widgets.entry_name = Gtk.Entry()
        widgets.entry_name.set_text(cfg.get("name", title_str))
        widgets.entry_name.set_size_request(150, -1)

        row_top.append(widgets.enable_check)
        row_top.append(widgets.entry_name)
        form_box.append(row_top)
        form_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # (2) 입력 대상 (Target)
        row_tgt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_tgt = Gtk.Label(label="연타 대상:")
        lbl_tgt.set_halign(Gtk.Align.START)

        tgt_labels = [item[0] for item in TARGET_TYPE_LIST]
        widgets.dropdown_target = Gtk.DropDown.new_from_strings(tgt_labels)
        cur_tgt = cfg.get("target_type", "keyboard")
        tgt_idx = 0
        for i, item in enumerate(TARGET_TYPE_LIST):
            if item[1] == cur_tgt:
                tgt_idx = i
                break
        widgets.dropdown_target.set_selected(tgt_idx)
        widgets.dropdown_target.set_hexpand(True)
        row_tgt.append(lbl_tgt)
        row_tgt.append(widgets.dropdown_target)
        form_box.append(row_tgt)

        # (2-1) 키보드 키 입력창
        widgets.key_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_key = Gtk.Label(label="키보드 키:")
        widgets.entry_target_key = Gtk.Entry()
        widgets.entry_target_key.set_text(str(cfg.get("target_value", "f")).upper())
        widgets.entry_target_key.set_max_length(5)
        widgets.entry_target_key.set_size_request(55, -1)
        widgets.key_box.append(lbl_key)
        widgets.key_box.append(widgets.entry_target_key)
        form_box.append(widgets.key_box)

        def on_target_changed(dropdown, param):
            sel = dropdown.get_selected()
            widgets.key_box.set_visible(TARGET_TYPE_LIST[sel][1] == "keyboard")

        widgets.dropdown_target.connect("notify::selected", on_target_changed)
        widgets.key_box.set_visible(cur_tgt == "keyboard")

        # (3) 마우스 트리거 & 키보드 단축키
        row_mktrig = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_mtrig = Gtk.Label(label="마우스:")
        mtrig_labels = [item[0] for item in MOUSE_TRIGGER_LIST]
        widgets.dropdown_mouse_trigger = Gtk.DropDown.new_from_strings(mtrig_labels)
        cur_mtrig = cfg.get("mouse_trigger", "BTN_SIDE" if uid == "macro1" else "BTN_EXTRA")
        mtrig_idx = 3
        for i, item in enumerate(MOUSE_TRIGGER_LIST):
            if item[1] == cur_mtrig:
                mtrig_idx = i
                break
        widgets.dropdown_mouse_trigger.set_selected(mtrig_idx)
        row_mktrig.append(lbl_mtrig)
        row_mktrig.append(widgets.dropdown_mouse_trigger)

        lbl_ktrig = Gtk.Label(label="키:")
        lbl_ktrig.set_margin_start(8)
        widgets.entry_kb_trigger = Gtk.Entry()
        widgets.entry_kb_trigger.set_text(str(cfg.get("keyboard_trigger", "f1" if uid == "macro1" else "f2")).upper())
        widgets.entry_kb_trigger.set_max_length(5)
        widgets.entry_kb_trigger.set_size_request(55, -1)
        widgets.entry_kb_trigger.connect("changed", lambda e, u=uid: self._sync_macro_kb_trigger(u, e.get_text()))
        row_mktrig.append(lbl_ktrig)
        row_mktrig.append(widgets.entry_kb_trigger)
        form_box.append(row_mktrig)

        # (4) 동작 모드 & 연타 횟수
        row_mode_cnt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_mode = Gtk.Label(label="모드:")
        mode_labels = [item[0] for item in MODE_LIST]
        widgets.dropdown_mode = Gtk.DropDown.new_from_strings(mode_labels)
        cur_mode = cfg.get("mode", "burst" if uid == "macro1" else "hold")
        mode_idx = 0
        for i, item in enumerate(MODE_LIST):
            if item[1] == cur_mode:
                mode_idx = i
                break
        widgets.dropdown_mode.set_selected(mode_idx)
        row_mode_cnt.append(lbl_mode)
        row_mode_cnt.append(widgets.dropdown_mode)

        lbl_cnt = Gtk.Label(label="횟수:")
        lbl_cnt.set_margin_start(8)
        widgets.spin_count = Gtk.SpinButton.new_with_range(1, 1000, 10)
        widgets.spin_count.set_value(float(cfg.get("burst_count", 100)))
        widgets.spin_count.set_size_request(65, -1)
        row_mode_cnt.append(lbl_cnt)
        row_mode_cnt.append(widgets.spin_count)
        form_box.append(row_mode_cnt)

        # (5) 딜레이 (누름 / 뗌)
        row_delays = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_d1 = Gtk.Label(label="누름(ms):")
        widgets.spin_press = Gtk.SpinButton.new_with_range(0.5, 50.0, 0.5)
        widgets.spin_press.set_digits(1)
        widgets.spin_press.set_value(float(cfg.get("press_delay_ms", 1.0)))
        widgets.spin_press.set_size_request(60, -1)
        row_delays.append(lbl_d1)
        row_delays.append(widgets.spin_press)

        lbl_d2 = Gtk.Label(label="뗌(ms):")
        lbl_d2.set_margin_start(8)
        widgets.spin_release = Gtk.SpinButton.new_with_range(0.5, 50.0, 0.5)
        widgets.spin_release.set_digits(1)
        widgets.spin_release.set_value(float(cfg.get("release_delay_ms", 1.0)))
        widgets.spin_release.set_size_request(60, -1)
        row_delays.append(lbl_d2)
        row_delays.append(widgets.spin_release)
        form_box.append(row_delays)

        # (6) 테스트 버튼
        test_btn = Gtk.Button(label=f"⚡ {cfg.get('name', title_str)} 1회 테스트")
        test_btn.connect("clicked", lambda b, u=uid: self.on_test_clicked(u))
        form_box.append(test_btn)

        return form_box

    def _sync_macro_kb_trigger(self, uid: str, text: str):
        t = text.strip().lower()
        if t:
            self.config[uid]["keyboard_trigger"] = t

    def on_master_switch_toggled(self, switch, state):
        self.master_enabled = state
        if state:
            self.update_status_ui("🟢 대기 중: 매크로가 켜졌습니다.")
        else:
            self.on_emergency_stop()
            self.update_status_ui("⚪ 비활성화됨: 전체 매크로가 꺼져 있습니다.")
        return False

    def on_save_all_clicked(self, btn):
        """모든 탭의 설정을 반영하여 config.json에 영구 저장"""
        for uid in ("macro1", "macro2"):
            w = self.tab_widgets[uid]
            cfg = self.config[uid]
            cfg["enabled"] = w.enable_check.get_active()
            cfg["name"] = w.entry_name.get_text().strip() or uid
            
            t_sel = w.dropdown_target.get_selected()
            cfg["target_type"] = TARGET_TYPE_LIST[t_sel][1]
            if cfg["target_type"] == "keyboard":
                cfg["target_value"] = w.entry_target_key.get_text().strip().lower() or "f"
            elif cfg["target_type"] == "ctrl_mouse_left":
                cfg["target_value"] = "ctrl_left"
            elif cfg["target_type"] == "ctrl_mouse_right":
                cfg["target_value"] = "ctrl_right"
            elif cfg["target_type"] == "mouse_right":
                cfg["target_value"] = "right"
            elif cfg["target_type"] == "mouse_left":
                cfg["target_value"] = "left"

            m_sel = w.dropdown_mouse_trigger.get_selected()
            cfg["mouse_trigger"] = MOUSE_TRIGGER_LIST[m_sel][1]
            cfg["keyboard_trigger"] = w.entry_kb_trigger.get_text().strip().lower()

            mode_sel = w.dropdown_mode.get_selected()
            cfg["mode"] = MODE_LIST[mode_sel][1]

            cfg["burst_count"] = int(w.spin_count.get_value())
            cfg["press_delay_ms"] = round(w.spin_press.get_value(), 2)
            cfg["release_delay_ms"] = round(w.spin_release.get_value(), 2)

        sw = self.skill_tab_widgets
        scfg = self.config["skill_macro"]
        scfg["enabled"] = sw.enable_check.get_active()
        scfg["name"] = sw.entry_name.get_text().strip() or "스킬 자동 연타"
        
        new_trig = sw.entry_kb_trigger.get_text().strip().lower() or "f4"
        scfg["keyboard_trigger"] = new_trig

        sm_sel = sw.dropdown_mouse_trigger.get_selected()
        scfg["mouse_trigger"] = MOUSE_TRIGGER_LIST[sm_sel][1]

        if sw.dropdown_mode:
            mode_sel = sw.dropdown_mode.get_selected()
            scfg["mode"] = SKILL_MODE_LIST[mode_sel][1]

        raw_keys = sw.entry_skill_keys.get_text().replace(',', ' ').split()
        scfg["skill_keys"] = [k.strip().lower() for k in raw_keys if k.strip()] or ["1", "2", "3", "4", "5"]

        scfg["press_delay_ms"] = round(sw.spin_press.get_value(), 2)
        scfg["interval_ms"] = round(sw.spin_interval.get_value(), 2)
        scfg["cycle_delay_ms"] = round(sw.spin_cycle.get_value(), 2)
        scfg["show_notifications"] = sw.check_notify.get_active()

        if self.save_config():
            self.update_status_ui("✓ 설정이 성공적으로 저장되었습니다.")
            GLib.timeout_add(1500, lambda: self.update_status_ui("🟢 대기 중: 트리거 키를 누르면 시작됩니다."))

    def on_test_clicked(self, uid: str):
        if not self.master_enabled:
            self.update_status_ui("⚠️ 전체 활성화 스위치를 먼저 켜주세요.")
            return
        self.execute_burst(uid)

    def on_emergency_stop(self, btn=None):
        """긴급 중지: 모든 매크로와 스킬 연타 중단 및 키 릴리스"""
        self.skill_state["active"] = False
        scfg = self.config.get("skill_macro", {})
        trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
        mode_str = "토글" if scfg.get("mode", "toggle") == "toggle" else "홀드"
        if self.skill_tab_widgets.btn_toggle_action:
            self.skill_tab_widgets.btn_toggle_action.set_label(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")

        for uid in ("macro1", "macro2"):
            st = self.macro_states[uid]
            st["active"] = False
            st["pressed"] = False
            self.release_target(uid)

        try:
            self.keyboard.release(Key.ctrl)
            for k in self.config.get("skill_macro", {}).get("skill_keys", ["1", "2", "3", "4", "5"]):
                try:
                    self.keyboard.release(k)
                except Exception:
                    pass
        except Exception:
            pass

        self.update_status_ui("🛑 긴급 중지: 모든 매크로 동작이 즉각 정지되었습니다.")

    def toggle_skill_macro(self, force_state=None):
        """스킬 자동 연타 시작/정지 제어 (250ms 디바운스로 evdev/pynput 중복 호출 원천 차단)"""
        if not self.master_enabled:
            self.update_status_ui("⚠️ 전체 활성화 스위치를 먼저 켜주세요.")
            return

        scfg = self.config.get("skill_macro", {})
        if not scfg.get("enabled", True):
            self.update_status_ui("⚠️ 스킬 자동 연타가 꺼져 있습니다. 체크박스를 켜주세요.")
            return

        now = time.perf_counter()
        trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
        mode_val = scfg.get("mode", "toggle")
        mode_str = "토글" if mode_val == "toggle" else "홀드"

        # 1. 상태 전환 결정
        if force_state is not None:
            if force_state == self.skill_state["active"]:
                return  # 이미 요청된 상태이면 무시
            new_state = force_state
        else:
            # 토글 모드: 250ms 이내 중복 트리거(evdev + pynput 연속 호출) 차단
            if now - self.last_skill_toggle_time < 0.25:
                return
            self.last_skill_toggle_time = now
            new_state = not self.skill_state["active"]

        self.skill_state["active"] = new_state

        if not new_state:
            # 즉각 정지 처리: 플래그 해제 + 키 강제 릴리스 + X11 디스플레이 동기화로 큐 비우기
            scfg = self.config.get("skill_macro", {})
            for k in scfg.get("skill_keys", ["1", "2", "3", "4", "5"]):
                try:
                    self.keyboard.release(k)
                except Exception:
                    pass
            if hasattr(self.keyboard, '_display'):
                try:
                    self.keyboard._display.sync()
                except Exception:
                    pass

            if self.skill_tab_widgets.btn_toggle_action:
                self.skill_tab_widgets.btn_toggle_action.set_label(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})")
            self.update_status_ui(f"■ [스킬 연타 정지] 즉각 중단되었습니다. ([{trig_str}] 재시작)")
            if scfg.get("show_notifications", True):
                send_osd_notification("디아블로4 매크로", f"■ 스킬 연타 정지 (OFF) - [{trig_str}]")
        else:
            # 시작 처리
            if self.skill_tab_widgets.btn_toggle_action:
                self.skill_tab_widgets.btn_toggle_action.set_label("■ 스킬 연타 가동 중... (클릭 시 멈춤)")
            self.update_status_ui(f"⚡ [스킬 연타 가동 중] 반복 실행 중... ([{trig_str}] 정지)")
            if scfg.get("show_notifications", True):
                keys_str = " ".join(scfg.get("skill_keys", ["1", "2", "3", "4", "5"]))
                send_osd_notification("디아블로4 매크로", f"▶ 스킬 연타 시작 (ON) - {keys_str}")
            
            threading.Thread(target=self._skill_macro_worker, daemon=True).start()

    def _skill_macro_worker(self):
        """스킬 자동 연타 백그라운드 고정밀 루프 (큐 누적 원천 차단 및 즉각 반응형)"""
        cycles = 0
        is_active = lambda: self.skill_state["active"] and self.master_enabled and self.running
        try:
            while is_active():
                scfg = self.config.get("skill_macro", {})
                skill_keys = scfg.get("skill_keys", ["1", "2", "3", "4", "5"])
                press_d = max(0.0005, float(scfg.get("press_delay_ms", 1.0)) / 1000.0)
                interval_d = max(0.0005, float(scfg.get("interval_ms", 1.0)) / 1000.0)
                cycle_d = max(0.0005, float(scfg.get("cycle_delay_ms", 1.0)) / 1000.0)

                # [적응형 큐 누적 방지 가드 (Anti-Bloat Guard)]
                # 디아블로4 게임 DirectInput 큐에 수천 개의 미처리 키 이벤트가 쌓이는 것을 원천 방지합니다.
                # 게임 틱레이트(60Hz) 기준 1사이클 전체 시간이 최소 35ms(초당 최대 ~28회)를 유지하도록 안전 마진을 자동 보장합니다.
                keys_total_time = len(skill_keys) * (press_d + interval_d)
                safe_cycle_d = max(cycle_d, max(0.005, 0.035 - keys_total_time))

                for k in skill_keys:
                    if not is_active():
                        break
                    try:
                        self.keyboard.press(k)
                        interruptible_sleep(press_d, is_active)
                        self.keyboard.release(k)
                        interruptible_sleep(interval_d, is_active)
                    except Exception:
                        pass

                cycles += 1
                self.skill_state["cycles"] = cycles

                if not is_active():
                    break

                if safe_cycle_d > 0:
                    interruptible_sleep(safe_cycle_d, is_active)

                # 매 사이클마다 X11 디스플레이 동기화로 백로그 누적 방지
                if hasattr(self.keyboard, '_display'):
                    try:
                        self.keyboard._display.sync()
                    except Exception:
                        pass
        finally:
            scfg = self.config.get("skill_macro", {})
            for k in scfg.get("skill_keys", ["1", "2", "3", "4", "5"]):
                try:
                    self.keyboard.release(k)
                except Exception:
                    pass
            if hasattr(self.keyboard, '_display'):
                try:
                    self.keyboard._display.sync()
                except Exception:
                    pass
            self.skill_state["active"] = False
            trig_str = str(scfg.get("keyboard_trigger", "f4")).upper()
            mode_val = scfg.get("mode", "toggle")
            mode_str = "토글" if mode_val == "toggle" else "홀드"
            GLib.idle_add(lambda: self.skill_tab_widgets.btn_toggle_action.set_label(f"▶ 스킬 연타 시작 ([{trig_str}] {mode_str})") if self.skill_tab_widgets.btn_toggle_action else False)

    def update_status_ui(self, message: str):
        def _update():
            self.status_indicator.set_text(message)
            m1 = self.macro_states["macro1"]
            m2 = self.macro_states["macro2"]
            scfg = self.config.get("skill_macro", {})
            curr_trig = str(scfg.get("keyboard_trigger", "f4")).upper()
            mode_val = scfg.get("mode", "toggle")
            mode_str = "토글" if mode_val == "toggle" else "홀드"
            skill_status = f"가동 중 ({self.skill_state['cycles']}회)" if self.skill_state["active"] else f"정지 ([{curr_trig}] {mode_str})"
            self.stats_label.set_text(
                f"• 스킬: {skill_status} | • 매크로1: {m1['runs']}회 | • 매크로2: {m2['runs']}회"
            )
            return False
        GLib.idle_add(_update)

    def press_target(self, uid: str):
        cfg = self.config.get(uid, {})
        ttype = cfg.get("target_type", "keyboard")
        val = cfg.get("target_value", "f")
        if ttype == "ctrl_mouse_left":
            self.mouse.press(Button.left)
        elif ttype == "ctrl_mouse_right":
            self.mouse.press(Button.right)
        elif ttype == "mouse_right":
            self.mouse.press(Button.right)
        elif ttype == "mouse_left":
            self.mouse.press(Button.left)
        else:
            self.keyboard.press(val)

    def release_target(self, uid: str):
        cfg = self.config.get(uid, {})
        ttype = cfg.get("target_type", "keyboard")
        val = cfg.get("target_value", "f")
        try:
            if ttype == "ctrl_mouse_left":
                self.mouse.release(Button.left)
            elif ttype == "ctrl_mouse_right":
                self.mouse.release(Button.right)
            elif ttype == "mouse_right":
                self.mouse.release(Button.right)
            elif ttype == "mouse_left":
                self.mouse.release(Button.left)
            else:
                self.keyboard.release(val)
        except Exception:
            pass

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
        # 큐 누적 방지: 1회 주기 최소 25ms 보장 (초당 최대 ~40회, 큐 적체율 0%)
        safe_release_d = max(release_d, max(0.005, 0.025 - press_d))
        is_ctrl = cfg.get("target_type") in ("ctrl_mouse_left", "ctrl_mouse_right")
        is_active = lambda: st["active"] and st["pressed"] and self.master_enabled and self.running

        def _worker():
            self.update_status_ui(f"⚡ [{name}] {count}회 연타 중...")
            t0 = time.perf_counter()
            done = 0
            try:
                if is_ctrl:
                    self.keyboard.press(Key.ctrl)
                    interruptible_sleep(0.002, is_active)
                for _ in range(count):
                    if not is_active():
                        break
                    self.press_target(uid)
                    interruptible_sleep(press_d, is_active)
                    self.release_target(uid)
                    interruptible_sleep(safe_release_d, is_active)
                    done += 1
                    # 매 사이클마다 디스플레이 소켓 동기화
                    if hasattr(self.keyboard, '_display'):
                        try: self.keyboard._display.sync()
                        except Exception: pass
                    if hasattr(self.mouse, '_display'):
                        try: self.mouse._display.sync()
                        except Exception: pass
            finally:
                self.release_target(uid)
                if is_ctrl:
                    try:
                        self.keyboard.release(Key.ctrl)
                    except Exception:
                        pass
                if hasattr(self.keyboard, '_display'):
                    try: self.keyboard._display.sync()
                    except Exception: pass
                if hasattr(self.mouse, '_display'):
                    try: self.mouse._display.sync()
                    except Exception: pass
                dur_ms = (time.perf_counter() - t0) * 1000.0
                st["runs"] += 1
                st["actions"] += done
                st["last_ms"] = dur_ms
                st["active"] = False
                self.update_status_ui(f"✓ [{name}] {done}회 연타 완료 ({dur_ms:.1f}ms)")

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
        # 큐 누적 방지: 1회 주기 최소 25ms 보장 (초당 최대 ~40회, 큐 적체율 0%)
        safe_release_d = max(release_d, max(0.005, 0.025 - press_d))
        is_ctrl = cfg.get("target_type") in ("ctrl_mouse_left", "ctrl_mouse_right")
        is_active = lambda: st["active"] and st["pressed"] and self.master_enabled and self.running

        def _worker():
            self.update_status_ui(f"⚡ [{name}] 연타 유지 중...")
            t0 = time.perf_counter()
            done = 0
            try:
                if is_ctrl:
                    self.keyboard.press(Key.ctrl)
                    interruptible_sleep(0.002, is_active)
                while is_active():
                    self.press_target(uid)
                    interruptible_sleep(press_d, is_active)
                    self.release_target(uid)
                    interruptible_sleep(safe_release_d, is_active)
                    done += 1
                    # 매 사이클마다 디스플레이 소켓 동기화
                    if hasattr(self.keyboard, '_display'):
                        try: self.keyboard._display.sync()
                        except Exception: pass
                    if hasattr(self.mouse, '_display'):
                        try: self.mouse._display.sync()
                        except Exception: pass
            finally:
                self.release_target(uid)
                if is_ctrl:
                    try:
                        self.keyboard.release(Key.ctrl)
                    except Exception:
                        pass
                if hasattr(self.keyboard, '_display'):
                    try: self.keyboard._display.sync()
                    except Exception: pass
                if hasattr(self.mouse, '_display'):
                    try: self.mouse._display.sync()
                    except Exception: pass
                dur_ms = (time.perf_counter() - t0) * 1000.0
                st["runs"] += 1
                st["actions"] += done
                st["last_ms"] = dur_ms
                st["active"] = False
                self.update_status_ui(f"✓ [{name} 정지] {done}회 연타 ({dur_ms:.1f}ms)")

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
            # 손을 떼는 순간 즉각 중지: 플래그 해제 + 타겟 릴리스 + 디스플레이 버퍼 동기화
            st["pressed"] = False
            st["active"] = False
            self.release_target(uid)
            try:
                self.keyboard.release(Key.ctrl)
            except Exception:
                pass
            if hasattr(self.keyboard, '_display'):
                try: self.keyboard._display.sync()
                except Exception: pass
            if hasattr(self.mouse, '_display'):
                try: self.mouse._display.sync()
                except Exception: pass
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
                self.update_status_ui(f"[{cfg.get('name', uid)} 토글 정지]")
            else:
                self.execute_burst(uid)

    def dispatch_mouse_trigger(self, trigger_name: str, is_press: bool):
        if not self.master_enabled:
            return
        
        if self.config.get("skill_macro", {}).get("mouse_trigger") == trigger_name:
            mode = self.config.get("skill_macro", {}).get("mode", "toggle")
            if mode == "toggle":
                if is_press:
                    self.toggle_skill_macro()
            elif mode == "hold":
                self.toggle_skill_macro(force_state=is_press)
            return

        for uid in ("macro1", "macro2"):
            if self.config.get(uid, {}).get("mouse_trigger") == trigger_name:
                self.trigger_unit(uid, is_press)

    def dispatch_keyboard_trigger(self, key_str: str, is_press: bool):
        if not self.master_enabled:
            return

        # 최신 실시간 등록된 keyboard_trigger와 비교
        target_trig = str(self.config.get("skill_macro", {}).get("keyboard_trigger", "f4")).lower()
        if key_str == target_trig:
            mode = self.config.get("skill_macro", {}).get("mode", "toggle")
            if mode == "toggle":
                if is_press:
                    self.toggle_skill_macro()
            elif mode == "hold":
                self.toggle_skill_macro(force_state=is_press)
            return

        for uid in ("macro1", "macro2"):
            if str(self.config.get(uid, {}).get("keyboard_trigger", "")).lower() == key_str:
                self.trigger_unit(uid, is_press)

    def start_background_listeners(self):
        """evdev 하드웨어 전역 리스너 (마우스 및 물리 키보드) + pynput 보조 리스너"""
        code_to_mouse_name = {
            ecodes.BTN_SIDE: "BTN_SIDE",
            ecodes.BTN_BACK: "BTN_SIDE",
            ecodes.BTN_EXTRA: "BTN_EXTRA",
            ecodes.BTN_FORWARD: "BTN_EXTRA",
            ecodes.BTN_MIDDLE: "BTN_MIDDLE"
        }

        # ecodes 키코드 -> 소문자 문자열 매핑 (f1~f12, space 등)
        ecodes_key_map = {}
        for name in dir(ecodes):
            if name.startswith('KEY_'):
                code = getattr(ecodes, name)
                ecodes_key_map[code] = name[4:].lower()

        # 1. evdev 전역 하드웨어 리스너 (Wayland 환경에서도 100% 감지)
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
                        if not dev:
                            continue
                        for ev in dev.read():
                            if ev.type == ecodes.EV_KEY:
                                if ev.code in code_to_mouse_name:
                                    trigname = code_to_mouse_name[ev.code]
                                    if ev.value == 1:
                                        self.dispatch_mouse_trigger(trigname, True)
                                    elif ev.value == 0:
                                        self.dispatch_mouse_trigger(trigname, False)
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

        # 2. pynput 마우스 보조 리스너
        def on_mouse_click(x, y, button, pressed):
            trigname = None
            if button == Button.x1:
                trigname = "BTN_SIDE"
            elif button == Button.x2:
                trigname = "BTN_EXTRA"
            elif button == Button.middle:
                trigname = "BTN_MIDDLE"
            if trigname:
                self.dispatch_mouse_trigger(trigname, pressed)

        m_listener = MouseListener(on_click=on_mouse_click)
        m_listener.daemon = True
        m_listener.start()

        # 3. pynput 키보드 보조 리스너
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

if __name__ == "__main__":
    app = MacroApp()
    app.run(sys.argv)
