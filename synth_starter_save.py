#!/usr/bin/env python3
"""
Take a FRESH new-game (extended-ROM) Yellow save and inject the 3 Johto
starters at Lv5 as the player's party. Designed to be run on a save the game
itself just created (name YELLOW, empty party) -> zero synthesis risk, we only
edit the party block + dex flags + checksum.

Output: overwrites the runner save AND writes a bundle copy.
"""
SAV = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\recomp\build\Pokemon_Yellow_Extended.sav"
BUNDLE = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\dist\Pokemon_Yellow_Extended.sav"

# extended-layout file offsets (see TECHNICAL_NOTES.md sec 3)
PLAYERNAME = 0x2598       # 11 bytes
OWNED, SEEN = 0x25A3, 0x25B7   # 20 bytes each
PARTY = 0x2F2E
PLAYERID = 0x2607
CHK_START, CHK = 0x2598, 0x3525

def be16(v): return bytes([(v >> 8) & 0xFF, v & 0xFF])
def be24(v): return bytes([(v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF])

def name(s):
    out = bytearray()
    for c in s:
        if 'A' <= c <= 'Z': out.append(0x80 + ord(c) - ord('A'))
        elif 'a' <= c <= 'z': out.append(0xA0 + ord(c) - ord('a'))
        elif '0' <= c <= '9': out.append(0xF6 + ord(c) - ord('0'))
        elif c == ' ': out.append(0x7F)
        else: out.append(0x50)
    out.append(0x50)
    while len(out) < 11: out.append(0x50)
    return bytes(out[:11])

EXP_L5 = 135  # medium-slow exp at level 5

def mon(species, t1, t2, moves, pp, level, hp, atk, df, spd, spc, otid):
    s = bytearray()
    s += bytes([species])
    s += be16(hp)                 # current HP = max
    s += bytes([level])           # BoxLevel
    s += bytes([0])               # status
    s += bytes([t1, t2])          # types
    s += bytes([0])               # catch rate / held item
    s += bytes((moves + [0,0,0,0])[:4])
    s += otid                     # OT id
    s += be24(EXP_L5)             # exp
    s += be16(0) * 5              # stat exp
    s += be16(0xFFFF)             # DVs (perfect)
    s += bytes((pp + [0,0,0,0])[:4])
    s += bytes([level])           # Level
    s += be16(hp)+be16(atk)+be16(df)+be16(spd)+be16(spc)  # stats
    assert len(s) == 44
    return bytes(s)

def main():
    import os
    data = bytearray(open(SAV, "rb").read())
    assert len(data) == 32768

    otid = bytes(data[PLAYERID:PLAYERID+2])
    otname = bytes(data[PLAYERNAME:PLAYERNAME+11])

    # types: GRASS=0x16 FIRE=0x14 WATER=0x15 ; moves TACKLE21 GROWL2d LEER2b SCRATCH0a
    structs = [
        mon(0xBF, 0x16,0x16, [0x21,0x2d], [35,40], 5, 21,11,13,11,11, otid),  # Chikorita
        mon(0xC2, 0x14,0x14, [0x21,0x2b], [35,40], 5, 20,11,10,13,12, otid),  # Cyndaquil
        mon(0xC5, 0x15,0x15, [0x0a,0x2b], [35,40], 5, 21,13,12,10,10, otid),  # Totodile
    ]
    nicks = [name("CHIKORITA"), name("CYNDAQUIL"), name("TOTODILE")]

    party = bytearray()
    party += bytes([3])                                   # count
    party += bytes([0xBF,0xC2,0xC5,0xFF,0x00,0x00,0x00])  # species + terminator
    for i in range(6): party += structs[i] if i < 3 else bytes(44)
    for i in range(6): party += otname if i < 3 else bytes(11)
    for i in range(6): party += nicks[i] if i < 3 else bytes(11)
    assert len(party) == 404
    data[PARTY:PARTY+404] = party

    # dex: seen + owned for the 3 starters (152/155/158)
    def setbit(base, dexnum):
        data[base + (dexnum-1)//8] |= 1 << ((dexnum-1) % 8)
    for d in (152, 155, 158):
        setbit(SEEN, d); setbit(OWNED, d)

    # checksum
    chk = (~sum(data[CHK_START:CHK])) & 0xFF
    data[CHK] = chk

    open(SAV, "wb").write(data)
    os.makedirs(os.path.dirname(BUNDLE), exist_ok=True)
    open(BUNDLE, "wb").write(data)
    print(f"OT id=0x{otid.hex()} | checksum=0x{chk:02X}")
    print(f"party @0x{PARTY:04X}: count={data[PARTY]} species={[hex(b) for b in data[PARTY+1:PARTY+5]]}")
    print(f"wrote {SAV}")
    print(f"wrote {BUNDLE}")

if __name__ == "__main__":
    main()
