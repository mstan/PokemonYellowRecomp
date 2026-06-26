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

# Runtime DLL set (23), derived from a live instance's loaded modules
# (PowerShell: (Get-Process ...).Modules | ? FileName -like *msys64*). Identical
# for both variants — shared SDL/ANGLE/curl runtime. Re-derive if the runtime changes.
DLLS=(libbrotlicommon libbrotlidec libcrypto-3-x64 libcurl-4 libEGL libgcc_s_seh-1
  libGLESv2 libiconv-2 libidn2-0 libintl-8 libnghttp2-14 libnghttp3-9
  libngtcp2_crypto_ossl-0 libngtcp2-16 libpsl-5 libssh2-1 libssl-3-x64 libstdc++-6
  libunistring-5 libwinpthread-1 libzstd SDL2 zlib1)
for d in "${DLLS[@]}"; do cp "$MGW/$d.dll" "$STAGE/"; done

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
echo "  contents: Pokemon_Yellow_$CAP.exe + 23 DLLs + rom_$V.gbc + rom.cfg + run.bat"
