# Pokémon Yellow Extended — Enhancements Roadmap

Tracking the Gen-2 content back-port on branch **`experiment/full-gen2-dex`**
(off `main`). Pipeline: pret decomp → inject Gen-2 content → RGBDS ROM →
`gbrecomp` static recompile → native SDL/ANGLE runner.

---

## Status at a glance

| Phase | State |
|---|---|
| Johto starters (dex 152–160) | ✅ shipped (v0.0.1/0.0.2, `main`) |
| Dex 161–215 (contiguous index space) | ✅ done + validated + committed |
| Dex 216–251 (MissingNo gap reuse) → **full Johto dex 1–251** | ✅ done + validated + committed |
| Validation save tooling (party + PC + full dex) | ✅ done |
| **Gen-2 moves foundation** (61 moves, data parser) | 🟡 parser done; injection pending |
| **Dark / Steel types** | ⬜ planned (part of moves foundation) |
| **`MOVE_MODE=simple`** (Gen1-mapped / damage-only effects) | ⬜ planned |
| **`MOVE_MODE=full`** (real Gen-2 effect port) | ⬜ planned (later) |
| Wire Gen-1 pre-evolutions → new mon | ⬜ planned |

Commits (newest first): `ce71993` gen2_moves parser · `92f03e5` HO-OH name fix ·
`0de81f5` gap-reuse 216–251 · `6e145fa` generator 161–215. *(Local only — not
yet pushed to the private remote.)*

---

## What's done

### Full Johto dex (1–251)
- **`gen2_data.py`** — parses pokecrystal (base_stats / evos_attacks /
  dex_entries) for any dex range and translates Gen-2 → Gen-1: Special = Gen-2
  Sp.Atk; DARK→GHOST / STEEL→ROCK (remap, *until* real types land); learnsets &
  TM/HM filtered to in-ROM moves; happiness/stat/Gen-2-item evolutions → level;
  full 2-page dex text carried via banked `text_far`. Validity sets are read
  from the ROM's own constant files, so it self-corrects as the ROM grows.
- **`inject_gen2.py`** — 9 hand-written starters + generated 161–251 (100 new
  mon). Index-ordered tables are appended for the contiguous block ($BF–$FE) and
  **gap-filled by internal index** for 216–251 (the 36 `const_skip` MissingNo
  slots in $01–$BE). Dex-ordered tables append in dex order. Pic resolver is a
  full 254-entry `PicBankByIndex` table (0 → vanilla Pics 1-5).
- **`fill_dex_save.py`** — builds a validation save from `pokeyellow.sym`
  offsets: party + all 12 PC boxes filled with Johto mon, whole 251 Pokédex
  owned+seen, main + per-bank box checksums recomputed. Never touches the live
  `.sav`.

---

## Roadmap (remaining)

### Phase A — Gen-2 moves + Dark/Steel (next up)

User decision: **pick-your-own-adventure XOR**. A `MOVE_MODE` selector in
`inject_gen2.py` — `off` (current Gen1-only) | `simple` | `full` — one-click
switchable, with per-mode effect modules. Build **foundation + `simple`** first
(working baseline); `full` slots in later as the XOR alternative.

**Foundation (mode-independent):**
1. Insert 61 Gen-2 move **constants** as IDs 166–226 (after STRUGGLE=165;
   `NUM_ATTACKS`→226). **Trim 8 unused animation slots** (`ANIM_A8`,
   `ANIM_B1`–`ANIM_B9` — confirmed 0 references) so animations shift to 227–255
   and fit the 1-byte ID space. *(165 + 61 + 37 = 263 > 255 → trim 8.)*
2. Add 61 rows to each NUM_ATTACKS-indexed table:
   - `data/moves/moves.asm` — `move <id>,<effect>,<power>,<type>,<acc%>,<pp>`
     (Gen-2 has a 7th effect-chance field → **drop it**).
   - `data/moves/names.asm` — `li "<NAME>"` (≤12 chars, in-battle width).
   - `data/moves/animations.asm` — `AttackAnimationPointers`; new moves point to
     one generic existing animation stream.
   - `data/moves/sfx.asm` — `MoveSoundTable`; reuse a generic SFX.
3. **Dark/Steel types:** add `STEEL` at `$09` (physical — split is
   `type >= SPECIAL($14)`) and `DARK` at `$1B` (special); add type names; append
   rows to `data/types/type_matchups.asm` `TypeEffects`. Then drop the
   DARK→GHOST / STEEL→ROCK remap in `gen2_data.TYPE_REMAP` when `MOVE_MODE != off`.
4. **Un-filter learnsets** — automatic once the move constants exist (the
   gen2_data validity filter starts passing them); l1/TM-HM open up too.

Parser already written: **`gen2_moves.py`** returns the 61 moves with injectable
data rows + the raw Gen-2 `EFFECT_*` name for the mappers.

**`MOVE_MODE=simple`** (`gen2_moves_simple.py`): map each Gen-2 `EFFECT_*` to the
nearest Gen-1 effect constant where it exists (Crunch→flinch/SpDef-down-as-damage,
Sludge Bomb→poison-chance, Megahorn→normal damage, …); damage-only
(`EFFECT_NORMAL_HIT`) for effects Gen-1 can't represent (weather, Curse, Perish
Song, Future Sight, Spikes, Encore, Baton Pass, Destiny Bond, …). Animations
stubbed to generic.

**`MOVE_MODE=full`** (`gen2_moves_full.py`): port the genuinely-new effects into
the Gen-1 battle engine — weather (Sandstorm/Sunny Day/Rain Dance), Curse, Perish
Song, Future Sight, Spikes, Encore, etc. Much larger; effectively porting a chunk
of the Gen-2 battle system. XOR alternative to `simple`.

### Phase B — Evolution wiring
Gen-1 pre-evolutions don't yet reach the new mon (Golbat→Crobat, Eevee→Espeon/
Umbreon, Onix→Steelix, Scyther→Scizor, Seadra→Kingdra, Slowpoke→Slowking,
Poliwhirl→Politoed, Gloom→Bellossom, Porygon→Porygon2, plus the baby pre-evos in
reverse). Patch the Gen-1 mon's evolution data to add the new branches.

---

## Technical reference (hard constraints & gotchas)

- **Species index is 1 byte, capped at `$FE`** (`$FF` = party-list terminator).
  `$BF–$FE` = 64 contiguous (dex 152–215); 216–251 reuse the 36 `const_skip`
  gaps. `NUM_POKEMON_INDEXES` stays 254 (gaps reused, not added);
  `NUM_POKEMON` = 251.
- **ROM0 / "Home" (bank $00) is fixed 16 KB and cannot grow** — the only code-
  size wall. The pic resolver was moved to a banked `GetPicBankFar` helper so
  home *shrank* vs vanilla. Total ROM auto-grows (MBC5 + rgbfix); individual
  16 KB banks just get more floating sections.
- **`dex_entries.asm` must stay inline in `bank10`** with `pokedex.asm`:
  `PokedexEntryPointers` and the entry blocks are read with **direct
  (non-banked) loads** (engine/menus/pokedex.asm ~L539-650). Relocating it →
  garbled HT/WT + spreading corruption. (base_stats→own bank and dex_text→own
  bank ARE safe — banked via `BANK(BaseStats)` / `text_far`.)
- **Index-ordered tables** (assert `NUM_POKEMON_INDEXES`): names, cries,
  dex_order, evos-ptr, dex_entries-ptr — gap mon fill by **exact internal index**
  (`replace_at_indexes`), NOT by MissingNo comment (cries also tags fossil/ghost
  slots MissingNo). base=0 for pokemon_constants (NO_MON=$00 first), base=1 for
  the 5 data tables (Rhydon=$01 first).
- **Dex-ordered tables** (assert `NUM_POKEMON`): base_stats, palettes,
  menu_icons + DEX_ consts — append in dex order. `GetMonHeader` indexes
  base_stats by **dex number** (via `IndexToPokedex` ← `dex_order`).
- **Move-ID space** (Phase A): see roadmap — 1 byte shared by 165 real moves +
  animation pseudo-moves; adding 61 requires trimming 8 unused anim slots.
- **WRAM sizing**: the Pokédex owned/seen arrays (2× `flag_array NUM_POKEMON`)
  live in WRAM **and the save**; `size_pokedex_wram()` recomputes the Stack org /
  `ds $eb-N` from the live count. Growing `NUM_POKEMON` changes the save layout
  → old saves read as "file data is destroyed" (expected) and `fill_dex_save.py`
  must be re-run.
- **Unown** sprites live in `gfx/pokemon/unown_a/` (form A), via the
  `SPRDIR_OVERRIDE` in gen2_data.

---

## Build & run

```bash
export CLEAN_PATH="/c/msys64/mingw64/bin:/c/msys64/usr/bin:/c/Windows/system32"

# 1. inject onto a CLEAN pokeyellow tree (always reset first; idempotency
#    guards key off the first starter, so adding mon needs a clean tree)
git -C pokeyellow checkout . && git -C pokeyellow clean -fd
PATH="$CLEAN_PATH" python3 inject_gen2.py

# 2. build the extended ROM (mingw32-make, NOT msys make)
cd pokeyellow
PATH="$CLEAN_PATH" TMPDIR=C:/msys64/tmp TMP=C:/msys64/tmp TEMP=C:/msys64/tmp \
  /c/msys64/mingw64/bin/mingw32-make.exe pokeyellow.gbc \
  RGBDS="F:/Projects/gbcrecomp/PokemonYellowDecomp/tools/rgbds/" -j4
cd ..

# 3. recompile → native + build
PATH="$CLEAN_PATH" /f/Projects/gbcrecomp/gb-recompiled/build/bin/gbrecomp.exe --config pokeyellow_recomp.toml
PATH="$CLEAN_PATH" /c/msys64/mingw64/bin/cmake.exe -G Ninja -S recomp -B recomp/build
PATH="$CLEAN_PATH" /c/msys64/mingw64/bin/ninja.exe -C recomp/build

# 4. validation save (writes *_FILLED.sav; never the live .sav)
PATH="$CLEAN_PATH" python3 fill_dex_save.py
```

Run: point `recomp/build/rom.cfg` at `pokeyellow/pokeyellow.gbc`, swap
`*_FILLED.sav` in as `Pokemon_Yellow_Extended.sav` (back up the live one),
launch `recomp/build/Pokemon_Yellow_Extended.exe`. Runner flags: `--input <file>`
(scripted buttons `U/D/L/R/A/B/S/T`), `--dump-frames a,b,c`, `--limit-frames N`.

**Rules:** edit pret SOURCE, never binary-patch a ROM. Never commit
ROMs/binaries/saves (repo + releases stay private). Never overwrite the user's
`recomp/build/*.sav`. Build long jobs at low priority.
