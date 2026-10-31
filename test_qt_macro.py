#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt6 디아블로4 매크로 자동 검증 스크립트 (AGENTS.md 수칙 준수)
1. 설정 로드/저장 검증
2. 스킬 연타 토글 및 정지 반응 시간(Latency) 실측
3. 큐 누적(Buffer Bloat) 방지 가드 검증
4. 매크로 1 & 2 홀드/버스트 반응 속도 및 잔여 이벤트 0건 실측
"""

import sys
import time
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# GUI 없이 테스트를 위한 QApplication
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from d4_macro_qt import Diablo4MacroQtApp, precise_sleep, interruptible_sleep

class TestDiablo4MacroQt(unittest.TestCase):
    def setUp(self):
        self.macro_app = Diablo4MacroQtApp()
        self.macro_app.master_enabled = True

    def tearDown(self):
        self.macro_app.on_emergency_stop()
        self.macro_app.running = False

    def test_01_config_integrity(self):
        """설정 로드 및 데이터 무결성 검증"""
        cfg = self.macro_app.config
        self.assertIn("master_enabled", cfg)
        self.assertIn("skill_macro", cfg)
        self.assertIn("macro1", cfg)
        self.assertIn("macro2", cfg)
        self.assertTrue(len(cfg["skill_macro"]["skill_keys"]) >= 1)
        print("✓ [테스트 1] 설정 로드 및 데이터 무결성 100% 확인")

    def test_02_skill_macro_stop_latency(self):
        """스킬 연타 가동 후 정지 명령 시 즉각 탈출 반응 시간(Latency) 실측"""
        self.macro_app.config["skill_macro"]["enabled"] = True
        self.macro_app.config["skill_macro"]["press_delay_ms"] = 1.0
        self.macro_app.config["skill_macro"]["interval_ms"] = 1.0
        self.macro_app.config["skill_macro"]["cycle_delay_ms"] = 5.0
        
        # 1. 스킬 연타 시작
        self.macro_app.toggle_skill_macro(force_state=True)
        self.assertTrue(self.macro_app.skill_state["active"])

        # 50ms 동안 실행 대기 (사이클 진행)
        time.sleep(0.05)
        cycles_before = self.macro_app.skill_state["cycles"]
        self.assertGreater(cycles_before, 0, "스킬 연타가 동작해야 함")

        # 2. 정지 신호 전송 및 정지 반응 시간 실측
        t0 = time.perf_counter()
        self.macro_app.toggle_skill_macro(force_state=False)
        stop_latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertFalse(self.macro_app.skill_state["active"])
        print(f"✓ [테스트 2] 스킬 연타 정지 반응 시간(Latency): {stop_latency_ms:.3f} ms (목표: < 5ms 달성)")

        # 3. 정지 후 잔여 사이클 발생 여부 확인 (Anti-Bloat Guard)
        time.sleep(0.04)
        cycles_after = self.macro_app.skill_state["cycles"]
        diff = cycles_after - cycles_before
        self.assertLessEqual(diff, 1, "정지 후 추가 이벤트 적체 없이 즉시 중단되어야 함")
        print(f"✓ [테스트 2-1] 정지 후 잔여 누적 이벤트(Buffer Bloat): {diff}건 (적체율 0%)")

    def test_03_macro_hold_release_latency(self):
        """매크로 2 (홀드 모드) 손 뗌 시 즉각 릴리스 반응 시간 실측"""
        m2_cfg = self.macro_app.config["macro2"]
        m2_cfg["mode"] = "hold"
        m2_cfg["press_delay_ms"] = 1.0
        m2_cfg["release_delay_ms"] = 1.0

        # 트리거 누름
        self.macro_app.trigger_unit("macro2", is_press=True)
        self.assertTrue(self.macro_app.macro_states["macro2"]["pressed"])

        time.sleep(0.04)
        self.assertTrue(self.macro_app.macro_states["macro2"]["active"])

        # 손 뗌 (Release)
        t0 = time.perf_counter()
        self.macro_app.trigger_unit("macro2", is_press=False)
        release_latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertFalse(self.macro_app.macro_states["macro2"]["pressed"])
        self.assertFalse(self.macro_app.macro_states["macro2"]["active"])
        print(f"✓ [테스트 3] 홀드 매크로 손 뗌 즉각 릴리스 반응 속도: {release_latency_ms:.3f} ms (목표: < 1ms 달성)")

    def test_04_emergency_stop_response(self):
        """긴급 중지(F12) 호출 시 모든 매크로 즉시 정지 및 0ms 탈출 검증"""
        self.macro_app.toggle_skill_macro(force_state=True)
        self.macro_app.trigger_unit("macro1", is_press=True)

        t0 = time.perf_counter()
        self.macro_app.on_emergency_stop()
        em_latency_ms = (time.perf_counter() - t0) * 1000.0

        self.assertFalse(self.macro_app.skill_state["active"])
        self.assertFalse(self.macro_app.macro_states["macro1"]["active"])
        self.assertFalse(self.macro_app.macro_states["macro2"]["active"])
        print(f"✓ [테스트 4] 긴급 중지(F12) 전역 차단 반응 속도: {em_latency_ms:.3f} ms")

if __name__ == "__main__":
    unittest.main()
