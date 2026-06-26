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
   gbrecomp  ──▶  Pokemon_Yellow_Extended.exe (native C → binary)
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
- **Distribution model: source only — no ROM, binary, or BPS.** The repo ships
  scripts + pinned pret commits; the user builds the ROM locally from pret.
  A BPS was rejected because its diff still encodes the Crystal-derived
  (copyrighted) sprites/data/text we add — only a diff that is *entirely your own
  work* is a clean patch, and ours isn't. `inject_gen2.py` is the on-the-fly
  extractor: it pulls Gen-2 content from **pokecrystal's source** (sprites + data,
  no Crystal ROM needed) and grafts it in at build time. The recompiled `.exe` is
  ROM-derivative and is likewise built locally, never shipped. See
  [ENHANCEMENTS.md](ENHANCEMENTS.md) and the **stock vs. extended** bifurcation in
  the README (`pokeyellow_recomp.toml` / `pokeyellow_stock_recomp.toml`).

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

A **clean (un-injected)** tree reproduces stock Yellow byte-for-byte:
`sha1sum pokeyellow.gbc` → `cc7d03262ebfaf2f06772c1a480c7d9d5f4a38e1` — this is
also the **stock** half of the bifurcation. Run `inject_gen2.py` on the clean
tree to produce the **extended** ROM.

> **ROM0 (Home, bank $00) is fixed 16 KB and cannot grow** — the only hard
> code-size wall. The `GetName` fix (§2.4) adds ~9 bytes there, but the pic
> resolver (§2.4) was redesigned to a banked helper that leaves Home *smaller*
> than vanilla, so the non-debug ROM has headroom. The **debug** ROM
> (`pokeyellow_debug.gbc`) packs extra debug code into Home and may still
> overflow — build the non-debug target.

To recompile the extended ROM into a native binary, see
`../pokeyellow_recomp.toml` and run `gbrecomp --config`. (Stock:
`../pokeyellow_stock_recomp.toml`.)

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

> **Internal-index space is a 1-byte id capped at `$FE`** (`$FF` = party-list
> terminator). Dex 152–215 use the contiguous tail `$BF–$FE` (append). Dex
> 216–251 are out of contiguous room, so they **reuse the 36 `const_skip`
> (MissingNo) gaps** in `$01–$BE` — placed at their exact gap index, NOT appended.
> `inject_gen2.py` does this with `replace_at_indexes()`; index-ordered tables get
> the new entry at the gap position (keyed by index, since the MissingNo *comment*
> is unreliable — cries tags fossil/ghost slots MissingNo too).
> `NUM_POKEMON_INDEXES` stays 254 (gaps reused, not added); `NUM_POKEMON` → 251.

### 2.1 Constants
- `constants/pokemon_constants.asm` — internal index. **Append** `const NAME` for
  contiguous mon; for gap-reuse mon, **replace a `const_skip`** in place.
  *Watch the `HM01` ceiling — see §2.4.*
- `constants/pokedex_constants.asm` — `const DEX_NAME` + bump `NUM_POKEMON`.

### 2.2 Stats / names / dex (data)
- `data/pokemon/base_stats/<mon>.asm` (+ `INCLUDE` it in `base_stats.asm`,
  **dex order**, before `assert_table_length NUM_POKEMON`). `GetMonHeader` indexes
  base_stats by **dex number** (via `IndexToPokedex` ← `dex_order`), so it appends.
- `names.asm`, `cries.asm`, `dex_order.asm` — **internal-index order** (append
  contiguous; gap-fill at the gap index).
- `palettes.asm` (`assert NUM_POKEMON+1`), `menu_icons.asm` — **dex order**.
- `evos_moves.asm` — a `dw <Mon>EvosMoves` in the **pointer table** (internal
  order) **and** a data block (`EVOLVE_LEVEL,lvl,target` + learnset). The injector
  supports typed multi-evolutions (LEVEL / ITEM / TRADE).
- `dex_entries.asm` — `dw <Mon>DexEntry` to the pointer table (internal order)
  + a data block (`db "CATEGORY@"`, height `db ft,in`, weight `dw tenths_lb`,
  `text_far _<Mon>DexEntry`, `text_end`). Add the (full 2-page) text to
  `dex_text.asm`. **`dex_entries.asm` must stay inline in `bank10`** with
  `pokedex.asm` — it's read with direct, non-banked loads (§2.4).

### 2.3 Sprites
- Drop `gfx/pokemon/front/<mon>.png` and `gfx/pokemon/back/<mon>b.png`. The
  build generates `.2bpp` → `.pic` automatically (`rgbgfx` + `pkmncompress`).
- Front: up to 7×7 tiles, **square**, **4-shade grayscale**.
- Back: **native 48×48 (6×6)**, 4-gray (NOT the vanilla 32×32 — see the
  native-back engine path in §2.4 / ISSUES #1; downscaling then 2× upscaling
  blurred them).
- Each mon gets its **own floating `SECTION "Pics <Mon>"`** in `gfx/pics.asm`
  with `<Mon>PicFront::` / `<Mon>PicBack::`; the linker auto-packs them across
  banks (rgbfix grows the ROM, MBC5).

### 2.4 Engine changes the new mon may force (the non-obvious part)

- **Pic bank routing (`home/pics.asm`).** Vanilla chooses a mon's pic bank by
  **internal-index range** (hard-coded "Pics 1–5"), which breaks for new mon —
  *and* gap-reuse mon sit at low indexes the ranges misroute. Replaced with a
  full **254-entry `PicBankByIndex` table** (one bank byte per index, 0 = fall
  back to vanilla ranges) read by a **banked `GetPicBankFar` helper**; the Home
  resolver shrinks to one far call (`Bankswitch`), so Home gets *smaller* than
  vanilla. Per-mon pics live in their own floating sections (§2.3).
- **`GetName` ceiling (`home/names2.asm`).** Gen 1 BUG: the "generate TM/HM
  name" shortcut (`cp HM01 / jp nc GetMachineName`) ran for **every** name list,
  capping Pokémon/move/trainer indexes below `HM01` (`$C4`). Gated on
  `wNameListType == ITEM_NAME` so the Pokédex can exceed 190 indexes (~+9 bytes
  in Home; offset by the pic-resolver shrink above).
- **WRAM / save layout (`ram/wram.asm`, `layout.link`) — now count-driven.**
  `NUM_POKEMON` sizes `wPokedexOwned`/`wPokedexSeen` (2× `flag_array NUM_POKEMON`,
  in WRAM *and the save*). `inject_gen2.size_pokedex_wram()` recomputes the delta
  vs vanilla (151→19 B each) from the live count and moves the Stack `org`
  up + shrinks `ds $eb-N` to match (251 mon → 32 B each, +26: `org $df2f`,
  `ds $eb-27`). **This changes the save format — see §3.**
- **`dex_entries.asm` must stay in `bank10`.** `PokedexEntryPointers` and the
  entry blocks are read with **direct (non-banked) loads** while `pokedex.asm`'s
  bank is mapped (`engine/menus/pokedex.asm` ~L539–650). Relocating it →
  garbled height/weight + spreading corruption. (base_stats *is* moved to its
  own bank — it's reached via `BANK(BaseStats)`; dex text via banked `text_far`.)

### 2.5 Back-porting a Pokémon from Gen 2 (pokecrystal)

Donor data lives in `pokecrystal/data/pokemon/` and
`pokecrystal/gfx/pokemon/<mon>/`. Translating Gen 2 → Gen 1:

| Field | Gen 2 (Crystal) | Gen 1 (Yellow) |
|---|---|---|
| Stats | `hp atk def spd sat sdf` | merge → `hp atk def spd spc`; **Special = Sp.Atk (`sat`)** |
| Items / gender / egg groups / hatch | present | **drop** (don't exist in Gen 1) |
| Types | any | currently **DARK→GHOST / STEEL→ROCK** remap; real Dark/Steel is on the roadmap (ENHANCEMENTS Phase A) |
| Level-up / TM learnset | Gen 2 moves | currently **filtered to Gen-1-only moves**; back-porting the 61 Gen-2 moves is roadmap Phase A |
| Front sprite | `front.png` = a **vertical anim sheet** `W×N` | crop the **top `W×W` frame**, recolor to 4-gray |
| Back sprite | `back.png` 48×48 (6×6) | **keep native 48×48**, recolor to 4-gray (engine renders it without the vanilla 2× upscale — ISSUES #1) |
| Special (Gen-1 value) | n/a for Johto mon | use `sat` (Sp.Atk) |
| Evolutions | LEVEL/ITEM/TRADE/HAPPINESS/STAT | LEVEL + Gen-1-stone ITEM + TRADE pass through; happiness/stat/Gen-2-item → level |
| Dex text | 2-page | carried in full via banked `text_far` (own ROMX section) |

This whole translation is **automated** — `gen2_data.py` parses pokecrystal and
emits Gen-1 data for any dex range; `inject_gen2.py` injects it. Sprite
conversion is Pillow (`to_gray4()` → 4 gray levels; front = `crop((0,0,W,W))`;
back centered on a 48×48 canvas, no scaling). Catch rate / base exp / growth rate
copy over directly. **Unown** sprites come from `gfx/pokemon/unown_a/` (form A).

---

## 3. Migrating a save across a save-format change

**Why it's needed.** Adding mon (§2.4) grows `wPokedexOwned`/`wPokedexSeen`
inside the *saved* main data (151→19 B each; **251→32 B each**). Everything after
the dex arrays shifts and the checksum range grows. **A stock Yellow save will
not load in the extended ROM** (offset + checksum mismatch → NEW GAME instead of
CONTINUE; the in-game message is literally "The file data is destroyed!").
Conversely an extended save won't load in stock — this is the save half of the
stock/extended bifurcation.

The current tool is **`../fill_dex_save.py`** — it reads every offset from this
build's `pokeyellow.sym` (so it's correct at any dex size), migrates a stock save
to the extended layout, fills the party + all 12 PC boxes + the whole Pokédex,
and recomputes the main + per-bank box checksums. The table below shows the
*shape*; the absolute offsets shift with `NUM_POKEMON`, so always derive them
from `pokeyellow.sym`, not these literals.

### Save layout (shape; the `(ext)` literals below are the **160-mon** build — derive current offsets from `pokeyellow.sym`)

Gen 1 SRAM is 32 KB (4 × 8 KB banks); the `.sav` mirrors it linearly, so for an
SRAM bank `B` address `$Axxx`, **file offset = `B*0x2000 + (addr - 0xA000)`**.
The save data is in bank 1:

| Symbol | SRAM | **File offset** | Notes |
|---|---|---|---|
| `sGameData` / `sPlayerName` | `01:a598` | `0x2598` | name, 11 bytes; checksum starts here |
| `sMainData` | `01:a5a3` | `0x25A3` | starts with `wPokedexOwned` |
| → `wPokedexOwned` | | `0x25A3` | `ceil(NUM_POKEMON/8)` B (19 stock, **32** at 251) |
| → `wPokedexSeen` | | after Owned | same size; immediately follows Owned |
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

The general shape (all of this is implemented in `fill_dex_save.py`, with offsets
read from `pokeyellow.sym` so it stays correct as the dex grows):

1. Copy everything up to `sMainData` (`wPokedexOwned`) unchanged.
2. Write `wPokedexOwned` then `wPokedexSeen`, each `ceil(NUM_POKEMON/8)` bytes
   (e.g. 32 B for 251), zero-padded beyond the stock 19.
3. Copy the rest of stock `sMainData` onward, **shifted by the dex growth**
   (`2 × (ceil(NUM_POKEMON/8) − 19)` bytes).
4. (Optional) overwrite `sPartyData` / the boxes with internal-index species
   bytes. **Get the index from the injected `pokemon_constants.asm`** — contiguous
   mon are `$BF+(dex−152)`, but gap-reuse mon (216–251) sit at their reused
   MissingNo index, *not* a formula. `fill_dex_save.species_index_map()` reads
   them from source.
5. Recompute the main checksum (8-bit sum of `sGameData..sGameDataEnd−1`,
   complemented) and the per-bank box checksums (each box, and all-boxes-per-bank).

> **PKHeX won't help for the new mon** — it only knows the official dex (1–151);
> our additions live at custom internal indexes (`$BF+` for 152–215, and *low*
> reused MissingNo slots for 216–251), which PKHeX treats as glitch mon. Edit the
> party/box bytes directly (or just use `fill_dex_save.py`).

### Where the runner reads the save

The runner persists battery SRAM as a `.sav` co-located with the binary
(`sdl_get_persistent_path(rom_name, ".sav")`). Drop the built `*_FILLED.sav` next
to `Pokemon_Yellow_Extended.exe` as `Pokemon_Yellow_Extended.sav` (back up any
live save first — never overwrite it), then boot → **CONTINUE**.
