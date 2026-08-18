"""Authoritative Hive network manager.

Coordinates profiles, state persistence, Tor/Orbot adapters, and health
reporting.  This is the single source of truth for network state that
PASS C (service supervisor) will consume.
"""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path
from typing import Any

import json
import urllib.request

from network.errors import NetworkRuntimeError, OrbotNotAvailableError, ProfileTransitionError, TorNotAvailableError
from network.health import HealthCheck, HealthLevel, HealthReport, summarize_health
from network.orbot import OrbotAdapter, OrbotEndpoints
from network.profiles import NetworkProfile, default_profile_config
from network.proxy import build_proxy_env, is_proxy_execution_allowed
from network.state import NetworkState, load_state, save_state, update_profile
from network.tor import TorAdapter, TorEndpoints


class NetworkManager:
    """Single authority for Hive network state."""

    def __init__(self, state_root: Path, repo_root: Path | None = None):
        self.state_root = Path(state_root)
        self.repo_root = repo_root
        self._tor_adapter: TorAdapter | None = None
        self._orbot_adapter: OrbotAdapter | None = None
        self._load()

    def _load(self) -> None:
        self.state = load_state(self.state_root)

    def _persist(self) -> None:
        save_state(self.state_root, self.state)

    @property
    def current_profile(self) -> NetworkProfile:
        return self.state.profile_enum

    # ------------------------------------------------------------------
    # Profile transitions
    # ------------------------------------------------------------------
    def select_direct(self) -> NetworkState:
        return self._set_profile(NetworkProfile.DIRECT)

    def select_orbot(self) -> NetworkState:
        state = self._set_profile(NetworkProfile.ORBOT)
        adapter = self._orbot()
        ok, detail = adapter.usable()
        state.last_error = None if ok else detail
        self._persist()
        return state

    def select_tor(self, *, timeout: float = 60.0) -> NetworkState:
        state = self._set_profile(NetworkProfile.TOR)
        adapter = self._tor()
        if not adapter.available():
            state.last_error = "tor binary not available"
            self._persist()
            raise TorNotAvailableError(state.last_error)
        try:
            result = adapter.start(timeout=timeout)
            if not result.get("started"):
                state.last_error = result.get("reason", "tor did not start")
        except Exception as exc:
            state.last_error = str(exc)
            self._persist()
            raise ProfileTransitionError(f"Failed to enter TOR profile: {exc}") from exc
        self._refresh_health()
        return state

    def select_hold(self) -> NetworkState:
        """Stop managed Tor and enter HOLD state."""
        tor = self._tor(may_be_none=True)
        if tor is not None:
            try:
                tor.stop()
            except Exception:
                pass
        state = self._set_profile(NetworkProfile.HOLD)
        state.listener_available = False
        state.control_available = False
        state.bootstrap_state = "unknown"
        state.proxy_test = None
        state.tor_confirmed = None
        return state

    def _set_profile(self, profile: NetworkProfile) -> NetworkState:
        cfg = default_profile_config(profile)
        self.state = update_profile(
            self.state_root,
            profile,
            socks_host=cfg.socks_host,
            socks_port=cfg.socks_port,
            control_host=cfg.control_host,
            control_port=cfg.control_port,
            managed_tor=cfg.managed_tor,
        )
        return self.state

    # ------------------------------------------------------------------
    # Adapters
    # ------------------------------------------------------------------
    def _tor(self, may_be_none: bool = False) -> TorAdapter:
        if self._tor_adapter is None:
            cfg = default_profile_config(NetworkProfile.TOR)
            state_dir = self.state_root / "tor"
            endpoints = TorEndpoints(
                socks_host=cfg.socks_host,
                socks_port=cfg.socks_port,
                control_host=cfg.control_host or "127.0.0.1",
                control_port=cfg.control_port or 9051,
            )
            adapter = TorAdapter(state_dir=state_dir, endpoints=endpoints)
            if not adapter.available() and may_be_none:
                return None  # type: ignore[return-value]
            self._tor_adapter = adapter
        return self._tor_adapter

    def _orbot(self) -> OrbotAdapter:
        if self._orbot_adapter is None:
            cfg = default_profile_config(NetworkProfile.ORBOT)
            endpoints = OrbotEndpoints(socks_host=cfg.socks_host, socks_port=cfg.socks_port)
            self._orbot_adapter = OrbotAdapter(endpoints)
        return self._orbot_adapter

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def health(self, *, include_proxy_test: bool = False, include_tor_confirmation: bool = False) -> HealthReport:
        profile = self.current_profile
        results: dict[HealthCheck, tuple[bool, str]] = {}

        if profile == NetworkProfile.DIRECT:
            results[HealthCheck.SOCKS_LISTENER] = (True, "direct mode does not require SOCKS")
            return HealthReport.from_results(str(profile), results)

        if profile == NetworkProfile.HOLD:
            results[HealthCheck.SOCKS_LISTENER] = (False, "HOLD mode: proxy execution disabled")
            return HealthReport.from_results(str(profile), results)

        if profile == NetworkProfile.ORBOT:
            adapter = self._orbot()
            h = adapter.health()
            results[HealthCheck.SOCKS_LISTENER] = (
                h["socks_reachable"],
                f"{h['socks_host']}:{h['socks_port']} — {h['detail']}",
            )
            return HealthReport.from_results(str(profile), results)

        if profile == NetworkProfile.TOR:
            adapter = self._tor(may_be_none=True)
            if adapter is None:
                results[HealthCheck.TOR_PROCESS] = (False, "tor binary unavailable")
                return HealthReport.from_results(str(profile), results, last_error="tor binary unavailable")
            data = adapter.health()
            for check in (HealthCheck.TOR_PROCESS, HealthCheck.SOCKS_LISTENER, HealthCheck.CONTROL_PORT, HealthCheck.BOOTSTRAP):
                key = check.value
                item = data["checks"].get(key, {"ok": False, "detail": "not checked"})
                results[check] = (item["ok"], item["detail"])
            # Proxy test is optional; include if requested.
            if include_proxy_test:
                ok, detail = self._proxy_test()
                results[HealthCheck.PROXY_REQUEST] = (ok, detail)
            if include_tor_confirmation:
                ok, detail = self._tor_confirmation_test()
                results[HealthCheck.TOR_CONFIRMATION] = (ok, detail)
            return HealthReport.from_results(str(profile), results)

        raise NetworkRuntimeError(f"Unsupported profile: {profile}")

    def _refresh_health(self) -> None:
        """Refresh persisted state from current adapter health."""
        profile = self.current_profile
        if profile == NetworkProfile.TOR:
            tor = self._tor(may_be_none=True)
            if tor is not None:
                data = tor.health()
                self.state.listener_available = data["checks"].get(HealthCheck.SOCKS_LISTENER.value, {}).get("ok", False)
                self.state.control_available = data["checks"].get(HealthCheck.CONTROL_PORT.value, {}).get("ok", False)
                self.state.bootstrap_state = data["checks"].get(HealthCheck.BOOTSTRAP.value, {}).get("detail", "unknown")
        elif profile == NetworkProfile.ORBOT:
            adapter = self._orbot()
            self.state.listener_available = adapter.health()["socks_reachable"]
        self._persist()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def _proxy_test(self) -> tuple[bool, str]:
        cfg = default_profile_config(self.current_profile)
        proxy_url = f"socks5h://{cfg.socks_host}:{cfg.socks_port}"
        try:
            req = urllib.request.Request(
                "https://check.torproject.org/api/ip",
                headers={"User-Agent": "Hive-OS/1.1"},
            )
            # Use a short timeout; failure is expected in many test environments.
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"all": proxy_url})
            )
            with opener.open(req, timeout=8) as resp:
                resp.read()
            return True, "proxied request succeeded"
        except Exception as exc:
            return False, f"proxied request failed: {exc}"

    def _tor_confirmation_test(self) -> tuple[bool, str]:
        """Explicitly confirm the current proxy route exits through Tor.

        A successful proxied request is NOT proof of Tor.  This test parses the
        check.torproject.org API response and only sets tor_confirmed=True when
        the service itself reports IsTor=true.
        """
        cfg = default_profile_config(self.current_profile)
        proxy_url = f"socks5h://{cfg.socks_host}:{cfg.socks_port}"
        try:
            req = urllib.request.Request(
                "https://check.torproject.org/api/ip",
                headers={"User-Agent": "Hive-OS/1.1"},
            )
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"all": proxy_url})
            )
            with opener.open(req, timeout=8) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return False, "Tor check returned non-JSON response"
            if data.get("IsTor") is True:
                return True, "Tor confirmed by check.torproject.org"
            if data.get("IsTor") is False:
                return False, "check.torproject.org reports IsTor=false"
            return False, "Tor check response missing IsTor field"
        except Exception as exc:
            return False, f"Tor confirmation request failed: {exc}"

    def test(self) -> dict[str, Any]:
        report = self.health(include_proxy_test=True, include_tor_confirmation=True)
        return report.to_dict()

    def newnym(self, timeout: float = 10.0) -> dict[str, Any]:
        if self.current_profile != NetworkProfile.TOR:
            raise TorNotAvailableError("NEWNYM is only supported for the TOR profile")
        adapter = self._tor(may_be_none=True)
        if adapter is None:
            raise TorNotAvailableError("tor binary unavailable")
        return adapter.newnym(timeout=timeout)

    # ------------------------------------------------------------------
    # Proxy execution
    # ------------------------------------------------------------------
    def proxy_env(self, base_env: dict[str, str] | None = None) -> dict[str, str]:
        """Return proxy-aware environment.

        When base_env is provided, proxy variables are added/removed from that
        base instead of from raw os.environ.  This lets the Supervisor pass the
        manifest-filtered environment and avoid leaking arbitrary host variables
        that the manifest did not explicitly allow.
        """
        return build_proxy_env(self.current_profile, base_env=base_env or os.environ)

    def can_run_proxy(self) -> tuple[bool, str]:
        allowed, reason = is_proxy_execution_allowed(self.state)
        return allowed, reason

    # ------------------------------------------------------------------
    # API for PASS C supervisor
    # ------------------------------------------------------------------
    def requirement_satisfied(self, *, network_required: bool = False, required_profile: str | None = None) -> tuple[bool, str]:
        """Check whether current network state satisfies a service requirement."""
        profile = self.current_profile
        if profile == NetworkProfile.HOLD:
            return False, "profile is HOLD"
        if required_profile is not None:
            want = required_profile.lower()
            if want == "proxied":
                if profile not in (NetworkProfile.TOR, NetworkProfile.ORBOT):
                    return False, f"requires a proxied profile; current is {profile}"
            elif want == "any":
                # any means any active non-HIVE network profile
                if profile not in (NetworkProfile.DIRECT, NetworkProfile.TOR, NetworkProfile.ORBOT):
                    return False, f"requires a non-HOLD network profile; current is {profile}"
            else:
                try:
                    want_enum = NetworkProfile.from_name(want)
                except ValueError:
                    return False, f"unknown required profile: {required_profile}"
                if profile != want_enum:
                    return False, f"requires {want}; current is {profile}"
        elif network_required and profile == NetworkProfile.DIRECT:
            # Service requires network but has no specific profile: DIRECT is acceptable.
            return True, "direct networking available"
        # For specific proxied profiles, verify basic health if possible.
        if network_required and profile in (NetworkProfile.TOR, NetworkProfile.ORBOT):
            report = self.health()
            if report.level == HealthLevel.UNAVAILABLE:
                return False, f"network unavailable: {report.overall}"
        return True, "network requirement satisfied"
