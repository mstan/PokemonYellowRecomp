#!/usr/bin/env python3
"""
Build a VALIDATION save for the extended (215-mon) Pokemon Yellow:
  * migrate the 100% vanilla Yellow .sav to the larger-Pokedex layout,
  * mark the WHOLE Pokedex (1..215) owned + seen,
  * fill the party (6) and all 12 PC boxes (240) with Johto mon (dex 152-215),
  * recompute the main-data + per-bank box checksums.

Writes to a NEW file; never touches the live recomp/build/*.sav.

All SRAM/WRAM offsets come from pokeyellow/pokeyellow.sym (this exact build),
so the script self-corrects if the layout changes. Mon data (types/stats/
moves) come from gen2_data (same source the ROM was built from). Internal
species index = $BF + (dex-152), because injection put dex 152..215 into the
contiguous index block $BF..$FE.
"""
import os, re, sys
import gen2_data

HERE = os.path.dirname(os.path.abspath(__file__))
SYM = os.path.join(HERE, "pokeyellow", "pokeyellow.sym")
SRC = r"C:\Users\Matthew\Desktop\Pokemon - Yellow Version - Special Pikachu Edition (USA, Europe) (CGB+SGB Enhanced).sav"
DST = os.path.join(HERE, "recomp", "build", "Pokemon_Yellow_Extended_FILLED.sav")

NUM_POKEMON = 251
DEX_BYTES = (NUM_POKEMON + 7) // 8        # 32
BOX_SIZE = 1122                            # bytes per stored box
BOX_SLOTS = 20
NUM_BOXES = 12

# Gen1 type constant values (type_constants.asm has gaps; these are canonical).
TYPE = {"NORMAL":0x00,"FIGHTING":0x01,"FLYING":0x02,"POISON":0x03,"GROUND":0x04,
        "ROCK":0x05,"BUG":0x07,"GHOST":0x08,"FIRE":0x14,"WATER":0x15,"GRASS":0x16,
        "ELECTRIC":0x17,"PSYCHIC_TYPE":0x18,"ICE":0x19,"DRAGON":0x1A}


def sym_addr(name):
    """Return (bank, addr) for a symbol from the .sym file."""
    with open(SYM, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"([0-9a-fA-F]{2,}):([0-9a-fA-F]{4})\s+" + re.escape(name) + r"\s*$", line)
            if m:
                return int(m.group(1), 16), int(m.group(2), 16)
    raise KeyError(name)


def sram_file_off(bank, addr):
    """SRAM bank+addr -> .sav file offset (8KB banks; SRAM window $A000)."""
    return bank * 0x2000 + (addr - 0xA000)


def move_value_map():
    s = open(os.path.join(HERE, "pokeyellow", "constants", "move_constants.asm"), encoding="utf-8").read()
    names = re.findall(r"^\s*const ([A-Z0-9_]+)", s, re.M)
    return {n: i for i, n in enumerate(names)}  # NO_MOVE=0, POUND=1, ...


def species_index_map():
    """Map species CONST -> internal index from the injected pokemon_constants.
    NO_MON is the first const ($00); contiguous mon sit at $BF-$FE and gap-reuse
    mon at former const_skip slots, so this is the only reliable source."""
    s = open(os.path.join(HERE, "pokeyellow", "constants", "pokemon_constants.asm"), encoding="utf-8").read()
    out, idx = {}, -1
    for line in s.splitlines():
        t = line.strip()
        if t.startswith("const ") or t == "const_skip" or t.startswith("const_skip "):
            idx += 1
            m = re.match(r"const ([A-Z0-9_]+)", t)
            if m:
                out[m.group(1)] = idx
    return out


def gen1_name(s):
    """Gen1 charmap, 11 bytes, 0x50-terminated/padded."""
    out = bytearray()
    for c in s[:10]:
        if "A" <= c <= "Z": out.append(0x80 + ord(c) - ord("A"))
        elif "a" <= c <= "z": out.append(0xA0 + ord(c) - ord("a"))
        elif "0" <= c <= "9": out.append(0xF6 + ord(c) - ord("0"))
        elif c == " ": out.append(0x7F)
        elif c == "-": out.append(0xE3)   # Gen1 charmap hyphen (HO-OH)
        elif c == ".": out.append(0xE8)
        else: out.append(0x50)
    out.append(0x50)
    while len(out) < 11: out.append(0x50)
    return bytes(out[:11])


def be16(v): return bytes([(v >> 8) & 0xFF, v & 0xFF])
def be24(v): return bytes([(v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])


def exp_at_50(growth):
    n = 50
    if growth == "GROWTH_MEDIUM_SLOW": return int(1.2*n**3 - 15*n**2 + 100*n - 140)
    if growth == "GROWTH_FAST":        return int(0.8*n**3)
    if growth == "GROWTH_SLOW":        return int(1.25*n**3)
    return n**3  # MEDIUM_FAST and the rare slightly_* (good enough for validation)


def stats_at_50(base):
    hp, atk, df, spd, spc = base  # DV 15, statexp 0, level 50
    return (hp + 75, atk + 20, df + 20, spd + 20, spc + 20)


MOVE = move_value_map()
SPECIES_IDX = species_index_map()


def mon_core(m, otid):
    """Shared 33-byte box-struct prefix for a generated mon dict m."""
    species = SPECIES_IDX[m["C"]]
    t1, t2 = TYPE[m["ty"][0]], TYPE[m["ty"][1]]
    moves = [MOVE.get(mv, 0) for mv in m["l1"]]
    pp = [20 if mv else 0 for mv in moves]
    hp, atk, df, spd, spc = stats_at_50(m["st"])
    exp = exp_at_50(m["growth"])
    s = bytearray()
    s += bytes([species])
    s += be16(hp)                 # current HP
    s += bytes([50, 0, t1, t2, 0])  # boxlevel, status, type1, type2, catchrate/item
    s += bytes((moves + [0, 0, 0, 0])[:4])
    s += otid
    s += be24(exp)
    s += be16(0) * 5              # stat exp
    s += be16(0xFFFF)            # DVs (max)
    s += bytes((pp + [0, 0, 0, 0])[:4])
    assert len(s) == 33, len(s)
    return s, species, (hp, atk, df, spd, spc)


def box_struct(m, otid):
    s, species, _ = mon_core(m, otid)
    return bytes(s), species


def party_struct(m, otid):
    s, species, st = mon_core(m, otid)
    hp, atk, df, spd, spc = st
    s = bytearray(s)
    s += bytes([50])
    s += be16(hp) + be16(atk) + be16(df) + be16(spd) + be16(spc)
    assert len(s) == 44, len(s)
    return bytes(s), species


def build_box(entries, otname):
    """entries: list of (struct33, species, nick) up to 20."""
    n = len(entries)
    b = bytearray([n])
    slist = bytearray(BOX_SLOTS + 1)
    for i, (_, sp, _) in enumerate(entries):
        slist[i] = sp
    slist[n] = 0xFF
    b += slist
    for i in range(BOX_SLOTS):
        b += entries[i][0] if i < n else bytes(33)
    for i in range(BOX_SLOTS):
        b += otname if i < n else bytes(11)
    for i in range(BOX_SLOTS):
        b += entries[i][2] if i < n else bytes(11)
    assert len(b) == BOX_SIZE, len(b)
    return bytes(b)


def csum(buf):
    return (~(sum(buf) & 0xFF)) & 0xFF


def main():
    stock = open(SRC, "rb").read()
    if len(stock) != 32768:
        sys.exit(f"expected 32768-byte SRAM, got {len(stock)}")

    # ---- resolve offsets from the symbol file ----
    pn_b, pn_a = sym_addr("sPlayerName"); F_PLAYERNAME = sram_file_off(pn_b, pn_a)
    md_b, md_a = sym_addr("sMainData");   F_MAIN = sram_file_off(md_b, md_a)
    pd_b, pd_a = sym_addr("sPartyData");   F_PARTY = sram_file_off(pd_b, pd_a)
    cb_b, cb_a = sym_addr("sCurBoxData");  F_CURBOX = sram_file_off(cb_b, cb_a)
    ck_b, ck_a = sym_addr("sMainDataCheckSum"); F_CHK = sram_file_off(ck_b, ck_a)
    _, owned_w = sym_addr("wPokedexOwned")
    _, curbox_w = sym_addr("wCurrentBoxNum")
    _, pid_w = sym_addr("wPlayerID")
    # main data block mirrors WRAM starting at wPokedexOwned.
    F_OWNED = F_MAIN                                   # owned at start of sMainData
    F_SEEN = F_OWNED + DEX_BYTES
    F_REST = F_SEEN + DEX_BYTES
    F_PID = F_MAIN + (pid_w - owned_w)
    F_CURBOXNUM = F_MAIN + (curbox_w - owned_w)
    # stock (vanilla 151) layout: 19-byte dex arrays.
    S_OWNED = F_MAIN
    S_SEEN = S_OWNED + 19
    S_REST = S_SEEN + 19
    S_CHK = F_CHK - (2 * (DEX_BYTES - 19))             # stock checksum sits earlier

    ext = bytearray(stock)  # keep sPlayerName + scratch; we overwrite the rest

    # ---- 1. main data: dex arrays (all set) + the rest shifted from stock ----
    full = bytearray(b"\xFF" * DEX_BYTES)
    # clear bits beyond NUM_POKEMON in the last byte
    extra = DEX_BYTES * 8 - NUM_POKEMON
    if extra:
        full[-1] = (0xFF >> extra)
    ext[F_OWNED:F_OWNED + DEX_BYTES] = full
    ext[F_SEEN:F_SEEN + DEX_BYTES] = full
    rest_len = S_CHK - S_REST
    ext[F_REST:F_REST + rest_len] = stock[S_REST:S_REST + rest_len]

    otname = bytes(ext[F_PLAYERNAME:F_PLAYERNAME + 11])
    otid = bytes(ext[F_PID:F_PID + 2])

    # ---- 2. mon data for dex 152..215 ----
    mons = gen2_data.build_mons(list(range(152, 252)))
    by_dex = {m["dex"]: m for m in mons}
    order = list(range(152, 252))  # 100 Johto mon, in dex order

    # ---- 3. party: gap-reuse mon (216+) so the new index path is testable ----
    party = bytearray()
    party_dex = [251, 249, 250, 248, 245, 216]  # Celebi, Lugia, Ho-Oh, Tyranitar, Suicune, Teddiursa
    party += bytes([len(party_dex)])
    structs = []
    for d in party_dex:
        st, sp = party_struct(by_dex[d], otid)
        structs.append((st, sp, gen1_name(by_dex[d]["name"])))
    party += bytes([sp for _, sp, _ in structs] + [0xFF] + [0] * (6 - len(party_dex)))
    for i in range(6):
        party += structs[i][0] if i < len(structs) else bytes(44)
    for i in range(6):
        party += otname if i < len(structs) else bytes(11)
    for i in range(6):
        party += structs[i][2] if i < len(structs) else bytes(11)
    assert len(party) == 404, len(party)
    ext[F_PARTY:F_PARTY + 404] = party

    # ---- 4. all 12 boxes: cycle through the 64 Johto mon ----
    flat = []
    i = 0
    for _ in range(NUM_BOXES * BOX_SLOTS):
        d = order[i % len(order)]; i += 1
        st, sp = box_struct(by_dex[d], otid)
        flat.append((st, sp, gen1_name(by_dex[d]["name"])))
    boxes = [flat[b * BOX_SLOTS:(b + 1) * BOX_SLOTS] for b in range(NUM_BOXES)]
    box_bytes = [build_box(boxes[b], otname) for b in range(NUM_BOXES)]

    b1_b, b1_a = sym_addr("sBox1");  F_BOX1 = sram_file_off(b1_b, b1_a)
    b7_b, b7_a = sym_addr("sBox7");  F_BOX7 = sram_file_off(b7_b, b7_a)
    for b in range(6):
        ext[F_BOX1 + b * BOX_SIZE:F_BOX1 + (b + 1) * BOX_SIZE] = box_bytes[b]
    for b in range(6):
        ext[F_BOX7 + b * BOX_SIZE:F_BOX7 + (b + 1) * BOX_SIZE] = box_bytes[6 + b]

    # current box = box 1
    ext[F_CURBOXNUM] = 0x00
    ext[F_CURBOX:F_CURBOX + BOX_SIZE] = box_bytes[0]

    # ---- 5. checksums ----
    # main data (sGameData..sGameDataEnd) = [F_PLAYERNAME, F_CHK)
    ext[F_CHK] = csum(ext[F_PLAYERNAME:F_CHK])
    # per-bank: all-boxes checksum + 6 individual, for banks 2 and 3
    for allname, indname, base in (
        ("sBank2AllBoxesChecksum", "sBank2IndividualBoxChecksums", F_BOX1),
        ("sBank3AllBoxesChecksum", "sBank3IndividualBoxChecksums", F_BOX7)):
        a_b, a_a = sym_addr(allname); F_ALL = sram_file_off(a_b, a_a)
        i_b, i_a = sym_addr(indname); F_IND = sram_file_off(i_b, i_a)
        ext[F_ALL] = csum(ext[base:base + 6 * BOX_SIZE])
        for b in range(6):
            ext[F_IND + b] = csum(ext[base + b * BOX_SIZE:base + (b + 1) * BOX_SIZE])

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    open(DST, "wb").write(ext)
    print(f"wrote {DST}")
    print(f"  OT='{otname.hex()}' id={otid.hex()}  main chk=0x{ext[F_CHK]:02X}")
    print(f"  dex: all {NUM_POKEMON} owned+seen (last byte 0x{full[-1]:02X})")
    print(f"  party: {len(party_dex)} ({[hex(s) for _,s,_ in structs]})")
    print(f"  boxes: 12 x {BOX_SLOTS} = {NUM_BOXES*BOX_SLOTS} Johto mon (cycled over {len(order)})")
    print(f"  offsets: party@0x{F_PARTY:04X} curbox@0x{F_CURBOX:04X} box1@0x{F_BOX1:04X} box7@0x{F_BOX7:04X} chk@0x{F_CHK:04X}")


if __name__ == "__main__":
    main()
