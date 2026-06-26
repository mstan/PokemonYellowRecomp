#!/usr/bin/env python3
"""
gen2_moves.py -- foundation for back-porting Gen2 moves into pokeyellow.

Parses pokecrystal's move table + names and exposes, for a given dex range,
the set of Gen2-only moves those mon learn, with Gen1-injectable data rows
(type/power/accuracy/pp). EFFECT translation is mode-specific and lives in the
effect modules (gen2_moves_simple / gen2_moves_full); this module only carries
the raw Gen2 effect name so those modules can map it.

Move-ID space: the 61 new moves take IDs 166..(165+N); see project memory.
Names are capped to Gen1's in-battle width (MOVE_NAME_LENGTH-2 = 12).
"""
import os, re
import gen2_data as gd

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "pokeyellow")
PC = os.path.join(HERE, "pokecrystal")

# Gen2 move-data types that don't exist in Gen1 -> nearest Gen1 type for the
# move's STAB/damage typing. (Dark/Steel are added as real types, so they are
# NOT remapped here.) CURSE_TYPE is Gen2's ??? (typeless) Curse.
MOVE_TYPE_REMAP = {"CURSE_TYPE": "GHOST"}

MAX_NAME = 12  # MOVE_NAME_LENGTH - 2 (in-battle "used X!" width)

# Variable-power Gen2 moves carry power 0/1 in the data (the real power is
# computed at runtime from HP, happiness, party, etc.). Gen1 can't scale, so
# give each a fixed, playable power. Applied in build_move_table for BOTH modes.
POWER_OVERRIDE = {
    "FLAIL": 80, "REVERSAL": 80, "HIDDEN_POWER": 50, "PRESENT": 40,
    "PURSUIT": 40, "ROLLOUT": 30, "FALSE_SWIPE": 40, "BEAT_UP": 30,
    "TRIPLE_KICK": 20,
}

# ---------------------------------------------------------------------------
# Real Gen2 types (added to the ROM only when MOVE_MODE != off). Gen1's
# physical/special split is BY TYPE: type < SPECIAL ($14) is physical, else
# special. So STEEL goes in the unused physical block ($09) and DARK after the
# special block ($1b). When these exist, gen2_data drops its DARK->GHOST /
# STEEL->ROCK remap and the new Dark/Steel moves keep their true type.
# Each: (const, display, is_special). Insertion points are handled by inject.
NEW_TYPES = [
    ("STEEL", "STEEL", False),  # physical, slot $09
    ("DARK",  "DARK",  True),   # special,  slot $1b
]

# Canonical Gen2 type chart rows for Dark/Steel (attacker, defender, multiplier).
# The engine's TypeEffects table lists only non-neutral matchups and uses the
# FIRST match, so appending these new-type rows can't collide with vanilla ones.
TYPE_MATCHUPS = [
    # Steel attacking
    ("STEEL", "ICE", "SUPER_EFFECTIVE"), ("STEEL", "ROCK", "SUPER_EFFECTIVE"),
    ("STEEL", "STEEL", "NOT_VERY_EFFECTIVE"), ("STEEL", "FIRE", "NOT_VERY_EFFECTIVE"),
    ("STEEL", "WATER", "NOT_VERY_EFFECTIVE"), ("STEEL", "ELECTRIC", "NOT_VERY_EFFECTIVE"),
    # attacking Steel (Steel's resistances / weaknesses)
    ("FIGHTING", "STEEL", "SUPER_EFFECTIVE"), ("GROUND", "STEEL", "SUPER_EFFECTIVE"),
    ("FIRE", "STEEL", "SUPER_EFFECTIVE"), ("POISON", "STEEL", "NO_EFFECT"),
    ("NORMAL", "STEEL", "NOT_VERY_EFFECTIVE"), ("FLYING", "STEEL", "NOT_VERY_EFFECTIVE"),
    ("ROCK", "STEEL", "NOT_VERY_EFFECTIVE"), ("BUG", "STEEL", "NOT_VERY_EFFECTIVE"),
    ("GRASS", "STEEL", "NOT_VERY_EFFECTIVE"), ("PSYCHIC_TYPE", "STEEL", "NOT_VERY_EFFECTIVE"),
    ("ICE", "STEEL", "NOT_VERY_EFFECTIVE"), ("DRAGON", "STEEL", "NOT_VERY_EFFECTIVE"),
    # Dark attacking
    ("DARK", "PSYCHIC_TYPE", "SUPER_EFFECTIVE"), ("DARK", "GHOST", "SUPER_EFFECTIVE"),
    ("DARK", "FIGHTING", "NOT_VERY_EFFECTIVE"), ("DARK", "DARK", "NOT_VERY_EFFECTIVE"),
    ("DARK", "STEEL", "NOT_VERY_EFFECTIVE"),
    # attacking Dark
    ("FIGHTING", "DARK", "SUPER_EFFECTIVE"), ("BUG", "DARK", "SUPER_EFFECTIVE"),
    ("PSYCHIC_TYPE", "DARK", "NO_EFFECT"),
    ("GHOST", "DARK", "NOT_VERY_EFFECTIVE"),
]

# Pseudo-animation const slots to drop so NUM_ATTACK_ANIMS stays <= 255 after
# the 61 new moves push it up by 61. 165 real + 61 new = 226 NUM_ATTACKS; the
# 37 pseudo-anims would then run 227..263 (>255). Trimming these 8 (all verified
# zero-reference outside move_constants.asm; ANIM_B4 IS referenced so it's kept,
# ANIM_B9 kept) brings the ceiling to exactly 255. Both the const line AND its
# 1:1 pointer in AttackAnimationPointers are removed together by inject.
ANIM_TRIM = ["ANIM_A8", "ANIM_B1", "ANIM_B2", "ANIM_B3",
             "ANIM_B5", "ANIM_B6", "ANIM_B7", "ANIM_B8"]

# Every new move points its per-move animation slot at a known-safe vanilla
# animation (Gen1 has no data for these moves). POUND is a plain physical hit
# that never crashes; status moves just show it harmlessly.
GENERIC_ANIM = "PoundAnim"
GENERIC_SFX = "SFX_POUND"


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def parse_moves():
    """name -> dict(effect, power, type, acc, pp) from pokecrystal moves.asm."""
    s = _read(os.path.join(PC, "data/moves/moves.asm"))
    out = {}
    for m in re.finditer(
        r"^\tmove (\w+),\s*(\w+),\s*(\d+),\s*(\w+),\s*(\d+),\s*(\d+)", s, re.M):
        name, effect, power, typ, acc, pp = m.groups()
        out[name] = dict(effect=effect, power=int(power),
                         type=MOVE_TYPE_REMAP.get(typ, typ), acc=int(acc), pp=int(pp))
    return out


def parse_names():
    """move const -> display name (li "..."), Gen1 order gives the const order."""
    s = _read(os.path.join(PC, "data/moves/names.asm"))
    names = re.findall(r'^\tli "([^"]*)"', s, re.M)
    consts = re.findall(r"^\s*const ([A-Z0-9_]+)", _read(
        os.path.join(PC, "constants/move_constants.asm")), re.M)
    # constants list begins at POUND (id 1); names list is parallel
    return {consts[i + 1]: nm for i, nm in enumerate(names) if i + 1 < len(consts)}


def gen1_move_set():
    s = _read(os.path.join(PY, "constants/move_constants.asm"))
    return set(re.findall(r"^\s*const ([A-Z0-9_]+)", s, re.M))


def needed_gen2_moves(dex_list):
    """Ordered list of Gen2-only move consts learned (level-up) by dex_list,
    de-duplicated, in first-seen order."""
    gen1 = gen1_move_set()
    order, blocks = gd._evos_blocks()
    consts = gd._dex_to_const()
    seen, result = set(), []
    for dex in dex_list:
        block = blocks[order[dex - 1]]
        in_learn = False
        for line in block:
            t = line.strip()
            if not t.startswith("db"):
                continue
            args = [a.strip() for a in t[2:].split(";")[0].split(",")]
            if args == ["0"]:
                if in_learn:
                    break
                in_learn = True
                continue
            if in_learn and len(args) == 2:
                mv = args[1]
                if mv not in gen1 and mv not in seen:
                    seen.add(mv); result.append(mv)
    return result


def build_move_table(dex_list):
    """Return list of dicts for each new move: {C, name, effect, power, type,
    acc, pp}. C = const (Gen2 token); name = display (<=12, uppercased)."""
    moves = parse_moves()
    names = parse_names()
    out = []
    for c in needed_gen2_moves(dex_list):
        if c not in moves:
            continue  # safety: move with no data row (shouldn't happen)
        d = dict(moves[c])
        if c in POWER_OVERRIDE:
            d["power"] = POWER_OVERRIDE[c]
        disp = names.get(c, c.replace("_", " "))[:MAX_NAME]
        out.append(dict(C=c, name=disp, **d))
    return out


# ---------- ASM emitters (shared by simple + full; effect chosen by caller) ----------
def moves_rows(new_moves, resolve_effect):
    """`move` table rows for moves.asm. resolve_effect(move)->effect const str.
    Animation field doubles as the move id (the macro's \\1), so it MUST be the
    move's own const for damage/typing to work; the visual anim is set by the
    AttackAnimationPointers entry, not this field."""
    rows = []
    for m in new_moves:
        rows.append(f"\tmove {m['C']+',':<14} {resolve_effect(m)+',':<28} "
                    f"{m['power']:3}, {m['type']+',':<14} {m['acc']:3}, {m['pp']:2}\n")
    return "".join(rows)


def names_rows(new_moves):
    return "".join(f'\tli "{m["name"]}"\n' for m in new_moves)


def anim_rows(new_moves):
    """Per-move pointers for the first AttackAnimationPointers table."""
    return "".join(f"\tdw {GENERIC_ANIM}\n" for _ in new_moves)


def sfx_rows(new_moves):
    return "".join(f"\tdb {GENERIC_SFX+',':<22} $00, $80 ; {m['C']}\n" for m in new_moves)


if __name__ == "__main__":
    tbl = build_move_table(list(range(152, 252)))
    print(f"{len(tbl)} Gen2-only moves needed by dex 152-251")
    longnames = [m["C"] for m in tbl if len(m["name"]) >= MAX_NAME]
    print(f"names at/over {MAX_NAME} chars: {longnames}")
    types = sorted({m["type"] for m in tbl})
    print(f"move types used: {types}")
    for m in tbl[:8]:
        print(f"  {m['C']:14} {m['name']:13} {m['type']:13} pow={m['power']:3} "
              f"acc={m['acc']:3} pp={m['pp']:2} eff={m['effect']}")
