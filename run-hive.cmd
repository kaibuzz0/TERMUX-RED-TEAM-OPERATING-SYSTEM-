@echo off
REM Hive OS Windows development/portable launcher wrapper.
REM This script only delegates to the existing bin\hive launcher.
REM Hive OS is primarily an Android/Termux/Linux runtime; Windows support is for development/testing only.

set "HIVE_ROOT=%~dp0"
python "%HIVE_ROOT%bin\hive" %*
