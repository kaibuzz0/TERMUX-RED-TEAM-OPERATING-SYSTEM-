# Isolated Physical Termux Validation Checklist

**Milestone 4 — Controlled mutation inside one validated temporary root**

This checklist performs controlled, reversible operations inside a single isolated test directory. It does not claim to be read-only or non-mutating. It makes no changes outside the chosen test root.

## Pre-conditions

- Physical Android device with Termux installed from F-Droid or GitHub release.
- Python and Bash available in Termux.
- Git available (optional).
- No root required.
- Enough free storage to copy the repository.

## Isolated test root

All steps below use a single test root. Resolve it once and verify it before cleanup.

```bash
export HIVE_TEST_ROOT="${TMPDIR}/hive-m4-test-$$"
mkdir -p "$HIVE_TEST_ROOT"
```

## Steps

1. **Deploy the repository into the test root**
   ```bash
   cp -r "$HOME/TERMUX-RED-TEAM-OPERATING-SYSTEM-" "$HIVE_TEST_ROOT/repo" ||      git clone https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-.git "$HIVE_TEST_ROOT/repo"
   cd "$HIVE_TEST_ROOT/repo"
   ```

2. **Verify launcher interpreter**
   ```bash
   head -n 1 "Hive Ops Final/bin/hive"
   python3 -m py_compile "Hive Ops Final/bin/hive"
   ```

3. **Verify repository-level dispatcher**
   ```bash
   python3 bin/hive --resolve
   ```

4. **Test `--help` does not mutate outside the test root**
   ```bash
   python3 "Hive Ops Final/bin/hive" --help
   test ! -e "$HOME/hive"
   test ! -e "/root/hive"
   ```

5. **Test launch from outside the repository**
   ```bash
   cd "$HIVE_TEST_ROOT"
   python3 "$HIVE_TEST_ROOT/repo/Hive Ops Final/bin/hive" --help
   ```

6. **Test with environment overrides**
   ```bash
   export HIVE_HOME="$HIVE_TEST_ROOT/hive-home"
   export HIVE_CONFIG_ROOT="$HIVE_TEST_ROOT/hive-config"
   python3 "$HIVE_TEST_ROOT/repo/Hive Ops Final/bin/hive" --help
   test ! -e "$HIVE_HOME"
   test ! -e "$HIVE_CONFIG_ROOT"
   ```

7. **Test path with spaces (copy into test root)**
   ```bash
   cp -r "$HIVE_TEST_ROOT/repo" "$HIVE_TEST_ROOT/hive repo"
   python3 "$HIVE_TEST_ROOT/hive repo/Hive Ops Final/bin/hive" --help
   ```

8. **Test `env.sh` sourcing**
   ```bash
   source "$HIVE_TEST_ROOT/repo/Hive Ops Final/etc/env.sh"
   echo "$HIVE_HOME"
   echo "$HIVE_OS"
   echo "$HIVE_SWARM"
   echo "$HIVE_FINAL"
   [[ "$HIVE_OS" != */root/* ]] && echo "OK: no /root in HIVE_OS" || echo "FAIL: /root in HIVE_OS"
   [[ "$HIVE_SWARM" != */root/* ]] && echo "OK: no /root in HIVE_SWARM" || echo "FAIL: /root in HIVE_SWARM"
   ```

9. **Test `services.json` parsing**
   ```bash
   python3 -c "import json; d=json.load(open('$HIVE_TEST_ROOT/repo/Hive Ops Final/etc/services.json')); print(d['version']); print(list(d['services'].keys()))"
   grep -q '/root/hive' "$HIVE_TEST_ROOT/repo/Hive Ops Final/etc/services.json" && echo "FAIL" || echo "OK"
   ```

10. **Runtime capability report**
    ```bash
    python3 "$HIVE_TEST_ROOT/repo/bin/hive" --runtime-info --json | head -c 2000
    ```

## Cleanup (validated, guarded)

1. Print the test root.
2. Verify a marker file exists inside it.
3. Remove only the test root.

```bash
printf 'Test root: %s\n' "$HIVE_TEST_ROOT"
if [ -d "$HIVE_TEST_ROOT/repo" ] && [ -f "$HIVE_TEST_ROOT/repo/hive-canonical.json" ]; then
    rm -rf "$HIVE_TEST_ROOT"
    echo "Cleanup complete"
else
    echo "Refusing cleanup: test root marker missing"
fi
```

## Expected results

- `--help` returns exit code 0.
- No directories created outside `$HIVE_TEST_ROOT` during `--help`.
- `env.sh` and `services.json` contain no `/root/hive` references.
