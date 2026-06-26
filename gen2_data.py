#!/usr/bin/env python3
"""
gen2_data.py -- generate Gen1-format MON dicts for a Johto dex range by
parsing pokecrystal's own data, so inject_gen2.py never hand-transcribes.

Output dicts use inject_gen2.py's schema (extended):
  C, Camel, f, dex, st=(hp,atk,df,spd,spc), ty=(t1,t2), exp, cr, growth,
  pal, icon, evos=[(method, ...)], l1=(m1..m4), learn=[(lvl,move)],
  tmhm="<line or ''>", cat, ft, inch, wt, dexbody=[text lines]

Gen2 -> Gen1 lossy translation (intentional, first-pass "Gen1-only" content):
  * Special stat  = Gen2 Sp.Atk (Gen1 has one Special).
  * DARK/STEEL    -> nearest Gen1 type (no real Dark/Steel yet).
  * Learnset/TMHM -> filtered to moves that exist in THIS ROM.
  * Evolutions    -> LEVEL/ITEM(Gen1 stone)/TRADE pass through; happiness/
                     stat/Gen2-item methods fall back to a level evolution.
  * Evo targets not present in the ROM (Gen1 mon or this batch) are dropped.
Everything is sourced from pokecrystal; validity sets are read from THIS
ROM's constant files, so the generator self-corrects as the ROM grows.
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, "pokeyellow")
PC = os.path.join(HERE, "pokecrystal")

# DARK/STEEL don't exist in Gen1. Map to the nearest existing type (thematic,
# and physical/special class follows the target type automatically).
TYPE_REMAP = {"DARK": "GHOST", "STEEL": "ROCK"}
GEN1_STONES = {"MOON_STONE", "FIRE_STONE", "WATER_STONE", "THUNDER_STONE", "LEAF_STONE"}

# Primary-type -> SGB palette / menu icon (Gen1 vocab).
TYPE_PAL = {
    "GRASS": "PAL_GREENMON", "BUG": "PAL_GREENMON", "POISON": "PAL_PURPLEMON",
    "FIRE": "PAL_REDMON", "FIGHTING": "PAL_REDMON", "WATER": "PAL_BLUEMON",
    "ICE": "PAL_CYANMON", "FLYING": "PAL_CYANMON", "ELECTRIC": "PAL_YELLOWMON",
    "GROUND": "PAL_BROWNMON", "ROCK": "PAL_BROWNMON", "GHOST": "PAL_PURPLEMON",
    "PSYCHIC_TYPE": "PAL_PINKMON", "NORMAL": "PAL_BROWNMON", "DRAGON": "PAL_BLUEMON",
}
TYPE_ICON = {
    "GRASS": "ICON_GRASS", "BUG": "ICON_BUG", "POISON": "ICON_SNAKE",
    "FIRE": "ICON_MON", "FIGHTING": "ICON_MON", "WATER": "ICON_WATER",
    "ICE": "ICON_WATER", "FLYING": "ICON_BIRD", "ELECTRIC": "ICON_MON",
    "GROUND": "ICON_QUADRUPED", "ROCK": "ICON_HELIX", "GHOST": "ICON_MON",
    "PSYCHIC_TYPE": "ICON_FAIRY", "NORMAL": "ICON_QUADRUPED", "DRAGON": "ICON_SNAKE",
}

NAME_OVERRIDE = {"HO_OH": "HO-OH"}  # only underscore'd display name in 161-251
# Mon whose sprites aren't at gfx/pokemon/<name>/ : Unown stores forms in
# gfx/pokemon/unown_<letter>/; use form A as its single Gen1 sprite.
SPRDIR_OVERRIDE = {"UNOWN": "unown_a"}


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def camel(const):
    return "".join(part.capitalize() for part in const.split("_"))


# ---------- validity sets, read from THIS ROM ----------
def _valid_moves():
    s = _read(os.path.join(PY, "constants/move_constants.asm"))
    return set(re.findall(r"^\s*const ([A-Z0-9_]+)", s, re.M))


def _valid_tmhm():
    s = _read(os.path.join(PY, "constants/item_constants.asm"))
    return set(re.findall(r"add_(?:tm|hm) ([A-Z0-9_]+)", s))


def _valid_species():
    """Real species constants already in the ROM (Gen1 set, pre-CHIKORITA)."""
    s = _read(os.path.join(PY, "constants/pokemon_constants.asm"))
    out = set()
    for m in re.finditer(r"^\s*const ([A-Z0-9_]+)", s, re.M):
        if m.group(1) == "CHIKORITA":
            break
        out.add(m.group(1))
    return out


# ---------- pokecrystal parsers ----------
def _dex_to_const():
    s = _read(os.path.join(PC, "constants/pokemon_constants.asm"))
    return re.findall(r"^\s*const ([A-Z0-9_]+)", s, re.M)


def _evos_blocks():
    ptrs = _read(os.path.join(PC, "data/pokemon/evos_attacks_pointers.asm"))
    order = re.findall(r"dw ([A-Za-z0-9]+)EvosAttacks", ptrs)
    body = _read(os.path.join(PC, "data/pokemon/evos_attacks.asm"))
    blocks, cur, buf = {}, None, []
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z0-9]+)EvosAttacks:", line)
        if m:
            if cur:
                blocks[cur] = buf
            cur, buf = m.group(1), []
        elif cur is not None:
            buf.append(line)
    if cur:
        blocks[cur] = buf
    return order, blocks


def _parse_base_stats(const):
    s = _read(os.path.join(PC, f"data/pokemon/base_stats/{const.lower()}.asm"))
    st = re.search(r"db\s+(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", s)
    hp, atk, df, spd, sat, sdf = (int(x) for x in st.groups())
    ty = re.search(r"db ([A-Z_]+), ([A-Z_]+) ; type", s).groups()
    cr = int(re.search(r"db (\d+) ; catch rate", s).group(1))
    exp = int(re.search(r"db (\d+) ; base exp", s).group(1))
    growth = re.search(r"db (GROWTH_[A-Z_]+) ; growth rate", s).group(1)
    tm = re.search(r"^\ttmhm (.+)$", s, re.M)
    tmhm = [t.strip() for t in tm.group(1).split(",")] if tm else []
    t1 = TYPE_REMAP.get(ty[0], ty[0])
    t2 = TYPE_REMAP.get(ty[1], ty[1])
    return dict(st=(hp, atk, df, spd, sat), ty=(t1, t2), cr=cr, exp=exp,
                growth=growth, tmhm_raw=tmhm)


def _parse_dex_entry(const):
    s = _read(os.path.join(PC, f"data/pokemon/dex_entries/{const.lower()}.asm")).splitlines()
    cat = re.search(r'db "([^"@]*)', s[0]).group(1)
    h, w = re.search(r"dw (\d+), (\d+)", s[1]).groups()
    ft, inch, wt = int(h) // 100, int(h) % 100, int(w)
    body = []
    for line in s[2:]:
        if not body and not line.strip():
            continue
        body.append(line.rstrip())
    while body and not body[-1].strip():
        body.pop()
    return cat, ft, inch, wt, body


def _xlate_dex_body(body):
    """Gen2 dex text -> Gen1 _<Mon>DexEntry inner lines (text/next/page), no dex."""
    out, started = [], False
    for line in body:
        t = line.strip()
        if t.startswith("db ") and not started:
            txt = re.search(r'db\s+(".*")', line).group(1)
            out.append(f"\ttext {txt}")
            started = True
        elif t.startswith("next"):
            out.append("\t" + t)
        elif t.startswith("page"):
            out.append("")
            out.append("\t" + t)
    if out:
        out[-1] = out[-1].replace('@"', '"')
    return out


def _parse_evos_learn(block, valid_moves, valid_species, valid_stones):
    evos, learn, section = [], [], "evo"
    for line in block:
        t = line.strip()
        if not t.startswith("db"):
            continue
        args = [a.strip() for a in t[2:].split(";")[0].split(",")]
        if section == "evo":
            if args == ["0"]:
                section = "learn"
                continue
            method, target = args[0], args[-1]
            if target not in valid_species:
                continue
            if method == "EVOLVE_LEVEL":
                evos.append(("LEVEL", int(args[1]), target))
            elif method == "EVOLVE_ITEM":
                item = args[1]
                evos.append(("ITEM", item, target) if item in valid_stones
                            else ("LEVEL", 30, target))
            elif method == "EVOLVE_TRADE":
                evos.append(("TRADE", target))
            elif method == "EVOLVE_HAPPINESS":
                evos.append(("LEVEL", 20, target))
            elif method == "EVOLVE_STAT":
                evos.append(("LEVEL", int(args[1]), target))
        else:
            if args == ["0"]:
                break
            lvl, move = int(args[0]), args[1]
            if move in valid_moves:
                learn.append((lvl, move))
    return evos, learn


# ---------- public API ----------
def build_mons(dex_list, extra_species=None):
    valid_moves = _valid_moves()
    valid_tmhm = _valid_tmhm()
    species = _valid_species()
    consts = _dex_to_const()
    new_consts = {consts[d - 1] for d in dex_list}
    species = species | new_consts | set(extra_species or [])

    order, evblocks = _evos_blocks()
    mons = []
    for dex in dex_list:
        const = consts[dex - 1]
        bs = _parse_base_stats(const)
        cat, ft, inch, wt, raw_body = _parse_dex_entry(const)
        label = order[dex - 1]
        evos, learn = _parse_evos_learn(evblocks[label], valid_moves, species, GEN1_STONES)

        l1 = [mv for lvl, mv in learn if lvl == 1 and mv in valid_moves][:4]
        if not l1:
            l1 = [learn[0][1]] if learn else ["TACKLE"]
        l1 = (l1 + ["NO_MOVE", "NO_MOVE", "NO_MOVE", "NO_MOVE"])[:4]
        learn_up = [(lvl, mv) for lvl, mv in learn if lvl > 1]

        tmhm_tokens = [t for t in bs["tmhm_raw"] if t in valid_tmhm]
        # an empty list still needs the macro: it emits the (all-zero) TM bytes
        # that are a mandatory part of the base_stats struct.
        tmhm_line = "\ttmhm " + ", ".join(tmhm_tokens) if tmhm_tokens else "\ttmhm"

        t1 = bs["ty"][0]
        mons.append(dict(
            C=const, Camel=camel(const), f=const.lower(), dex=dex,
            sprdir=SPRDIR_OVERRIDE.get(const, const.lower()),
            st=bs["st"], ty=bs["ty"], exp=bs["exp"], cr=bs["cr"], growth=bs["growth"],
            pal=TYPE_PAL.get(t1, "PAL_GRAYMON"), icon=TYPE_ICON.get(t1, "ICON_MON"),
            name=NAME_OVERRIDE.get(const, const),
            evos=evos, l1=tuple(l1), learn=learn_up, tmhm=tmhm_line,
            cat=cat, ft=ft, inch=inch, wt=wt,
            dexbody=_xlate_dex_body(raw_body),
        ))
    return mons


if __name__ == "__main__":
    import sys
    lo, hi = (int(x) for x in (sys.argv[1:3] or [161, 165]))
    for m in build_mons(list(range(lo, hi + 1))):
        print(f"--- #{m['dex']} {m['C']} ({m['name']}) ---")
        print(f"  st={m['st']} ty={m['ty']} exp={m['exp']} cr={m['cr']} {m['growth']}")
        print(f"  pal={m['pal']} icon={m['icon']}")
        print(f"  evos={m['evos']}")
        print(f"  l1={m['l1']}")
        print(f"  learn={m['learn']}")
        print(f"  tmhm={m['tmhm']}")
        print(f"  cat={m['cat']!r} {m['ft']}'{m['inch']}\" {m['wt']/10}lb")
        for ln in m["dexbody"]:
            print(f"    |{ln}")
