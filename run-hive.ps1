# Hive OS Windows development/portable launcher wrapper.
# This script only delegates to the existing bin\hive launcher.
# Hive OS is primarily an Android/Termux/Linux runtime; Windows support is for development/testing only.

$HiveRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$HiveBin = Join-Path $HiveRoot "bin\hive"
& python $HiveBin @args
