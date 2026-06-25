# PokemonYellowDecomp

An extended **Pokémon Yellow** built from the [pret/pokeyellow](https://github.com/pret/pokeyellow)
decompilation, then run **natively** through our `gbrecomp` static recompiler
and SDL/ANGLE runner.

The headline change: **9 new Pokémon — the three Johto starter lines**
(Chikorita→Bayleef→Meganium, Cyndaquil→Quilava→Typhlosion,
Totodile→Croconaw→Feraligatr), back-ported from [pret/pokecrystal](https://github.com/pret/pokecrystal)
as **Pokédex #152–160**, bringing Yellow to **160 Pokémon**.

Everything is done by editing the **decomp source** (assembly + data + PNG
sprites) and reassembling a real ROM — *not* by binary-patching a `.gbc`.

## Layout

```
PokemonYellowDecomp/
  pokeyellow/        pret decomp (base) — edited to add the 9 mon
  pokecrystal/       pret decomp (Gen 2 donor — stats, sprites, learnsets)
  roms/              your stock base ROMs (verified; not distributed)
  tools/rgbds/       RGBDS 1.0.1 (the GB assembler)
  inject_gen2.py     idempotent injector: data + ASM edits + sprite conversion
  pokeyellow_recomp.toml   gbrecomp config to recompile the modified ROM
  recomp/            generated native project (Pokemon_Yellow.exe)
```

## Quick start

```bash
# 1. Build the extended ROM (see Documentation for the mingw32-make gotcha)
cd pokeyellow
mingw32-make pokeyellow.gbc RGBDS=../tools/rgbds/ -j4   # → pokeyellow.gbc

# 2. Recompile it to native + run on our runner
gbrecomp --config ../pokeyellow_recomp.toml
#   build recomp/ with cmake+ninja, then run recomp/build/Pokemon_Yellow.exe
```

The modified ROM is a legit GB ROM (sha1 `8efa12df…`, vs stock `cc7d0326…`); it
also runs in any GBC emulator.

## Documentation

See **[TECHNICAL_NOTES.md](TECHNICAL_NOTES.md)** for the deep dives:

- **The pipeline** — decomp → ROM → recompile → native runner, and the
  content-vs-behavior rule for where to add extensibility.
- **Building** — RGBDS, the **`mingw32-make` / `TEMP`** gotcha, byte-exact
  baseline verification.
- **[Adding a new Pokémon](TECHNICAL_NOTES.md#2-adding-a-new-pokémon)** — the
  full ~12-file checklist (which tables are internal-index- vs Pokédex-ordered),
  plus the engine changes new mon can force (pic-bank routing, the `GetName`
  index ceiling, WRAM/save-layout growth).
  - **[Back-porting from Gen 2](TECHNICAL_NOTES.md#25-back-porting-a-pokémon-from-gen-2-pokecrystal)**
    — Special-stat split, dropping Gen-2-only fields, Gen-1 move remaps, and
    the sprite crop/resize/recolor.
- **[Migrating a save](TECHNICAL_NOTES.md#3-migrating-a-save-across-a-save-format-change)**
  — why adding mon changes the save format (bigger Pokédex flag arrays), the
  exact offsets + checksum, and the stock→extended migration recipe. (Note:
  PKHeX can't set the new mon — they live at custom internal indexes.)

Known issues + proposed fixes are tracked in **[ISSUES.md](ISSUES.md)** (e.g.
#1: blurry back sprites on back-ported Gen 2 mon → the native-48×48 back-sprite
engine fix).

## Distribution

Ship the pre-recompiled binary + a **BPS patch** + (optionally) a starter save.
The user provides their own **stock** Yellow ROM — no ROM is ever distributed.

**Auto-patch on launch (implemented).** When the launcher is given a stock ROM
whose SHA-256 doesn't match the build, it looks for `<prefix>.bps` next to the
executable, applies it, and — if the result matches the expected ROM — writes
`<romname>.extended.gbc` next to the exe and runs that (caching the path so it's
a one-time step). The user just supplies a stock ROM; the enhanced ROM is
produced automatically. See `bps_patch.c` / `launcher.c` in the runtime and
`make_bps.py` (patch generator) here.

Release folder (next to the .exe):

Filenames are **annotated** so it's always clear what a file is (the build's
`output_prefix` drives the exe, save, and patch-lookup names). A future stock
build would use prefix `Pokemon_Yellow_Stock` so its `.sav` never collides.

| File | Purpose |
|---|---|
| `Pokemon_Yellow_Extended.exe` | the recompiled extended game |
| `Pokemon_Yellow_Extended.bps` | stock→extended patch (`dist/Pokemon_Yellow_Extended.bps`) |
| `*.dll` (23) | SDL2, ANGLE (libEGL/libGLESv2), curl, and their deps |

First launch: pick your stock Yellow ROM → `<yourrom>.extended.gbc` is generated
and booted (cached for next time). Then NEW GAME as usual.

> No save is bundled. A clean "new game + 3 starters at Lv5" save can be
> generated with `synth_starter_save.py` if desired; it would be extended-only
> (stock Yellow rejects it safely — the larger Pokédex flag arrays change the
> save layout/checksum).

> When publishing, this is released as **PokemonYellowRecomp** (the deliverable
> is the recomp + BPS; the decomp is the build-time tool that produces the
> patch). `.gitignore` here already excludes ROMs/saves/build output.

## Credits / legal

Built on **pret**'s `pokeyellow` and `pokecrystal` disassemblies. Pokémon is ©
Nintendo / Creatures / GAME FREAK. No ROM is included or distributed — supply
your own legally-obtained copy. The BPS patch contains only original additions
(a binary diff), not any portion of the copyrighted ROM.
