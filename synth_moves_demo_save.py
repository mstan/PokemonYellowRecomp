#!/usr/bin/env python3
"""
synth_moves_demo_save.py -- build a demo save whose party shows off the injected
Gen2 moves (MOVE_MODE=full ROM). Bases off an existing extended-ROM save (keeps
the player's name/ID/badges/items), and only REPLACES the 6-mon party + sets the
dex flags for those mon + fixes the checksum. Every species index, move id, type
value, base stat and PP is resolved from the freshly-injected pokeyellow/ files,
so it self-corrects to whatever the build actually produced.

Offsets are derived for the 251-dex extended layout and verified against the
base save's checksum on load (aborts if the base doesn't validate).
"""
import os, re, math

PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokeyellow")
BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recomp", "build")
BASE_SAV = os.path.join(BUILD, "Pokemon_Yellow_Extended.sav.preMovesDemo")
OUT_SAV  = os.path.join(BUILD, "Pokemon_Yellow_Extended.sav")
BUNDLE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist",
                        "Pokemon_Yellow_Extended_MovesDemo.sav")

# extended (251-dex) save-file offsets, derived from pokeyellow.sym:
#   sPlayerName=0xA598->0x2598 ; sMainData=0xA5A3->0x25A3 (= wPokedexOwned) ;
#   wPokedexSeen-wPokedexOwned=0x20 ; wPlayerID-wPokedexOwned=0x7C ;
#   sPartyData=0xAF46->0x2F46 ; sMainDataCheckSum=0xB53D->0x353D.
PLAYERNAME = 0x2598
OWNED, SEEN = 0x25A3, 0x25C3
PLAYERID = 0x261F
PARTY = 0x2F46
CHK_START, CHK = 0x2598, 0x353D

LEVEL = 50

# Showcase party: (species const, [<=4 move consts], nickname). 24 distinct new
# moves spanning every tier -- the 2 NATIVE handlers (Heal Bell, Psych Up), real
# Dark/Steel STAB, heals, burn, and a wide sample of best-effort fallbacks.
PARTY_DEF = [
    ("TYRANITAR",  ["CRUNCH", "PURSUIT", "SANDSTORM", "ANCIENTPOWER"], "TYRANITAR"),   # Rock/Dark
    ("SKARMORY",   ["STEEL_WING", "METAL_CLAW", "SPIKES", "FALSE_SWIPE"], "SKARMORY"),  # Steel/Flying
    ("BLISSEY",    ["HEAL_BELL", "MILK_DRINK", "PRESENT", "SAFEGUARD"], "BLISSEY"),      # native Heal Bell
    ("GIRAFARIG",  ["PSYCH_UP", "FUTURE_SIGHT", "CRUNCH", "MIRROR_COAT"], "GIRAFARIG"),  # native Psych Up
    ("HO_OH",      ["SACRED_FIRE", "SUNNY_DAY", "MORNING_SUN", "AEROBLAST"], "HO-OH"),   # Fire/Flying
    ("MISDREAVUS", ["CURSE", "PERISH_SONG", "DESTINY_BOND", "PAIN_SPLIT"], "MISDREAVUS"),# Ghost
]


def _read(rel):
    with open(os.path.join(PY, rel), encoding="utf-8") as fh:
        return fh.read()


def species_index():
    """const|const_skip line ordinal (NO_MON = 0) -> species internal index."""
    idx, out = -1, {}
    for line in _read("constants/pokemon_constants.asm").splitlines():
        t = line.split(";")[0].strip()
        if t.startswith("const ") or t == "const_skip" or t.startswith("const_skip "):
            idx += 1
            if t.startswith("const "):
                out[t.split()[1]] = idx
    return out


def move_table():
    """name -> (id, pp). id = 1-based row order in moves.asm (the `move` table)."""
    out, i = {}, 0
    for m in re.finditer(r"^\tmove (\w+),.*?,\s*(\d+)\s*$", _read("data/moves/moves.asm"), re.M):
        i += 1
        out[m.group(1)] = (i, int(m.group(2)))
    return out


def type_values():
    """type const -> numeric value (honours const_next / const_skip / DEF lines)."""
    val, out = 0, {}
    for line in _read("constants/type_constants.asm").splitlines():
        t = line.split(";")[0].strip()
        if t.startswith("const_next"):
            val = int(re.search(r"const_next\s+(\d+)", t).group(1))
        elif t == "const_skip" or t.startswith("const_skip "):
            n = re.search(r"const_skip\s+(\d+)", t)
            val += int(n.group(1)) if n else 1
        elif t.startswith("const "):
            out[t.split()[1]] = val; val += 1
    return out


def base_stats(const):
    s = _read(f"data/pokemon/base_stats/{const.lower()}.asm")
    hp, atk, df, spd, spc = (int(x) for x in re.search(
        r"db\s+(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", s).groups())
    t1, t2 = re.search(r"db ([A-Z_]+), ([A-Z_]+) ; type", s).groups()
    growth = re.search(r"db (GROWTH_[A-Z_]+) ; growth rate", s).group(1)
    return dict(st=(hp, atk, df, spd, spc), ty=(t1, t2), growth=growth)


def stat_at(base, lvl, is_hp=False):
    core = ((base + 15) * 2 * lvl) // 100          # DV 15, stat exp 0
    return core + lvl + 10 if is_hp else core + 5


def exp_at(growth, n):
    if growth == "GROWTH_MEDIUM_SLOW":
        return max(0, int((6 * n**3) / 5 - 15 * n**2 + 100 * n - 140))
    if growth == "GROWTH_FAST":
        return (4 * n**3) // 5
    if growth == "GROWTH_SLOW":
        return (5 * n**3) // 4
    return n**3                                    # MEDIUM_FAST + any exotic


def be16(v): return bytes([(v >> 8) & 0xFF, v & 0xFF])
def be24(v): return bytes([(v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])


def encode_name(s, width=11):
    out = bytearray()
    for c in s:
        if 'A' <= c <= 'Z': out.append(0x80 + ord(c) - ord('A'))
        elif 'a' <= c <= 'z': out.append(0xA0 + ord(c) - ord('a'))
        elif '0' <= c <= '9': out.append(0xF6 + ord(c) - ord('0'))
        elif c == ' ': out.append(0x7F)
        elif c == '-': out.append(0xE3)
        else: out.append(0x50)
    out.append(0x50)
    while len(out) < width: out.append(0x50)
    return bytes(out[:width])


def build_mon(const, move_consts, sp_idx, moves, types, otid):
    bs = base_stats(const)
    hp, atk, df, spd, spc = bs["st"]
    HP = stat_at(hp, LEVEL, is_hp=True)
    stats = [HP, stat_at(atk, LEVEL), stat_at(df, LEVEL),
             stat_at(spd, LEVEL), stat_at(spc, LEVEL)]
    mv_ids = [moves[m][0] for m in move_consts]
    mv_pp  = [moves[m][1] for m in move_consts]
    t1, t2 = (types[bs["ty"][0]], types[bs["ty"][1]])
    s = bytearray()
    s += bytes([sp_idx])
    s += be16(HP)                                  # current HP = full
    s += bytes([LEVEL])                            # BoxLevel
    s += bytes([0])                                # status
    s += bytes([t1, t2])                           # types
    s += bytes([0])                                # catch rate / held item
    s += bytes((mv_ids + [0, 0, 0, 0])[:4])
    s += otid
    s += be24(exp_at(bs["growth"], LEVEL))
    s += be16(0) * 5                               # stat exp
    s += be16(0xFFFF)                              # DVs (perfect)
    s += bytes((mv_pp + [0, 0, 0, 0])[:4])
    s += bytes([LEVEL])                            # Level
    for v in stats: s += be16(v)                   # MaxHP/Atk/Def/Spd/Spc
    assert len(s) == 44, len(s)
    return s


def main():
    sp = species_index()
    moves = move_table()
    types = type_values()

    data = bytearray(open(BASE_SAV, "rb").read())
    assert len(data) == 32768, "base save must be a 32 KB extended save"
    base_chk = (~sum(data[CHK_START:CHK])) & 0xFF
    assert base_chk == data[CHK], "base save checksum invalid -> wrong layout/offsets"

    otid = bytes(data[PLAYERID:PLAYERID + 2])
    otname = bytes(data[PLAYERNAME:PLAYERNAME + 11])

    structs, nicks, species = [], [], []
    for const, mv, nick in PARTY_DEF:
        species.append(sp[const])
        structs.append(build_mon(const, mv, sp[const], moves, types, otid))
        nicks.append(encode_name(nick))

    party = bytearray()
    party += bytes([len(PARTY_DEF)])
    party += bytes((species + [0xFF] + [0] * 6)[:7])      # species list + terminator
    for i in range(6): party += structs[i] if i < len(structs) else bytes(44)
    for i in range(6): party += otname if i < len(structs) else bytes(11)
    for i in range(6): party += nicks[i] if i < len(nicks) else bytes(11)
    assert len(party) == 404, len(party)
    data[PARTY:PARTY + 404] = party

    # dex: mark the 6 demo mon seen + owned. dex number = DEX_<const>; derive it
    # from pokedex_constants ordinal (DEX_CHIKORITA = 152, contiguous upward).
    dexnum = {}
    n = 0
    for line in _read("constants/pokedex_constants.asm").splitlines():
        t = line.split(";")[0].strip()
        if t.startswith("const DEX_"):
            n += 1; dexnum[t.split()[1][4:]] = n
    def setbit(base, d):
        data[base + (d - 1) // 8] |= 1 << ((d - 1) % 8)
    for const, _, _ in PARTY_DEF:
        d = dexnum[const]; setbit(OWNED, d); setbit(SEEN, d)

    data[CHK] = (~sum(data[CHK_START:CHK])) & 0xFF

    open(OUT_SAV, "wb").write(data)
    os.makedirs(os.path.dirname(BUNDLE), exist_ok=True)
    open(BUNDLE, "wb").write(data)

    print(f"OT id=0x{otid.hex()}  checksum=0x{data[CHK]:02X}")
    print(f"party @0x{PARTY:04X}: count={data[PARTY]}  species={[hex(b) for b in species]}")
    for const, mv, _ in PARTY_DEF:
        print(f"  {const:11} idx=0x{sp[const]:02X}  Lv{LEVEL}  moves="
              + ", ".join(f"{m}(#{moves[m][0]})" for m in mv))
    print(f"wrote {OUT_SAV}")
    print(f"wrote {BUNDLE}")


if __name__ == "__main__":
    main()
