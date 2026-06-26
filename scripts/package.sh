#!/usr/bin/env bash
# Package a built variant into a standalone, runnable zip.
#
# Usage: scripts/package.sh <stock|extended> [version]
#
# Output: dist/Pokemon_Yellow_<Cap>_<version>.zip  (dist/ is gitignored).
# PRIVATE artifact: the zip bundles the ROM (the stock ROM is literally
# copyrighted Yellow; the extended ROM is ROM-derivative). Do NOT distribute —
# this is for local/personal use only, which is why dist/ is never committed.
set -euo pipefail
V="${1:?usage: scripts/package.sh <stock|extended> [version]}"
VER="${2:-v0.0.3}"
case "$V" in
  extended) OUT=recomp;       CAP=Extended;;
  stock)    OUT=recomp_stock; CAP=Stock;;
  *) echo "variant must be stock|extended"; exit 1;;
esac

P="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$P/$OUT/build"
EXE="$BUILD/Pokemon_Yellow_$CAP.exe"
ROM="$BUILD/rom_$V.gbc"
MGW=/c/msys64/mingw64/bin
[ -f "$EXE" ] || { echo "build it first: scripts/build.sh $V"; exit 1; }
[ -f "$ROM" ] || { echo "ROM missing ($ROM) — re-run scripts/build.sh $V"; exit 1; }

STAGE="$P/dist/Pokemon_Yellow_${CAP}_$VER"
ZIP="$P/dist/Pokemon_Yellow_${CAP}_$VER.zip"
rm -rf "$STAGE" "$ZIP"; mkdir -p "$STAGE"

cp "$EXE" "$STAGE/"
cp "$ROM" "$STAGE/rom_$V.gbc"
printf 'rom_%s.gbc\n' "$V" > "$STAGE/rom.cfg"   # relative -> resolves next to the exe

# Auto-derive the DLL set: walk the exe's import table transitively, bundling
# only DLLs that live in the mingw64 toolchain dir (system DLLs ship with
# Windows). This self-adjusts to the build — e.g. with GBRT_NETPLAY off there's
# no libcurl tree, so it drops from ~23 to ~7 DLLs automatically.
declare -A seen
queue=("$EXE")
# Seed DLLs that SDL dlopen's at runtime (not in the static import table, so the
# import walk alone misses them): the ANGLE EGL driver. The walk then pulls their
# own deps. Without this the package builds but fails at GL-context creation.
for r in libEGL; do
  if [ -f "$MGW/$r.dll" ] && [ -z "${seen[$r.dll]:-}" ]; then
    seen[$r.dll]=1; cp "$MGW/$r.dll" "$STAGE/"; queue+=("$MGW/$r.dll")
  fi
done
while [ ${#queue[@]} -gt 0 ]; do
  cur="${queue[0]}"; queue=("${queue[@]:1}")
  for d in $(objdump.exe -p "$cur" 2>/dev/null | sed -n 's/.*DLL Name:[[:space:]]*//p' | tr -d '\r'); do
    if [ -f "$MGW/$d" ] && [ -z "${seen[$d]:-}" ]; then
      seen[$d]=1; cp "$MGW/$d" "$STAGE/"; queue+=("$MGW/$d")
    fi
  done
done
echo "  bundled ${#seen[@]} runtime DLLs"

# tiny run.bat so the cfg/saves resolve next to the exe regardless of how it's launched
cat > "$STAGE/run.bat" <<BAT
@echo off
cd /d "%~dp0"
start "" "Pokemon_Yellow_$CAP.exe" %*
BAT

# zip via PowerShell Compress-Archive (always available on Windows)
PS="/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
"$PS" -NoProfile -Command \
  "Compress-Archive -Path '$(cygpath -w "$STAGE")\\*' -DestinationPath '$(cygpath -w "$ZIP")' -Force"

echo "PACKAGED: dist/Pokemon_Yellow_${CAP}_$VER.zip  ($(du -h "$ZIP" | cut -f1)), $(ls "$STAGE" | wc -l) files"
echo "  contents: Pokemon_Yellow_$CAP.exe + ${#seen[@]} DLLs + rom_$V.gbc + rom.cfg + run.bat"
