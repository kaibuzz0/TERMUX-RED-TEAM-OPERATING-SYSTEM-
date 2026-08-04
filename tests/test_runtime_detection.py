"""Tests for lib/hive_runtime.py capability detector."""

import json
import os
import unittest
from pathlib import Path

from lib.hive_runtime import (
    CapabilityState,
    detect_android,
    detect_termux,
    detect_proot,
    detect_root_requested,
    detect_termux_api,
    detect_environment,
    detect_platform,
    detect_tools,
    build_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class CapabilityStateTests(unittest.TestCase):
    def test_states_are_strings(self):
        self.assertEqual(CapabilityState.AVAILABLE.value, "AVAILABLE")


class PlatformDetectionTests(unittest.TestCase):
    def test_detect_platform_has_required_fields(self):
        info = detect_platform()
        self.assertIn("system", info.__dict__)
        self.assertIn("android", info.__dict__)
        self.assertIn("termux", info.__dict__)

    def test_termux_not_simulated_on_windows(self):
        if os.name == "nt":
            self.assertNotEqual(detect_termux(), CapabilityState.AVAILABLE.value)

    def test_android_is_unverified_or_available(self):
        state = detect_android()
        self.assertIn(state.value, ["AVAILABLE", "UNVERIFIED", "UNAVAILABLE"])


class ToolDetectionTests(unittest.TestCase):
    def test_python_state_is_valid(self):
        state = detect_tools().python
        self.assertIn(state.value, ["AVAILABLE", "UNAVAILABLE"])

    def test_git_state_is_valid(self):
        state = detect_tools().git
        self.assertIn(state.value, ["AVAILABLE", "UNAVAILABLE"])

    def test_termux_api_unavailable_on_windows(self):
        if os.name == "nt":
            self.assertEqual(detect_termux_api().value, "UNAVAILABLE")


class EnvironmentTests(unittest.TestCase):
    def test_environment_returns_dict(self):
        env = detect_environment()
        self.assertIsNotNone(env.home)


class ReportTests(unittest.TestCase):
    def test_build_report_returns_structured_data(self):
        report = build_report()
        self.assertIn("platform", report.__dict__)
        self.assertIn("tools", report.__dict__)
        self.assertIn("environment", report.__dict__)


if __name__ == "__main__":
    unittest.main()
