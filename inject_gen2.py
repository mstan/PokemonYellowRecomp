#!/usr/bin/env python3
"""
Inject the 9 Johto starter-line Pokémon (dex 152-160) into pokeyellow,
sourcing data + sprites from pokecrystal. Idempotent: safe to re-run.

Gen2->Gen1 translation: Special = Gen2 Sp.Atk; drop items/gender/egg/hatch;
Gen1-only movesets; sprites cropped/resized/recolored to Gen1 format.
New mon get internal indexes $BF-$C7 (>= $99) so the pic-bank resolver in
home/pics.asm is extended to route them to a new "Pics Gen2" bank.
"""
import os, sys
from PIL import Image

PY = os.path.join(os.path.dirname(__file__), "pokeyellow")
PC = os.path.join(os.path.dirname(__file__), "pokecrystal")

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

def append(relpath, block, guard):
    p = os.path.join(PY, relpath)
    s = read(p)
    if guard in s:
        print(f"  skip (already injected): {relpath}"); return
    if not s.endswith("\n"): s += "\n"
    write(p, s + block); print(f"  appended: {relpath}")

# ---- 1. constants ----
print("constants:")
insert_before("constants/pokemon_constants.asm", "DEF NUM_POKEMON_INDEXES",
    "".join(f"\tconst {m['C']}\n" for m in MONS), "const CHIKORITA")
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
\tdb 45 ; catch rate
\tdb {m['exp']} ; base exp

\tINCBIN "gfx/pokemon/front/{m['f']}.pic", 0, 1 ; sprite dimensions
\tdw {m['Camel']}PicFront, {m['Camel']}PicBack

\tdb {', '.join(m['l1'])} ; level 1 learnset
\tdb GROWTH_MEDIUM_SLOW ; growth rate

\t; tm/hm learnset
{m['tmhm']}
\t; end

\tdb 0 ; padding
"""
    write(os.path.join(PY, f"data/pokemon/base_stats/{m['f']}.asm"), body)
print("  wrote 9 base_stats files")

# ---- 3. names / cries / dex_order / palettes / menu_icons (table appends) ----
print("tables:")
insert_before("data/pokemon/names.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f'\tdname "{m["C"]}"\n' for m in MONS), '"CHIKORITA"')
insert_before("data/pokemon/cries.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f"\tmon_cry SFX_CRY_25, ${0x40+i*5:02X}, ${0x80-i*4:02X} ; {m['Camel']}\n"
            for i,m in enumerate(MONS)), "; Chikorita")
insert_before("data/pokemon/dex_order.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f"\tdb DEX_{m['C']}\n" for m in MONS), "DEX_CHIKORITA")
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
    ins = [f"\tdw {m['Camel']}EvosMoves" for m in MONS]
    lines[last_dw+1:last_dw+1] = ins
    write(p, "\n".join(lines)); print("  patched evos pointer table")
append_evos_pointers()
evo_blocks = []
for m in MONS:
    ev = f"\tdb EVOLVE_LEVEL, {m['evo'][0]}, {m['evo'][1]}\n" if m["evo"] else ""
    learn = "".join(f"\tdb {lvl}, {mv}\n" for lvl,mv in m["learn"])
    evo_blocks.append(f"""{m['Camel']}EvosMoves:
; Evolutions
{ev}\tdb 0
; Learnset
{learn}\tdb 0
""")
append("data/pokemon/evos_moves.asm", "\n"+"\n".join(evo_blocks), "ChikoritaEvosMoves:")

# ---- 5. dex_entries (pointer table + data blocks) + dex_text ----
print("dex entries/text:")
insert_before("data/pokemon/dex_entries.asm", "\tassert_table_length NUM_POKEMON_INDEXES",
    "".join(f"\tdw {m['Camel']}DexEntry\n" for m in MONS), "dw ChikoritaDexEntry")
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
    t = m["tx"]
    text_blocks.append(f"""_{m['Camel']}DexEntry::
\ttext "{t[0]}"
\tnext "{t[1]}"
\tnext "{t[2]}"
\tdex
""")
append("data/pokemon/dex_text.asm", "\n"+"\n".join(text_blocks), "_ChikoritaDexEntry::")

# ---- 6. pics.asm new section + home/pics.asm bank routing ----
print("pics:")
pics = 'SECTION "Pics Gen2", ROMX\n\n' + "".join(
    f'{m["Camel"]}PicFront:: INCBIN "gfx/pokemon/front/{m["f"]}.pic"\n'
    f'{m["Camel"]}PicBack::  INCBIN "gfx/pokemon/back/{m["f"]}b.pic"\n' for m in MONS)
append("gfx/pics.asm", "\n"+pics, "Pics Gen2")
# extend the pic-bank resolver: index >= CHIKORITA -> "Pics Gen2"
hp = os.path.join(PY, "home/pics.asm"); hs = read(hp)
if "Pics Gen2" not in hs:
    old = '\tld a, BANK("Pics 5")\n.GotBank'
    new = ('\tld a, b\n\tcp CHIKORITA\n\tld a, BANK("Pics Gen2")\n\tjr nc, .GotBank\n'
           '\tld a, BANK("Pics 5")\n.GotBank')
    assert old in hs, "home/pics.asm bank pattern not found"
    write(hp, hs.replace(old, new, 1)); print("  patched home/pics.asm bank routing")
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
    fr = Image.open(os.path.join(PC, f"gfx/pokemon/{m['f']}/front.png"))
    W = fr.width
    to_gray4(fr.crop((0, 0, W, W))).save(os.path.join(PY, f"gfx/pokemon/front/{m['f']}.png"))
    bk = Image.open(os.path.join(PC, f"gfx/pokemon/{m['f']}/back.png"))
    to_gray4(bk, (32, 32)).save(os.path.join(PY, f"gfx/pokemon/back/{m['f']}b.png"))
print("  wrote 9 front + 9 back PNGs")
print("DONE.")
