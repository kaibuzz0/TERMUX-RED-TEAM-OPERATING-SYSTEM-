"""Targeted tests for Hive OS 1.0.1 Termux dependency split / installer repair.

Covers:
- Runtime requirements file exists and contains only core packages
- Runtime requirements do NOT contain dev/AI/network-only packages
- Core CLI imports succeed with runtime dependency set
- Full requirements remain available for optional/dev use
- README and website install instructions updated
"""

import ast
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_REQS = REPO_ROOT / "requirements-runtime.txt"
EXTRAS_REQS = REPO_ROOT / "requirements-extras.txt"
DEV_REQS = REPO_ROOT / "requirements-dev.txt"
FULL_REQS = REPO_ROOT / "requirements.txt"
INSTALLER = REPO_ROOT / "install-termux-easy.sh"
README = REPO_ROOT / "README.md"
WEBSITE = REPO_ROOT / "docs" / "index.html"

CORE_DIRS = [
    REPO_ROOT / "bin",
    REPO_ROOT / "lib",
    REPO_ROOT / "config_engine",
    REPO_ROOT / "policy_engine",
    REPO_ROOT / "hive_broker",
    REPO_ROOT / "operations_center",
    REPO_ROOT / "services",
    REPO_ROOT / "installer",
    REPO_ROOT / "security",
    REPO_ROOT / "plugin_sdk",
    REPO_ROOT / "release_engine",
    REPO_ROOT / "updates",
]


def _parse_requirements(path: Path) -> set[str]:
    """Return normalized package names from a requirements file."""
    pkgs = set()
    if not path.exists():
        return pkgs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip version specifiers and extras
        name = line.split("=")[0].split("[")[0].split(">")[0].split("<")[0].strip().lower()
        if name:
            pkgs.add(name)
    return pkgs


def _stdlib_modules() -> set[str]:
    stdlib = set(sys.builtin_module_names)
    stdlib |= {
        "argparse", "base64", "collections", "concurrent", "copy", "dataclasses",
        "datetime", "enum", "errno", "getpass", "hashlib", "json", "os", "pathlib",
        "platform", "re", "secrets", "shutil", "signal", "socket", "stat",
        "subprocess", "sys", "tarfile", "tempfile", "time", "typing", "uuid",
        "zipfile", "inspect", "textwrap", "logging", "threading", "numbers",
        "decimal", "fractions", "html", "http", "ftplib", "imaplib", "smtplib",
        "xml", "csv", "io", "warnings", "traceback", "types", "functools",
        "itertools", "math", "random", "string", "difflib", "filecmp", "fnmatch",
        "glob", "linecache", "pickle", "marshal", "dbm", "shelve", "bisect",
        "heapq", "array", "weakref", "contextlib", "abc", "zoneinfo", "calendar",
        "timeit", "profile", "pstats", "unittest", "doctest", "pdb", "code",
        "codeop", "compileall", "py_compile", "symtable", "token", "tokenize",
        "keyword", "dis", "pickletools", "lib2to3", "msilib", "msvcrt", "winreg",
        "winsound", "nis", "grp", "pwd", "spwd", "crypt", "termios", "tty",
        "pty", "fcntl", "resource", "syslog", "optparse", "getopt", "readline",
        "rlcompleter", "netrc", "plistlib", "mailbox", "mimetypes", "binhex",
        "binascii", "quopri", "uu", "encodings", "locale", "gettext", "cmd",
        "shlex", "tkinter", "idlelib", "turtledemo", "turtle", "pydoc",
        "ensurepip", "venv", "zipapp", "modulefinder", "runpy", "importlib",
        "pkgutil", "zipimport", "hmac", "configparser", "contextvars", "queue",
        "selectors", "socketserver", "urllib", "importlib.metadata",
    }
    return stdlib


def _collect_third_party_imports() -> set[str]:
    """Scan core Python files for non-stdlib imports."""
    stdlib = _stdlib_modules()
    found = set()
    for directory in CORE_DIRS:
        if not directory.is_dir():
            continue
        for root, _dirs, files in os.walk(directory):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = Path(root) / f
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top = alias.name.split(".")[0]
                            if top not in stdlib and not top.startswith("__"):
                                found.add(top.lower())
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            top = node.module.split(".")[0]
                            if top not in stdlib and not top.startswith("__"):
                                found.add(top.lower())
    return found


class TermuxDependencyRepairTests(unittest.TestCase):
    """Regression tests for dependency split and installer repair."""

    # ── File existence ──
    def test_runtime_requirements_exists(self):
        self.assertTrue(RUNTIME_REQS.exists(), "requirements-runtime.txt must exist")

    def test_extras_requirements_exists(self):
        self.assertTrue(EXTRAS_REQS.exists(), "requirements-extras.txt must exist")

    def test_dev_requirements_exists(self):
        self.assertTrue(DEV_REQS.exists(), "requirements-dev.txt must exist")

    def test_full_requirements_preserved(self):
        self.assertTrue(FULL_REQS.exists(), "original requirements.txt must be preserved")

    # ── Runtime contents ──
    def test_runtime_contains_pyyaml(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        self.assertIn("pyyaml", pkgs, "runtime must include pyyaml")

    def test_runtime_contains_cryptography(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        self.assertIn("cryptography", pkgs, "runtime must include cryptography")

    def test_runtime_does_not_contain_numpy(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        self.assertNotIn("numpy", pkgs, "runtime must NOT include numpy")

    def test_runtime_does_not_contain_matplotlib(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        self.assertNotIn("matplotlib", pkgs, "runtime must NOT include matplotlib")

    def test_runtime_does_not_contain_nltk(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        self.assertNotIn("nltk", pkgs, "runtime must NOT include nltk")

    def test_runtime_does_not_contain_dev_packages(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        for dev in ("pytest", "pytest-cov", "pytest-asyncio", "black", "flake8", "mypy"):
            self.assertNotIn(dev, pkgs, f"runtime must NOT include {dev}")

    def test_runtime_does_not_contain_legacy_network_packages(self):
        pkgs = _parse_requirements(RUNTIME_REQS)
        for pkg in ("scapy", "paramiko", "dnspython", "beautifulsoup4", "pynacl", "bcrypt"):
            self.assertNotIn(pkg, pkgs, f"runtime must NOT include {pkg}")

    # ── Extras contents ──
    def test_extras_contains_numpy(self):
        pkgs = _parse_requirements(EXTRAS_REQS)
        self.assertIn("numpy", pkgs, "extras should include numpy for legacy AI use")

    def test_extras_contains_matplotlib(self):
        pkgs = _parse_requirements(EXTRAS_REQS)
        self.assertIn("matplotlib", pkgs, "extras should include matplotlib")

    def test_extras_contains_nltk(self):
        pkgs = _parse_requirements(EXTRAS_REQS)
        self.assertIn("nltk", pkgs, "extras should include nltk")

    # ── Dev contents ──
    def test_dev_contains_pytest(self):
        pkgs = _parse_requirements(DEV_REQS)
        self.assertIn("pytest", pkgs, "dev should include pytest")

    # ── Import audit: core code only needs runtime packages ──
    def test_core_imports_subset_of_runtime(self):
        """All third-party imports in core code must be in runtime requirements."""
        imports = _collect_third_party_imports()
        runtime = _parse_requirements(RUNTIME_REQS)
        # Known internal packages are OK
        internals = {
            "config_engine", "policy_engine", "hive_broker", "operations_center",
            "services", "installer", "security", "plugin_sdk", "release_engine",
            "updates", "lib", "version", "schema", "network",
        }
        # Import name → PyPI package name mappings
        import_to_pkg = {
            "yaml": "pyyaml",
        }
        mapped = {import_to_pkg.get(i, i) for i in imports}
        # psutil is imported only inside win32 conditional try blocks;
        # Linux/Termux uses /proc fallback, so it is optional.
        allowed_optional = {"psutil"}
        unexpected = mapped - runtime - internals - allowed_optional
        self.assertEqual(
            unexpected, set(),
            f"Core runtime code imports packages not in requirements-runtime.txt: {unexpected}"
        )

    # ── Installer audit ──
    def test_installer_uses_runtime_requirements(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("requirements-runtime.txt", text,
                        "install-termux-easy.sh must install runtime requirements")
        self.assertNotIn("requirements.txt", text,
                         "install-termux-easy.sh must NOT reference full requirements.txt")

    def test_installer_uses_master_not_old_tag(self):
        text = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("master", text,
                        "install-termux-easy.sh must clone master branch")
        self.assertNotIn("hive-os-v1.0.0", text,
                         "install-termux-easy.sh must NOT reference old v1.0.0 tag")

    # ── README audit ──
    def test_readme_shows_runtime_install(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("requirements-runtime.txt", text,
                        "README must document runtime requirements install")

    def test_readme_uses_master_branch(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("--branch master", text,
                        "README must reference master branch for current install")

    # ── Website audit ──
    def test_website_shows_runtime_install(self):
        text = WEBSITE.read_text(encoding="utf-8")
        self.assertIn("requirements-runtime.txt", text,
                        "Website must document runtime requirements install")

    def test_website_uses_master_branch(self):
        text = WEBSITE.read_text(encoding="utf-8")
        self.assertIn("--branch master", text,
                        "Website must reference master branch for current install")


if __name__ == "__main__":
    unittest.main()
