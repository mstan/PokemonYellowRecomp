#!/usr/bin/env bash
# Build a variant end-to-end: ROM (inject if extended) -> static recompile ->
# native exe, then stage its ROM + rom.cfg next to the exe.
#
# Usage: scripts/build.sh <stock|extended>
#
# stock and extended both build to pokeyellow/pokeyellow.gbc and each exe
# SHA-verifies its ROM at runtime, so we copy the ROM to rom_<variant>.gbc in
# the build dir and point that build's rom.cfg at it (the two never collide).
set -euo pipefail
V="${1:?usage: scripts/build.sh <stock|extended>}"
case "$V" in
  extended) TOML=pokeyellow_recomp.toml;       OUT=recomp;       CAP=Extended;;
  stock)    TOML=pokeyellow_stock_recomp.toml; OUT=recomp_stock; CAP=Stock;;
  *) echo "variant must be stock|extended"; exit 1;;
esac

export PATH="/c/msys64/mingw64/bin:/c/msys64/usr/bin:/c/Windows/system32"
export TMPDIR="C:/msys64/tmp" TMP="C:/msys64/tmp" TEMP="C:/msys64/tmp"
P="$(cd "$(dirname "$0")/.." && pwd)"
cd "$P"
RGBDS="$P/tools/rgbds/"
GBRECOMP="/f/Projects/gbcrecomp/gb-recompiled/build/bin/gbrecomp.exe"
MGW=/c/msys64/mingw64/bin

echo "== [$V] reset pokeyellow to a clean tree =="
git -C pokeyellow checkout . >/dev/null 2>&1
git -C pokeyellow clean -fd >/dev/null 2>&1

if [ "$V" = extended ]; then
  echo "== [$V] inject Gen2 content (full Johto dex) =="
  python3 inject_gen2.py
fi

echo "== [$V] build ROM =="
( cd pokeyellow && "$MGW/mingw32-make.exe" pokeyellow.gbc RGBDS="$RGBDS" -j4 )
echo "   ROM sha1: $(sha1sum pokeyellow/pokeyellow.gbc | cut -d' ' -f1)"

echo "== [$V] static recompile + native build =="
"$GBRECOMP" --config "$TOML"
"$MGW/cmake.exe" -G Ninja -S "$OUT" -B "$OUT/build"
"$MGW/ninja.exe" -C "$OUT/build"

echo "== [$V] stage ROM + rom.cfg next to the exe =="
cp pokeyellow/pokeyellow.gbc "$OUT/build/rom_$V.gbc"
echo "$P/$OUT/build/rom_$V.gbc" > "$OUT/build/rom.cfg"

echo "BUILT: $OUT/build/Pokemon_Yellow_$CAP.exe  (run via launcher: YELLOW_VARIANT=$V ./yellow.exe)"
