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
        disp = names.get(c, c.replace("_", " "))[:MAX_NAME]
        out.append(dict(C=c, name=disp, **d))
    return out


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
