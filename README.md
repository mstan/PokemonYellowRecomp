# PokemonYellowDecomp

An extended **Pokémon Yellow** built from the [pret/pokeyellow](https://github.com/pret/pokeyellow)
decompilation, then run **natively** through our `gbrecomp` static recompiler
and SDL/ANGLE runner.

The headline change: **the full Johto Pokédex — 100 new Pokémon (#152–251)**,
back-ported from [pret/pokecrystal](https://github.com/pret/pokecrystal),
bringing Yellow to the complete **National Dex #1–251**. (Started as the 9 Johto
starters; see [ENHANCEMENTS.md](ENHANCEMENTS.md) for status + roadmap.)

Everything is done by editing the **decomp source** (assembly + data + PNG
sprites) and reassembling a real ROM — *not* by binary-patching a `.gbc`. The
Gen-2 content is pulled from pokecrystal's source at build time (no Crystal ROM
needed), so the repo ships **source only — no ROM, binary, or patch**.

## Layout

```
PokemonYellowDecomp/
  pokeyellow/        pret decomp (base) — injected to add dex 152–251
  pokecrystal/       pret decomp (Gen 2 donor — stats, sprites, learnsets, text)
  roms/              optional: your own stock ROM for byte-verification (not distributed)
  tools/rgbds/       RGBDS 1.0.1 (the GB assembler)
  gen2_data.py       pokecrystal → Gen1 data translator (any dex range)
  inject_gen2.py     idempotent injector: data + ASM edits + sprite conversion
  gen2_moves.py      Gen2-move foundation parser (next phase)
  fill_dex_save.py   validation-save builder (party + PC + full Pokédex)
  pokeyellow_recomp.toml         gbrecomp config — EXTENDED build
  pokeyellow_stock_recomp.toml   gbrecomp config — STOCK build (bifurcation)
  recomp/            generated native project (Pokemon_Yellow_Extended.exe)
```

## Quick start

```bash
# 1. Build the extended ROM (see Documentation for the mingw32-make gotcha)
cd pokeyellow
mingw32-make pokeyellow.gbc RGBDS=../tools/rgbds/ -j4   # → pokeyellow.gbc

# 2. Recompile it to native + run on our runner
gbrecomp --config ../pokeyellow_recomp.toml
#   build recomp/ with cmake+ninja, then run recomp/build/Pokemon_Yellow_Extended.exe
```

The extended ROM is a legit GB ROM (vs stock Yellow sha1 `cc7d0326…`); it also
runs in any GBC emulator. (Inject onto a clean tree first — `inject_gen2.py`'s
idempotency guards key off the first injected mon, so adding mon needs a reset
`pokeyellow/`.)

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

## Distribution — source only, no BPS

**Nothing copyrighted is distributed, and there is no BPS patch.** The repo ships
only the scripts + the pinned pret commits ([BUILD_DEPS.md](BUILD_DEPS.md)). The
build clones pret `pokeyellow` + `pokecrystal` and produces the ROM **locally**,
so we never redistribute Nintendo's content.

A BPS was deliberately rejected: a patch is only "clean" when its diff is your
own work, but ours encodes the **Crystal-derived sprites / data / dex text** we
add — i.e. copyrighted content. So we drop the BPS entirely. `inject_gen2.py` is
effectively an **on-the-fly extractor** — it pulls the Gen-2 content from
pokecrystal's *source* and grafts it into Yellow at build time. No Crystal ROM is
needed; pret's open decomp is the donor.

To get a runnable game, a user clones this repo, fetches the pinned prets, and
runs the build (Quick start above). The recompiled `.exe` is ROM-derivative, so
it too is built locally and never shipped.

### Stock vs. extended (bifurcation)

Two distinct, non-colliding targets are built from the same pret base:

| Target | ROM source | Recompile config | Output |
|---|---|---|---|
| **Stock** | pret pokeyellow, **un-injected** | `pokeyellow_stock_recomp.toml` | `recomp_stock/…/Pokemon_Yellow_Stock.exe` |
| **Extended** | pret pokeyellow + `inject_gen2.py` | `pokeyellow_recomp.toml` | `recomp/…/Pokemon_Yellow_Extended.exe` |

The injector only ever runs on a freshly-reset tree, so **stock is always
recoverable** (`git -C pokeyellow checkout . && git -C pokeyellow clean -fd`).
Distinct `output_prefix`es keep the two exes/saves separate, and the runner's
`--differential` oracle can A/B them.

> A clean "new game + 3 starters" save can be generated with
> `synth_starter_save.py`, and the validation save (party + full PC + complete
> Pokédex) with `fill_dex_save.py`. Both are **extended-only** — stock Yellow
> rejects them safely, since the larger Pokédex flag arrays change the save
> layout/checksum. Saves are never committed.

## Credits / legal

Built on **pret**'s `pokeyellow` and `pokecrystal` disassemblies. Pokémon is ©
Nintendo / Creatures / GAME FREAK. No ROM, binary, or patch is distributed: this
repo is **source only** (scripts + pret pins), and the ROM is built locally from
the open decompilations. Supply your own legally-obtained game if you want to
verify byte-for-byte against the stock base.
