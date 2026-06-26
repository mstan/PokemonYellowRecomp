#!/usr/bin/env bash
# Build yellow.exe (the stock/extended launcher) into the repo root and drop a
# default yellow.cfg next to it. Run from anywhere.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
/c/msys64/mingw64/bin/gcc.exe -O2 -o "$ROOT/yellow.exe" "$HERE/yellow.c"
[ -f "$ROOT/yellow.cfg" ] || cp "$HERE/yellow.cfg" "$ROOT/yellow.cfg"
echo "built $ROOT/yellow.exe  (variant cfg: $ROOT/yellow.cfg)"
