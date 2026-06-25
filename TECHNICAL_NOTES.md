# Pokémon Yellow Decomp — Technical Notes

How this project extends Pokémon Yellow and runs it natively. Covers the
end-to-end pipeline, the build, **adding new Pokémon** (incl. **back-porting
from Gen 2**), and **migrating saves** across save-format changes.

---

## 0. The pipeline (and why each step exists)

```
pret pokeyellow (GB assembly)
      │  edit SOURCE (data + a little engine)        ← extensibility lives here
      ▼
   RGBDS build  ──▶  modified pokeyellow.gbc  (a real, valid GB ROM)
      │  static recompile
      ▼
   gbrecomp  ──▶  Pokemon_Yellow.exe (native C → binary)
      │  run
      ▼
   our SDL/ANGLE runner  (loads the .gbc at runtime, SHA-256-verified)
```

Key facts:

- **We edit pret SOURCE, not the ROM binary.** New content (Pokémon, moves,
  maps) is added as assembly/data in the decomp, then reassembled by RGBDS.
  Never hand-patch the `.gbc`.
- **The recompiler is required to get a native binary.** A decomp only builds
  a ROM. There is no "decomp → native" shortcut; the ROM is fed to `gbrecomp`.
- **Content vs. behavior** — the rule of thumb for extensibility:
  - *New content* (a new Pokémon's stats/sprite/dex) → **decomp source** (this
    doc, §2). Zero runtime cost; one source of truth.
  - *Live behavior* (cheats, inject an already-defined mon into the party,
    overlays, render tweaks) → **post-recomp runtime hooks** in the runner
    (`game_extras`: `game_on_frame` / `game_dispatch_override` /
    `game_draw_overlay`) + direct `GBContext` memory access. This is the
    "widescreen-mod" style of the SNES/N64 recomp projects.
- **Distribution model** (for a launcher): ship a **BPS patch** (stock→extended
  byte-diff) + the pre-recompiled binaries; the user supplies their own stock
  ROM. Never distribute the ROM. The launcher SHA-verifies the stock ROM, then
  applies the patch on the fly if the user opts into the extended experience.

---

## 1. Building

Requirements: msys2 mingw64 (gcc/make), **RGBDS 1.0.1** (prebuilt in
`tools/rgbds/`), Python 3 + Pillow (for sprite conversion).

> **Gotcha:** use **`mingw32-make`, NOT msys2 `/usr/bin/make`.** The msys make
> passes an empty `TEMP` to recipes, so gcc/rgbgfx fall back to `C:\Windows\`
> (not writable) and the build dies with "Cannot create temporary file" / 233
> missing-`.2bpp` errors. Create drive-relative tmp dirs once
> (`mkdir -p /f/tmp /c/tmp /c/msys64/tmp`) — native gcc resolves `/tmp`
> drive-relative.

```bash
cd pokeyellow
export CLEAN_PATH="/c/msys64/mingw64/bin:/c/msys64/usr/bin:/c/Windows/system32:/c/Windows"
PATH="$CLEAN_PATH" TMPDIR="C:/msys64/tmp" TMP="C:/msys64/tmp" TEMP="C:/msys64/tmp" \
  /c/msys64/mingw64/bin/mingw32-make.exe pokeyellow.gbc \
  RGBDS="F:/Projects/gbcrecomp/PokemonYellowDecomp/tools/rgbds/" -j4
```

Verify a clean checkout reproduces the stock ROM byte-for-byte:
`sha1sum pokeyellow.gbc` → `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1`.

> The **debug** ROM (`pokeyellow_debug.gbc`) currently overflows ROM0 by ~15
> bytes because the `GetName` fix (§2.4) grows the Home bank. Build only the
> non-debug target until ~15 bytes are freed in bank 0.

To recompile the modified ROM into a native binary, see
`../pokeyellow_recomp.toml` and run `gbrecomp --config`.

---

## 2. Adding a new Pokémon

A species touches ~12 places. Tables are either **internal-index ordered**
(append at the species' index slot) or **Pokédex-ordered** (append at its dex
number). Mixing these up is the most common mistake — `assert_table_length`
in each file will catch a miscount, so **build often and let the asserts guide
you.**

The whole process is automated in **`../inject_gen2.py`** (idempotent: data
inserts + ASM edits + the engine fixes below + Pillow sprite conversion). Read
it as the worked example; the manual checklist:

### 2.1 Constants
- `constants/pokemon_constants.asm` — internal index. **Append** a `const NAME`
  (new mon get the next free index). *Watch the `HM01` ceiling — see §2.4.*
- `constants/pokedex_constants.asm` — `const DEX_NAME` + bump `NUM_POKEMON`.

### 2.2 Stats / names / dex (data)
- `data/pokemon/base_stats/<mon>.asm` (+ `INCLUDE` it in `base_stats.asm`,
  **dex order**, before `assert_table_length NUM_POKEMON`).
- `names.asm`, `cries.asm`, `dex_order.asm` — **internal-index order** (append).
- `palettes.asm` (`assert NUM_POKEMON+1`), `menu_icons.asm` — **dex order**.
- `evos_moves.asm` — add a `dw <Mon>EvosMoves` to the **pointer table**
  (internal order) **and** a data block (`EVOLVE_LEVEL,lvl,target` + learnset).
- `dex_entries.asm` — `dw <Mon>DexEntry` to the pointer table (internal order)
  + a data block (`db "CATEGORY@"`, height `db ft,in`, weight `dw tenths_lb`,
  `text_far _<Mon>DexEntry`, `text_end`). Add the text to `dex_text.asm`.

### 2.3 Sprites
- Drop `gfx/pokemon/front/<mon>.png` and `gfx/pokemon/back/<mon>b.png`. The
  build generates `.2bpp` → `.pic` automatically (`rgbgfx` + `pkmncompress`).
- Front: up to 7×7 tiles, **square**; back: **32×32 (4×4)**; both **4-shade
  grayscale**.
- Add `INCBIN` labels in `gfx/pics.asm`: `<Mon>PicFront::`, `<Mon>PicBack::`.

### 2.4 Engine changes the new mon may force (the non-obvious part)

- **Pic bank routing (`home/pics.asm`).** A mon's pic bank is chosen by
  **internal-index range** (hard-coded). Indexes `>= $99` map to "Pics 5",
  which is full — so new high-index mon need a new bank. We added a
  `SECTION "Pics Gen2"` and a route: `cp CHIKORITA / jr nc → BANK("Pics Gen2")`.
- **`GetName` ceiling (`home/names2.asm`).** Gen 1 has a BUG: the "generate
  TM/HM name" shortcut (`cp HM01 / jp nc GetMachineName`) ran for **every**
  name list, capping Pokémon/move/trainer indexes below `HM01` (`$C5`). We
  fixed it to gate on `wNameListType == ITEM_NAME`, so the Pokédex can exceed
  190 indexes. (This is what makes >9 extra mon possible. It grows the Home
  bank ~10 bytes — fine for the release ROM, overflows the debug ROM.)
- **WRAM / save layout (`ram/wram.asm`, `layout.link`).** `NUM_POKEMON`
  feeds `flag_array NUM_POKEMON` for `wPokedexOwned` / `wPokedexSeen`. Every
  time `NUM_POKEMON` crosses a multiple of 8, **each array grows 1 byte** (so
  +2 total). That overflowed WRAM; we trimmed the stack (`ds $eb-1` → `$eb-3`)
  and nudged its pin (`org $df15` → `$df17`). **This also changes the save
  format — see §3.**

### 2.5 Back-porting a Pokémon from Gen 2 (pokecrystal)

Donor data lives in `pokecrystal/data/pokemon/` and
`pokecrystal/gfx/pokemon/<mon>/`. Translating Gen 2 → Gen 1:

| Field | Gen 2 (Crystal) | Gen 1 (Yellow) |
|---|---|---|
| Stats | `hp atk def spd sat sdf` | merge → `hp atk def spd spc`; **Special = Sp.Atk (`sat`)** |
| Items / gender / egg groups / hatch | present | **drop** (don't exist in Gen 1) |
| Types | any | must be a **Gen 1 type** (no Dark/Steel — those need adding, big job) |
| Level-up / TM learnset | Gen 2 moves | **remap to Gen-1-only moves** (Gen-2-exclusive moves don't exist) |
| Front sprite | `front.png` = a **vertical anim sheet** `W×N` | crop the **top `W×W` frame**, recolor to 4-gray |
| Back sprite | `back.png` 48×48 (6×6) | **resize to 32×32 (4×4)**, recolor to 4-gray |
| Special (Gen-1 value) | n/a for Johto mon | `pokecrystal/.../gen1_base_special.asm` only lists **Kanto** mon; for Johto mon use `sat` |

Sprite conversion is done with Pillow in `inject_gen2.py` (`quant4()` maps to
4 gray levels; front = `crop((0,0,W,W))`, back = `resize((32,32))`). Catch rate
/ base exp / growth rate copy over directly.

---

## 3. Migrating a save across a save-format change

**Why it's needed.** Adding mon (§2.4) grew `wPokedexOwned`/`wPokedexSeen` by
+1 byte **each** (19→20) inside the *saved* main data. Everything after the dex
arrays shifts, and the checksum range grows. **A stock Yellow save will not load
in the extended ROM** (offsets + checksum mismatch → the game shows NEW GAME
instead of CONTINUE). Conversely an extended save won't load in stock.

This is a real "save-version" problem: the extended build effectively has its
own save format. For distribution, treat extended saves as a separate slot, or
ship a migrator like the one below.

### Save layout (from this build's `pokeyellow.sym`)

Gen 1 SRAM is 32 KB (4 × 8 KB banks); the `.sav` mirrors it linearly, so for an
SRAM bank `B` address `$Axxx`, **file offset = `B*0x2000 + (addr - 0xA000)`**.
The save data is in bank 1:

| Symbol | SRAM | **File offset** | Notes |
|---|---|---|---|
| `sGameData` / `sPlayerName` | `01:a598` | `0x2598` | name, 11 bytes; checksum starts here |
| `sMainData` | `01:a5a3` | `0x25A3` | starts with `wPokedexOwned` |
| → `wPokedexOwned` | | `0x25A3` | **20 B** extended (19 stock) |
| → `wPokedexSeen` | | `0x25B7` (ext) | **20 B** extended (19 stock) |
| `sSpriteData` | `01:ad2e` | `0x2D2E` (ext) | |
| `sPartyData` | `01:af2e` | **`0x2F2E`** (ext; `0x2F2C` stock = +2) | the party |
| `sCurBoxData` | `01:b0c2` | `0x30C2` (ext) | |
| `sTileAnimations` | `01:b524` | `0x3524` (ext) | last checksummed byte |
| `sMainDataCheckSum` | `01:b525` | `0x3525` (ext) | the checksum byte |

**Party block** (`sPartyData`, 404 bytes): `count` (1) · `species[6]+0xFF` (7)
· `6 × party_struct` (44 each) · `OT names` (6×11) · `nicknames` (6×11).
`party_struct` = Species, HP(2), BoxLevel, Status, Type1, Type2, CatchRate,
Moves(4), OTID(2), Exp(3), 5×StatExp(2), DVs(2), PP(4), Level, MaxHP(2),
Atk(2), Def(2), Spd(2), Spc(2). (See `macros/ram.asm`.)

**Checksum** (`engine/menus/save.asm`): `CalcCheckSum(sGameData,
sGameDataEnd-sGameData)` = 8-bit sum of bytes `0x2598..0x3524`, then complement
(`XOR $FF`); stored at `0x3525`. Recompute after any edit.

### Migration recipe (stock → extended)

1. Copy `0x0000..0x25A2` unchanged (sprite buffers, HoF, player name, up to the
   dex).
2. `wPokedexOwned`: write the stock 19 bytes + **1 zero** (→ 20).
3. `wPokedexSeen`: write the stock 19 bytes + **1 zero** (→ 20).
4. Copy the rest of stock `sMainData` onward, **shifted +2** (sprite data, party,
   box, tile-anim).
5. (Optional) overwrite `sPartyData` with the party you want (internal-index
   species bytes; e.g. Pikachu `$54`, Chikorita `$BF`, Cyndaquil `$C2`,
   Totodile `$C5`).
6. Recompute the checksum over `0x2598..0x3524` and write it at `0x3525`.

Editing an **extended** save in place (no migration) = just steps 5–6.

> **PKHeX won't help for the new mon** — it only knows the official dex
> (1–151); our additions live at internal indexes `$BF+`, which PKHeX treats as
> glitch mon. Edit the party bytes directly (internal indexes) instead.

### Where the runner reads the save

The runner persists battery SRAM as a `.sav` co-located with the binary
(`sdl_get_persistent_path(rom_name, ".sav")`). Drop the migrated/edited `.sav`
next to `Pokemon_Yellow.exe` (run once and let it create one to confirm the
exact filename), then boot → **CONTINUE**.
