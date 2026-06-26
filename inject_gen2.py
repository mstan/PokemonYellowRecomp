#!/usr/bin/env python3
"""
Inject the 9 Johto starter-line Pokémon (dex 152-160) into pokeyellow,
sourcing data + sprites from pokecrystal. Idempotent: safe to re-run.

Gen2->Gen1 translation: Special = Gen2 Sp.Atk; drop items/gender/egg/hatch;
Gen1-only movesets; sprites cropped/resized/recolored to Gen1 format.
New mon get internal indexes $BF-$C7 (>= $99) so the pic-bank resolver in
home/pics.asm is extended to route them to a new "Pics Gen2" bank.
"""
import os, sys, subprocess
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "pokeyellow")
PC = os.path.join(HERE, "pokecrystal")
ENGINE_PATCH = os.path.join(HERE, "patches", "engine.patch")

GRASS_TMHM = "\ttmhm TOXIC, BODY_SLAM, TAKE_DOWN, DOUBLE_EDGE, MEGA_DRAIN, SOLARBEAM, MIMIC, DOUBLE_TEAM, REFLECT, BIDE, REST, SUBSTITUTE, CUT"
FIRE_TMHM  = "\ttmhm TOXIC, BODY_SLAM, TAKE_DOWN, DOUBLE_EDGE, FIRE_BLAST, MIMIC, DOUBLE_TEAM, BIDE, REST, SUBSTITUTE, STRENGTH"
WATER_TMHM = "\ttmhm TOXIC, ICE_BEAM, BLIZZARD, BODY_SLAM, TAKE_DOWN, DOUBLE_EDGE, SURF, MIMIC, DOUBLE_TEAM, BIDE, REST, SUBSTITUTE, STRENGTH, CUT"

# name, Camel, file, dex, hp,atk,def,spd,spc, type, exp, pal, icon,
# evolve(level,target_const) or None, l1moves(4), learnset[(lvl,move)],
# tmhm, category, ft,in, weight(tenths lb), dex_text(3 lines)
MONS = [
 dict(C="CHIKORITA",Camel="Chikorita",f="chikorita",dex=152,st=(45,49,65,45,49),
   ty=("GRASS","GRASS"),exp=64,pal="PAL_GREENMON",icon="ICON_GRASS",
   evo=(16,"BAYLEEF"),l1=("TACKLE","GROWL","NO_MOVE","NO_MOVE"),
   learn=[(9,"RAZOR_LEAF"),(17,"REFLECT"),(25,"BODY_SLAM"),(33,"LIGHT_SCREEN"),(41,"SOLARBEAM")],
   tmhm=GRASS_TMHM,cat="LEAF",ft=2,inch=11,wt=141,
   tx=("A sweet aroma","wafts from the","leaf on its head.")),
 dict(C="BAYLEEF",Camel="Bayleef",f="bayleef",dex=153,st=(60,62,80,60,63),
   ty=("GRASS","GRASS"),exp=141,pal="PAL_GREENMON",icon="ICON_GRASS",
   evo=(32,"MEGANIUM"),l1=("TACKLE","GROWL","RAZOR_LEAF","NO_MOVE"),
   learn=[(9,"RAZOR_LEAF"),(23,"REFLECT"),(31,"BODY_SLAM"),(41,"LIGHT_SCREEN"),(49,"SOLARBEAM")],
   tmhm=GRASS_TMHM,cat="LEAF",ft=3,inch=11,wt=353,
   tx=("Spicy aromas","from its leaves","perk you up.")),
 dict(C="MEGANIUM",Camel="Meganium",f="meganium",dex=154,st=(80,82,100,80,83),
   ty=("GRASS","GRASS"),exp=208,pal="PAL_GREENMON",icon="ICON_GRASS",
   evo=None,l1=("TACKLE","GROWL","RAZOR_LEAF","NO_MOVE"),
   learn=[(9,"RAZOR_LEAF"),(23,"REFLECT"),(31,"BODY_SLAM"),(46,"LIGHT_SCREEN"),(56,"SOLARBEAM")],
   tmhm=GRASS_TMHM,cat="HERB",ft=5,inch=11,wt=2216,
   tx=("Its breath can","revive dead","grass and plants.")),
 dict(C="CYNDAQUIL",Camel="Cyndaquil",f="cyndaquil",dex=155,st=(39,52,43,65,60),
   ty=("FIRE","FIRE"),exp=65,pal="PAL_REDMON",icon="ICON_MON",
   evo=(14,"QUILAVA"),l1=("TACKLE","LEER","NO_MOVE","NO_MOVE"),
   learn=[(12,"EMBER"),(19,"QUICK_ATTACK"),(27,"FIRE_SPIN"),(35,"SWIFT"),(43,"FIRE_BLAST")],
   tmhm=FIRE_TMHM,cat="FIREMOUSE",ft=1,inch=8,wt=174,
   tx=("It is timid, and","curls up to guard","with its flames.")),
 dict(C="QUILAVA",Camel="Quilava",f="quilava",dex=156,st=(58,64,58,80,80),
   ty=("FIRE","FIRE"),exp=142,pal="PAL_REDMON",icon="ICON_MON",
   evo=(36,"TYPHLOSION"),l1=("TACKLE","LEER","SMOKESCREEN","EMBER"),
   learn=[(12,"EMBER"),(21,"QUICK_ATTACK"),(31,"FIRE_SPIN"),(45,"SWIFT"),(58,"FIRE_BLAST")],
   tmhm=FIRE_TMHM,cat="VOLCANO",ft=2,inch=11,wt=419,
   tx=("It intimidates","foes with intense","bursts of flame.")),
 dict(C="TYPHLOSION",Camel="Typhlosion",f="typhlosion",dex=157,st=(78,84,78,100,109),
   ty=("FIRE","FIRE"),exp=209,pal="PAL_REDMON",icon="ICON_MON",
   evo=None,l1=("TACKLE","LEER","SMOKESCREEN","EMBER"),
   learn=[(12,"EMBER"),(21,"QUICK_ATTACK"),(31,"FIRE_SPIN"),(50,"SWIFT"),(64,"FIRE_BLAST")],
   tmhm=FIRE_TMHM,cat="VOLCANO",ft=5,inch=7,wt=1753,
   tx=("It unleashes","explosive blasts","of roiling fire.")),
 dict(C="TOTODILE",Camel="Totodile",f="totodile",dex=158,st=(50,65,64,43,44),
   ty=("WATER","WATER"),exp=66,pal="PAL_BLUEMON",icon="ICON_WATER",
   evo=(18,"CROCONAW"),l1=("SCRATCH","LEER","NO_MOVE","NO_MOVE"),
   learn=[(7,"WATER_GUN"),(13,"BITE"),(20,"RAGE"),(28,"SLASH"),(35,"SCREECH"),(43,"HYDRO_PUMP")],
   tmhm=WATER_TMHM,cat="BIGJAW",ft=2,inch=0,wt=209,
   tx=("Its tough jaws","can crunch its","prey with ease.")),
 dict(C="CROCONAW",Camel="Croconaw",f="croconaw",dex=159,st=(65,80,80,58,59),
   ty=("WATER","WATER"),exp=143,pal="PAL_BLUEMON",icon="ICON_WATER",
   evo=(30,"FERALIGATR"),l1=("SCRATCH","LEER","RAGE","WATER_GUN"),
   learn=[(7,"WATER_GUN"),(13,"BITE"),(21,"RAGE"),(28,"SLASH"),(37,"SCREECH"),(45,"HYDRO_PUMP")],
   tmhm=WATER_TMHM,cat="BIGJAW",ft=3,inch=7,wt=551,
   tx=("Once its fangs","clamp down, it","will not let go.")),
 dict(C="FERALIGATR",Camel="Feraligatr",f="feraligatr",dex=160,st=(85,105,100,78,79),
   ty=("WATER","WATER"),exp=210,pal="PAL_BLUEMON",icon="ICON_WATER",
   evo=None,l1=("SCRATCH","LEER","RAGE","WATER_GUN"),
   learn=[(7,"WATER_GUN"),(13,"BITE"),(21,"RAGE"),(28,"SLASH"),(39,"SCREECH"),(50,"HYDRO_PUMP")],
   tmhm=WATER_TMHM,cat="BIGJAW",ft=7,inch=7,wt=1958,
   tx=("It rams foes with","its huge body and","powerful tail.")),
]

# ---- Johto dex 161+ : data generated from pokecrystal (see gen2_data.py) ----
# Internal index ('idx') is a 1-byte species id, capped at $FE ($FF = party
# terminator). FERALIGATR=$C7, so $C8-$FE = 55 contiguous slots = dex 161-215.
# Dex 216-251 (36 mon) reuse the 36 MissingNo const_skip gaps in $01-$BE.
# Override the range for incremental testing via GEN2_DEX_LO / GEN2_DEX_HI.
import re as _re
import gen2_data
_LO = int(os.environ.get("GEN2_DEX_LO", "161"))
_HI = int(os.environ.get("GEN2_DEX_HI", "251"))
_STARTERS = [m["C"] for m in MONS]

# ---- Gen2 movesets/types: MOVE_MODE = off | simple | full -------------------
# off    : current behaviour (Gen1-only movesets, Dark/Steel remapped away).
# simple : add the 61 Gen2-only moves with real type/power/PP, EFFECTS mapped to
#          the nearest Gen1 effect (no engine changes).  + real Dark/Steel.
# full   : same moves/types, but native handlers are compiled into the battle
#          engine for the effects that can't be expressed in Gen1 (tiered;
#          see gen2_moves_full.py).  Build both, pick at run time.
# Switching modes requires a clean pokeyellow checkout (edits aren't reversible
# in place); within a mode the script stays idempotent.
import gen2_moves
MOVE_MODE = os.environ.get("MOVE_MODE", "off").lower()
assert MOVE_MODE in ("off", "simple", "full"), f"bad MOVE_MODE: {MOVE_MODE!r}"
NEW_MOVES, _MV = [], None
if MOVE_MODE != "off":
    import gen2_moves_simple, gen2_moves_full
    _MV = gen2_moves_full if MOVE_MODE == "full" else gen2_moves_simple
    gen2_data.TYPE_REMAP = {}  # keep mon's true Dark/Steel typing (types added below)
    gen2_data.TYPE_PAL.setdefault("DARK", "PAL_PURPLEMON")
    gen2_data.TYPE_PAL.setdefault("STEEL", "PAL_GRAYMON")
    gen2_data.TYPE_ICON.setdefault("DARK", "ICON_MON")
    gen2_data.TYPE_ICON.setdefault("STEEL", "ICON_MON")
    # Build the new-move table from the dex actually being injected (starters +
    # the generated range). Must precede build_mons so its learnset filter
    # accepts these moves (gen2_data._valid_moves reads move_constants.asm).
    _dex_for_moves = sorted(set(range(152, 161)) | set(range(_LO, _HI + 1)))
    NEW_MOVES = gen2_moves.build_move_table(_dex_for_moves)
    # Inject move CONSTANTS now (before build_mons). STRUGGLE must stay last
    # (engine asserts NUM_ATTACKS == STRUGGLE), so insert immediately before it.
    _mc = os.path.join(PY, "constants/move_constants.asm")
    _s = open(_mc, encoding="utf-8").read()
    if NEW_MOVES and NEW_MOVES[0]["C"] not in _s.split("DEF NUM_ATTACKS")[0]:
        _i = _s.rfind("\tconst STRUGGLE")
        _s = _s[:_i] + "".join(f"\tconst {m['C']}\n" for m in NEW_MOVES) + _s[_i:]
        open(_mc, "w", encoding="utf-8", newline="\n").write(_s)
        print(f"move constants: +{len(NEW_MOVES)} before STRUGGLE (MOVE_MODE={MOVE_MODE})")
    else:
        print(f"move constants: already present (MOVE_MODE={MOVE_MODE})")

MONS += gen2_data.build_mons(list(range(_LO, _HI + 1)), extra_species=_STARTERS)

def _gap_indexes():
    """Internal indexes of the const_skip (MissingNo) slots, in index order.
    RHYDON=$01 is the first const; the i-th const/const_skip line is index i."""
    s = open(os.path.join(PY, "constants/pokemon_constants.asm"), encoding="utf-8").read()
    idx, gaps = -1, []   # NO_MON is the first const line and is index $00
    for line in s.splitlines():
        t = line.strip()
        if t.startswith("const ") or t == "const_skip" or t.startswith("const_skip "):
            idx += 1
            if t.startswith("const_skip"):
                gaps.append(idx)
    return gaps

_GAPS = _gap_indexes()
# assign each mon its internal index: 152-215 contiguous from $BF; 216-251 -> gaps
for _m in MONS:
    _d = _m["dex"]
    _m["idx"] = 0xBF + (_d - 152) if _d <= 215 else _GAPS[_d - 216]
CONTIG = [m for m in MONS if m["dex"] <= 215]   # appended at index tail $BF-$FE
GAP    = [m for m in MONS if m["dex"] >= 216]    # reuse scattered MissingNo slots
assert len(GAP) <= len(_GAPS), f"need {len(GAP)} gaps, have {len(_GAPS)}"
print(f"MONS: {len(MONS)} total ({len(_STARTERS)} starters, "
      f"{len(CONTIG)-len(_STARTERS)} contiguous 161-215, {len(GAP)} gap-reuse 216-{_HI})")

def read(p):
    with open(p, encoding="utf-8") as fh: return fh.read()
def write(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as fh: fh.write(s)

def insert_before(relpath, marker, block, guard):
    p = os.path.join(PY, relpath)
    s = read(p)
    if guard in s:
        print(f"  skip (already injected): {relpath}"); return
    idx = s.rfind(marker)
    if idx < 0:
        print(f"  !! marker not found in {relpath}: {marker!r}"); sys.exit(1)
    s = s[:idx] + block + s[idx:]
    write(p, s); print(f"  patched: {relpath}")

def insert_before_regex(relpath, pattern, block, guard):
    """Like insert_before, but locates the FIRST line matching a regex (so the
    anchor can be a specific row whose exact spacing is awkward to hard-code,
    e.g. the STRUGGLE row in the move tables)."""
    p = os.path.join(PY, relpath)
    s = read(p)
    if guard in s:
        print(f"  skip (already injected): {relpath}"); return
    m = _re.search(pattern, s, _re.M)
    if not m:
        print(f"  !! pattern not found in {relpath}: {pattern!r}"); sys.exit(1)
    s = s[:m.start()] + block + s[m.start():]
    write(p, s); print(f"  patched: {relpath}")

def append(relpath, block, guard):
    p = os.path.join(PY, relpath)
    s = read(p)
    if guard in s:
        print(f"  skip (already injected): {relpath}"); return
    if not s.endswith("\n"): s += "\n"
    write(p, s + block); print(f"  appended: {relpath}")

def replace_at_indexes(relpath, entry_regex, items, base, guard):
    """Replace the data entry at specific INTERNAL INDEXES in an index-ordered
    table. items = [(internal_index, replacement_line), ...]; entry_regex must
    match EVERY data entry (so positions line up). base = index of the first
    matched entry (0 if the table includes NO_MON/$00, else 1). Used for gap
    reuse: each gap-reuse mon's entry replaces the MissingNo placeholder sitting
    at its const_skip index — keyed by index, NOT by a MissingNo comment (which
    is unreliable: e.g. cries tags fossil/ghost slots MissingNo too). Idempotent."""
    p = os.path.join(PY, relpath); s = read(p)
    if guard in s:
        print(f"  skip (already gap-filled): {relpath}"); return
    matches = list(_re.finditer(entry_regex, s, _re.M))
    out = s
    for idx, repl in sorted(items, reverse=True):  # back-to-front keeps offsets
        pos = idx - base
        if not (0 <= pos < len(matches)):
            print(f"  !! {relpath}: index ${idx:02X} -> pos {pos} of {len(matches)} out of range")
            sys.exit(1)
        m = matches[pos]
        out = out[:m.start()] + repl + out[m.end():]
    write(p, out); print(f"  gap-filled {len(items)}: {relpath}")

def apply_engine_patch():
    """Apply patches/engine.patch (the manual engine edits that aren't simple
    table inserts: GetName index-ceiling fix, stack/layout for the bigger
    Pokedex flag arrays, and the native 48x48 back-sprite path). Idempotent."""
    if not os.path.exists(ENGINE_PATCH):
        print("  !! patches/engine.patch missing"); sys.exit(1)
    # already applied?
    if subprocess.run(["git", "apply", "--reverse", "--check", ENGINE_PATCH],
                      cwd=PY, capture_output=True).returncode == 0:
        print("  skip (engine patch already applied)"); return
    r = subprocess.run(["git", "apply", ENGINE_PATCH], cwd=PY, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  !! engine patch failed to apply:\n{r.stderr}"); sys.exit(1)
    print("  applied patches/engine.patch (GetName fix, stack/layout, 48x48 backs)")

def size_pokedex_wram():
    """The Pokedex owned/seen arrays (2x flag_array NUM_POKEMON) grow with the
    dex. engine.patch hardcodes the 160-mon delta (+2); recompute it from the
    ACTUAL count so any batch size links. Vanilla: NUM_POKEMON=151 -> 19 bytes
    each, Stack org=$df15, stack `ds $eb - 1`. Move the Stack org UP by the
    extra bytes and shrink the stack the same amount so it still ends at $dfff.
    Idempotent (regex recomputes the same value)."""
    import math, re
    num_pokemon = 151 + len(MONS)
    grow = 2 * (math.ceil(num_pokemon / 8) - 19)  # bytes beyond vanilla
    org = 0xdf15 + grow
    lp = os.path.join(PY, "layout.link"); ls = read(lp)
    ls2 = re.sub(r"org \$df[0-9a-fA-F]{2}([^\n]*)",
                 f"org ${org:04x} ; Stack start, +{grow} for {num_pokemon}-mon Pokedex", ls, count=1)
    if ls2 != ls: write(lp, ls2)
    wp = os.path.join(PY, "ram/wram.asm"); ws = read(wp)
    ws2 = re.sub(r"ds \$eb - \d+", f"ds $eb - {1 + grow}", ws, count=1)
    if ws2 != ws: write(wp, ws2)
    print(f"  sized Pokedex WRAM: NUM_POKEMON={num_pokemon}, +{grow}B "
          f"(Stack org=${org:04x}, stack=ds $eb - {1 + grow})")

def relocate_growing_tables():
    """base_stats outgrows its shared ROMX bank ("Battle Engine 6") at full-dex
    sizes. It is reached via BANK(BaseStats) (an explicit far load in
    GetMonHeader), so it is safe to move into its own floating ROMX section;
    the linker re-packs the freed code and rgbfix grows the ROM. Idempotent.

    NOTE: dex_entries.asm is deliberately NOT relocated. PokedexEntryPointers
    AND the per-mon entry blocks are read with DIRECT (non-banked) loads while
    pokedex.asm's own bank is mapped (see engine/menus/pokedex.asm ~L539-650),
    so the data must stay co-located with that code. bank10 has ~11KB free, so
    the larger table fits inline. Moving it elsewhere reads garbage -> garbled
    height/weight and spreading corruption."""
    mp = os.path.join(PY, "main.asm"); ms = read(mp)
    anchor = '\nSECTION "Battle Core", ROMX'
    if 'SECTION "Base Stats"' not in ms:
        ms = ms.replace('INCLUDE "data/pokemon/base_stats.asm"\n', '', 1)
        ms = ms.replace(anchor,
            '\nSECTION "Base Stats", ROMX\n\nINCLUDE "data/pokemon/base_stats.asm"\n'
            + anchor, 1)
        write(mp, ms); print("  relocated base_stats -> own bank")

def relocate_anim_overflow():
    """Adding 61 per-move pointers to AttackAnimationPointers overflows bank1E
    (already near-full from the full dex). Move three far-accessed chunks out to
    a floating ROMX bank to make room: cut2 (entered via `predef UsedCut`),
    dust_smoke (`callfar AnimateBoulderDust`), and the fishing gfx (loaded with
    a BANK() byte from its table) -- all bank-transparent, so relocation is safe.
    Moved as one contiguous block to preserve their original ordering. Idempotent."""
    mp = os.path.join(PY, "main.asm"); ms = read(mp)
    if 'SECTION "Gen2 Anim Overflow"' in ms:
        print("  skip (anim overflow already relocated)"); return
    moved = ['INCLUDE "engine/overworld/cut2.asm"\n',
             'INCLUDE "engine/overworld/dust_smoke.asm"\n',
             'INCLUDE "gfx/fishing.asm"\n']
    for inc in moved:
        if inc not in ms:
            print(f"  !! anim-overflow include not found: {inc!r}"); sys.exit(1)
        ms = ms.replace(inc, "", 1)
    sec = '\nSECTION "Gen2 Anim Overflow", ROMX\n\n' + "".join(moved)
    ms = ms.replace('\nSECTION "Surfing Minigame", ROMX',
                    sec + '\nSECTION "Surfing Minigame", ROMX', 1)
    write(mp, ms)
    print("  relocated cut2/dust_smoke/fishing -> floating bank (anim overflow)")

def trim_anim_slots():
    """Drop gen2_moves.ANIM_TRIM pseudo-animation slots so NUM_ATTACK_ANIMS
    (= NUM_ATTACKS + #pseudo-anims) stays <= 255 once the 61 new moves push
    NUM_ATTACKS to 226. Removes each slot's const (move_constants.asm) AND its
    1:1 pointer in the pseudo-anim region of AttackAnimationPointers
    (animations.asm). Idempotent (keys off the first trim const still present)."""
    trim = gen2_moves.ANIM_TRIM
    mc = os.path.join(PY, "constants/move_constants.asm"); ms = read(mc)
    if f"\tconst {trim[0]}\n" not in ms:
        print("  skip (anim slots already trimmed)"); return
    after = ms.split("DEF NUM_ATTACKS", 1)[1].split("DEF NUM_ATTACK_ANIMS", 1)[0]
    pseudo = _re.findall(r"^\tconst (\w+)", after, _re.M)  # 37 pseudo-anim consts, in order
    drop_ord = sorted(pseudo.index(c) for c in trim)
    for c in trim:
        ms = ms.replace(f"\tconst {c}\n", "", 1)
    write(mc, ms)
    ap = os.path.join(PY, "data/moves/animations.asm"); s = read(ap)
    head, rest = s.split("\tassert_table_length NUM_ATTACKS\n", 1)
    region, tail = rest.split("\tassert_table_length NUM_ATTACK_ANIMS", 1)
    dw = region.splitlines(keepends=True)              # the 37 pseudo-anim `dw` lines
    dws = [i for i, l in enumerate(dw) if l.lstrip().startswith("dw ")]
    for o in sorted(drop_ord, reverse=True):
        del dw[dws[o]]
    write(ap, head + "\tassert_table_length NUM_ATTACKS\n" + "".join(dw)
          + "\tassert_table_length NUM_ATTACK_ANIMS" + tail)
    print(f"  trimmed {len(trim)} anim slots: {', '.join(trim)}")

# ---- 0. engine patches (non-table edits) ----
print("engine patches:")
apply_engine_patch()
size_pokedex_wram()
relocate_growing_tables()

# ---- 1. constants ----
print("constants:")
# internal-index list: contiguous mon append at the tail ($BF-$FE); gap-reuse
# mon REPLACE const_skip slots in place (NUM_POKEMON_INDEXES stays the same).
insert_before("constants/pokemon_constants.asm", "DEF NUM_POKEMON_INDEXES",
    "".join(f"\tconst {m['C']}\n" for m in CONTIG), "const CHIKORITA")
if GAP:
    replace_at_indexes("constants/pokemon_constants.asm", r"^\tconst(?:_skip| [A-Z0-9_]+).*$",
        [(m["idx"], f"\tconst {m['C']}") for m in GAP], 0, f"\tconst {GAP[0]['C']}\n")
# pokedex (dex-number) consts: all new mon append in dex order.
insert_before("constants/pokedex_constants.asm", "DEF NUM_POKEMON ",
    "".join(f"\tconst DEX_{m['C']}\n" for m in MONS), "DEX_CHIKORITA")

# ---- 2. base_stats include + files ----
print("base_stats:")
insert_before("data/pokemon/base_stats.asm", "\tassert_table_length NUM_POKEMON",
    "".join(f'INCLUDE "data/pokemon/base_stats/{m["f"]}.asm"\n' for m in MONS),
    "base_stats/chikorita.asm")
for m in MONS:
    hp,atk,df,spd,spc = m["st"]
    body = f"""\tdb DEX_{m['C']} ; pokedex id

\tdb {hp:3}, {atk:3}, {df:3}, {spd:3}, {spc:3}
\t;   hp  atk  def  spd  spc

\tdb {m['ty'][0]}, {m['ty'][1]} ; type
\tdb {m.get('cr', 45)} ; catch rate
\tdb {m['exp']} ; base exp

\tINCBIN "gfx/pokemon/front/{m['f']}.pic", 0, 1 ; sprite dimensions
\tdw {m['Camel']}PicFront, {m['Camel']}PicBack

\tdb {', '.join(m['l1'])} ; level 1 learnset
\tdb {m.get('growth', 'GROWTH_MEDIUM_SLOW')} ; growth rate

\t; tm/hm learnset
{m['tmhm']}
\t; end

\tdb 0 ; padding
"""
    write(os.path.join(PY, f"data/pokemon/base_stats/{m['f']}.asm"), body)
print(f"  wrote {len(MONS)} base_stats files")

# ---- 3. names / cries / dex_order / palettes / menu_icons ----
# names/cries/dex_order are INDEX-ordered (assert NUM_POKEMON_INDEXES): append
# the contiguous mon, gap-fill the rest into their MissingNo slots. palettes/
# menu_icons are DEX-ordered (NUM_POKEMON): append all new mon in dex order.
print("tables:")
def cry(i, camel):
    return f"\tmon_cry SFX_CRY_25, ${(0x40+i*5)&0xFF:02X}, ${(0x60+i*3)&0xFF|1:02X} ; {camel}"
insert_before("data/pokemon/names.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f'\tdname "{m.get("name", m["C"])}"\n' for m in CONTIG), '"CHIKORITA"')
insert_before("data/pokemon/cries.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(cry(i, m["Camel"]) + "\n" for i, m in enumerate(CONTIG)), "; Chikorita")
insert_before("data/pokemon/dex_order.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f"\tdb DEX_{m['C']}\n" for m in CONTIG), "DEX_CHIKORITA")
if GAP:
    replace_at_indexes("data/pokemon/names.asm", r'^\tdname ".*"$',
        [(m["idx"], f'\tdname "{m.get("name", m["C"])}"') for m in GAP], 1,
        f'\tdname "{GAP[0].get("name", GAP[0]["C"])}"')
    replace_at_indexes("data/pokemon/cries.asm", r"^\tmon_cry .*$",
        [(m["idx"], cry(i, m["Camel"])) for i, m in enumerate(GAP)], 1,
        cry(0, GAP[0]["Camel"]))
    replace_at_indexes("data/pokemon/dex_order.asm", r"^\tdb (?:DEX_[A-Z0-9_]+|0)\b.*$",
        [(m["idx"], f"\tdb DEX_{m['C']}") for m in GAP], 1, f"\tdb DEX_{GAP[0]['C']}")
insert_before("data/pokemon/palettes.asm", "\tassert_table_length NUM_POKEMON + 1",
    "".join(f"\tdb {m['pal']:<13}; {m['C']}\n" for m in MONS), "; CHIKORITA")
insert_before("data/pokemon/menu_icons.asm", "\tend_nybble_array NUM_POKEMON",
    "".join(f"\tnybble {m['icon']:<12}; {m['Camel']}\n" for m in MONS), "; Chikorita")

# ---- 4. evos_moves (pointer table + data blocks) ----
print("evos_moves:")
insert_before("data/pokemon/evos_moves.asm", "EvosMovesPointerTable" ,
    "", "DUMMY_NEVER")  # no-op anchor; pointer table is appended via marker below
# pointer table: each pre-existing pointer is "\tdw <Mon>EvosMoves" ; the table is
# terminated by a non-dw line. Append our 9 dw right after the last existing dw.
def append_evos_pointers():
    p = os.path.join(PY, "data/pokemon/evos_moves.asm"); s = read(p)
    if "dw ChikoritaEvosMoves" in s: print("  skip evos pointers"); return
    lines = s.split("\n")
    # find pointer table region: from 'EvosMovesPointerTable' until first blank after dw lines
    start = next(i for i,l in enumerate(lines) if l.startswith("EvosMovesPointerTable"))
    last_dw = start
    for i in range(start+1, len(lines)):
        if lines[i].lstrip().startswith("dw "): last_dw = i
        elif lines[i].strip()=="" and last_dw>start: break
    ins = [f"\tdw {m['Camel']}EvosMoves" for m in CONTIG]  # contiguous at the tail
    lines[last_dw+1:last_dw+1] = ins
    write(p, "\n".join(lines)); print("  patched evos pointer table")
append_evos_pointers()
if GAP:  # gap mon: fill their scattered evos pointer slots by internal index
    replace_at_indexes("data/pokemon/evos_moves.asm", r"^\tdw [A-Za-z0-9]+EvosMoves$",
        [(m["idx"], f"\tdw {m['Camel']}EvosMoves") for m in GAP], 1,
        f"\tdw {GAP[0]['Camel']}EvosMoves")
def evo_lines(m):
    """Emit Gen1 evolution bytes from either the new typed 'evos' list or the
    legacy single 'evo' tuple. Gen1 byte formats:
      LEVEL: db EVOLVE_LEVEL, <lvl>, <target>
      ITEM:  db EVOLVE_ITEM, <item>, 1, <target>
      TRADE: db EVOLVE_TRADE, 1, <target>"""
    if "evos" in m:
        out = []
        for e in m["evos"]:
            if e[0] == "LEVEL": out.append(f"\tdb EVOLVE_LEVEL, {e[1]}, {e[2]}\n")
            elif e[0] == "ITEM": out.append(f"\tdb EVOLVE_ITEM, {e[1]}, 1, {e[2]}\n")
            elif e[0] == "TRADE": out.append(f"\tdb EVOLVE_TRADE, 1, {e[1]}\n")
        return "".join(out)
    return f"\tdb EVOLVE_LEVEL, {m['evo'][0]}, {m['evo'][1]}\n" if m.get("evo") else ""

evo_blocks = []
for m in MONS:
    ev = evo_lines(m)
    learn = "".join(f"\tdb {lvl}, {mv}\n" for lvl,mv in m["learn"])
    evo_blocks.append(f"""{m['Camel']}EvosMoves:
; Evolutions
{ev}\tdb 0
; Learnset
{learn}\tdb 0
""")
append("data/pokemon/evos_moves.asm", "\n"+"\n".join(evo_blocks), "ChikoritaEvosMoves:")

# ---- 5. dex_entries (pointer table + data blocks) + dex_text ----
# Pointer table is INDEX-ordered: contiguous append + gap-fill MissingNoDexEntry.
# Entry/text data blocks are label-referenced -> append all (position-free).
print("dex entries/text:")
insert_before("data/pokemon/dex_entries.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f"\tdw {m['Camel']}DexEntry\n" for m in CONTIG), "dw ChikoritaDexEntry")
if GAP:
    replace_at_indexes("data/pokemon/dex_entries.asm", r"^\tdw [A-Za-z0-9]+DexEntry$",
        [(m["idx"], f"\tdw {m['Camel']}DexEntry") for m in GAP], 1,
        f"\tdw {GAP[0]['Camel']}DexEntry")
dex_blocks = []
for m in MONS:
    dex_blocks.append(f"""{m['Camel']}DexEntry:
\tdb "{m['cat']}@"
\tdb {m['ft']},{m['inch']}
\tdw {m['wt']}
\ttext_far _{m['Camel']}DexEntry
\ttext_end
""")
append("data/pokemon/dex_entries.asm", "\n"+"\n".join(dex_blocks), "ChikoritaDexEntry:")
text_blocks = []
for m in MONS:
    if "dexbody" in m:
        body = "\n".join(m["dexbody"])
        text_blocks.append(f"_{m['Camel']}DexEntry::\n{body}\n\tdex\n")
    else:
        t = m["tx"]
        text_blocks.append(f"""_{m['Camel']}DexEntry::
\ttext "{t[0]}"
\tnext "{t[1]}"
\tnext "{t[2]}"
\tdex
""")
# Full 2-page Gen2 dex text is far larger than vanilla's terse entries and
# overflows the 16KB "Pokédex Text" bank. Entries are reached via banked
# text_far pointers, so park the new ones in their own floating ROMX section.
# (dex_text.asm is the last include in "Pokédex Text"; text.asm starts a new
#  SECTION right after, so this directive captures only our appended entries.)
append("data/pokemon/dex_text.asm",
       '\nSECTION "Pokedex Text Gen2", ROMX\n\n' + "\n".join(text_blocks),
       "_ChikoritaDexEntry::")

# ---- 6. pics.asm sections + per-species pic-bank table + resolver ----
# One floating ROMX section per mon (front+back share a bank, as the resolver
# computes a single bank used for both). The linker auto-packs these across as
# many banks as needed and rgbfix grows the ROM (MBC5). A floating bank table
# (Gen2PicBanks, indexed by species-CHIKORITA) records each mon's pic bank via
# BANK(), so the home resolver needs no per-bank range comparisons and this
# scales to any count / non-contiguous indexes.
print("pics:")
pics = "\n".join(
    f'SECTION "Pics {m["Camel"]}", ROMX\n'
    f'{m["Camel"]}PicFront:: INCBIN "gfx/pokemon/front/{m["f"]}.pic"\n'
    f'{m["Camel"]}PicBack::  INCBIN "gfx/pokemon/back/{m["f"]}b.pic"\n' for m in MONS)
# Full internal-index -> pic-bank table (PicBankByIndex) + a banked resolver.
# One byte per index $01-$FE: the mon's pic bank via BANK(), or 0 if the index
# isn't an injected mon (-> fall back to vanilla "Pics 1-5"/fossil ranges). A
# full-index table (not species>=CHIKORITA) is required because gap-reuse mon
# sit at LOW indexes scattered through $01-$BE. The resolver lives in ROMX (reads
# the table in-bank); the home side shrinks to one far call, freeing ROM0.
idx2camel = {m["idx"]: m["Camel"] for m in MONS}
picrows = "".join(
    (f'\tdb BANK({idx2camel[i]}PicFront) ; ${i:02X} {idx2camel[i]}\n' if i in idx2camel
     else f'\tdb 0 ; ${i:02X}\n')
    for i in range(1, 255))
banktable = (
    'SECTION "Pic Bank Table", ROMX\n'
    'PicBankByIndex::\n' + picrows +
    '\nGetPicBankFar::\n'
    '; in: c = species index ; out: e = pic ROM bank\n'
    '\tld a, c\n'
    '\tand a\n'
    '\tjr z, .vanilla\n'
    '\tdec a\n'
    '\tld e, a\n'
    '\tld d, 0\n'
    '\tld hl, PicBankByIndex\n'
    '\tadd hl, de\n'
    '\tld a, [hl]\n'
    '\tand a\n'
    '\tjr z, .vanilla\n'
    '\tld e, a\n'
    '\tret\n'
    '.vanilla\n'
    '\tld a, c\n'
    '\tcp FOSSIL_KABUTOPS\n'
    '\tjr nz, .nf\n'
    '\tld e, BANK(FossilKabutopsPic)\n'
    '\tret\n'
    '.nf\n'
    '\tcp TANGELA + 1\n'
    '\tjr nc, .n1\n'
    '\tld e, BANK("Pics 1")\n'
    '\tret\n'
    '.n1\n'
    '\tcp MOLTRES + 1\n'
    '\tjr nc, .n2\n'
    '\tld e, BANK("Pics 2")\n'
    '\tret\n'
    '.n2\n'
    '\tcp BEEDRILL + 2\n'
    '\tjr nc, .n3\n'
    '\tld e, BANK("Pics 3")\n'
    '\tret\n'
    '.n3\n'
    '\tcp STARMIE + 1\n'
    '\tjr nc, .n4\n'
    '\tld e, BANK("Pics 4")\n'
    '\tret\n'
    '.n4\n'
    '\tld e, BANK("Pics 5")\n'
    '\tret\n')
append("gfx/pics.asm", "\n" + pics + "\n" + banktable, "Pics Chikorita")
# Home resolver: replace the entire vanilla range chain with one far call.
hp = os.path.join(PY, "home/pics.asm"); hs = read(hp)
if "GetPicBankFar" not in hs:
    old = (
        '\tld a, [wCurPartySpecies]\n'
        '\tld b, a\n'
        '\tcp FOSSIL_KABUTOPS\n'
        '\tld a, BANK(FossilKabutopsPic)\n'
        '\tjr z, .GotBank\n'
        '\tld a, b\n'
        '\tcp TANGELA + 1\n'
        '\tld a, BANK("Pics 1")\n'
        '\tjr c, .GotBank\n'
        '\tld a, b\n'
        '\tcp MOLTRES + 1\n'
        '\tld a, BANK("Pics 2")\n'
        '\tjr c, .GotBank\n'
        '\tld a, b\n'
        '\tcp BEEDRILL + 2\n'
        '\tld a, BANK("Pics 3")\n'
        '\tjr c, .GotBank\n'
        '\tld a, b\n'
        '\tcp STARMIE + 1\n'
        '\tld a, BANK("Pics 4")\n'
        '\tjr c, .GotBank\n'
        '\tld a, BANK("Pics 5")\n'
        '.GotBank\n'
        '\tjp UncompressSpriteData')
    new = (
        '\tld a, [wCurPartySpecies]\n'
        '\tld c, a\n'
        '\tld hl, GetPicBankFar\n'
        '\tld b, BANK(GetPicBankFar)\n'
        '\tcall Bankswitch ; runs GetPicBankFar far, returns bank in e\n'
        '\tld a, e\n'
        '\tjp UncompressSpriteData')
    assert old in hs, "home/pics.asm resolver pattern not found"
    write(hp, hs.replace(old, new, 1)); print("  patched home/pics.asm -> far bank resolver")
else:
    print("  skip home/pics.asm")

# ---- 7. sprites (Pillow): crop front frame, resize back, recolor to 4-gray ----
print("sprites:")
def to_gray4(img, size=None):
    # Convert to luminance FIRST (palette-aware), THEN resize. Resizing a
    # mode-'P' image interpolates palette *indices* -> garbage; converting to
    # 'L' first means we interpolate actual brightness. Finally quantize to the
    # 4 GB shades.
    g = img.convert("RGBA").convert("L")
    if size is not None:
        g = g.resize(size, Image.LANCZOS)
    return g.point([min(3, v * 4 // 256) * 85 for v in range(256)])
for m in MONS:
    src = m.get("sprdir", m["f"])  # source form dir (e.g. unown -> unown_a)
    fr = Image.open(os.path.join(PC, f"gfx/pokemon/{src}/front.png"))
    W = fr.width
    to_gray4(fr.crop((0, 0, W, W))).save(os.path.join(PY, f"gfx/pokemon/front/{m['f']}.png"))
    # Back: keep Gen 2's NATIVE 48x48 (6x6 tiles) — no downscale. LoadMonBackPic
    # detects the 6x6 dimension and renders it without the vanilla 2x upscale, so
    # there's no downscale+re-upscale blur (see engine/battle/init_battle.asm).
    # Force exactly 48x48 by centering on a white canvas (no scaling).
    bk = Image.open(os.path.join(PC, f"gfx/pokemon/{src}/back.png")).convert("RGBA").convert("L")
    canvas = Image.new("L", (48, 48), 255)
    canvas.paste(bk, ((48 - bk.width) // 2, (48 - bk.height) // 2))
    to_gray4(canvas).save(os.path.join(PY, f"gfx/pokemon/back/{m['f']}b.png"))
print(f"  wrote {len(MONS)} front + {len(MONS)} back PNGs")

# ---- 8. Gen2 moves + Dark/Steel types (MOVE_MODE simple/full) ----
if MOVE_MODE != "off" and NEW_MOVES:
    print(f"moves+types ({MOVE_MODE}):")
    relocate_anim_overflow()  # free bank1E room for the +61 animation pointers
    # types: STEEL ($09, physical block) and DARK ($1b, after the special block)
    insert_before("constants/type_constants.asm", "DEF UNUSED_TYPES EQU const_value",
        "\tconst STEEL\n", "\tconst STEEL\n")
    insert_before("constants/type_constants.asm", "DEF NUM_TYPES EQU const_value",
        "\tconst DARK\n", "\tconst DARK\n")
    insert_before("data/types/names.asm", "REPT UNUSED_TYPES_END",
        "\tdw .Steel\n", "\tdw .Steel\n")
    insert_before("data/types/names.asm", "\tassert_table_length NUM_TYPES",
        "\tdw .Dark\n", "\tdw .Dark\n")
    insert_before("data/types/names.asm", '.Normal:   db "NORMAL@"',
        '.Steel:    db "STEEL@"\n.Dark:     db "DARK@"\n', '.Steel:')
    matchups = "\t; --- Gen2 Dark/Steel type matchups ---\n" + "".join(
        f"\tdb {a+',':<13} {d+',':<13} {mlt}\n" for a, d, mlt in gen2_moves.TYPE_MATCHUPS)
    insert_before("data/types/type_matchups.asm", "\tdb -1 ; end", matchups,
        "Gen2 Dark/Steel type matchups")

    # move tables: 61 rows go BEFORE the STRUGGLE row in each parallel table so
    # STRUGGLE stays the last move (NUM_ATTACKS == STRUGGLE).
    resolve = _MV.resolve
    insert_before_regex("data/moves/moves.asm", r"^\tmove STRUGGLE,",
        gen2_moves.moves_rows(NEW_MOVES, resolve), f"\tmove {NEW_MOVES[0]['C']},")
    insert_before_regex("data/moves/names.asm", r'^\tli "STRUGGLE"',
        gen2_moves.names_rows(NEW_MOVES), f'\tli "{NEW_MOVES[0]["name"]}"')
    insert_before_regex("data/moves/animations.asm", r"^\tdw StruggleAnim$",
        "\t; Gen2 moves (generic anim)\n" + gen2_moves.anim_rows(NEW_MOVES),
        "Gen2 moves (generic anim)")
    insert_before_regex("data/moves/sfx.asm", r"^\tdb .*; STRUGGLE$",
        gen2_moves.sfx_rows(NEW_MOVES), f"; {NEW_MOVES[0]['C']}\n")
    trim_anim_slots()

    # full mode only: compile native effect handlers into the battle engine
    if MOVE_MODE == "full":
        ed = _MV.engine_edits()
        if ed["consts"]:
            insert_before("constants/move_effect_constants.asm",
                "DEF NUM_MOVE_EFFECTS", ed["consts"], ed["consts"].split()[1])
            insert_before_regex("data/moves/effects_pointers.asm",
                r"^\tassert_table_length NUM_MOVE_EFFECTS", ed["pointers"],
                ed["pointers"].split()[1])
            append("engine/battle/effects.asm", "\n" + ed["handlers"],
                ed["handlers"].split("\n", 1)[0])
            if ed["residual1"]:
                insert_before("data/battle/residual_effects_1.asm", "\tdb -1 ; end",
                    ed["residual1"], ed["residual1"].split()[1])
        print(f"  full-mode engine: {len(_MV.NATIVE_EFFECTS)} native effect handler(s)")

print("DONE.")
