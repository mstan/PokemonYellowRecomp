#!/usr/bin/env python3
"""
Generate a BPS patch (stock Yellow -> extended Yellow) and verify it applies
back to the exact extended ROM. BPS embeds source/target/patch CRC32s so the
applier (here + the runtime launcher) can validate the user's ROM.

Simple correct encoder: SourceRead for unchanged runs, TargetRead for changed
runs (source and target are the same size). Not size-optimal, but tiny since
the two ROMs differ in only a few regions.
"""
import sys, zlib

STOCK = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\roms\Pokemon - Yellow Version (UE) [C][!].gbc"
EXT   = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\pokeyellow\pokeyellow.gbc"
OUT   = r"F:\Projects\gbcrecomp\PokemonYellowDecomp\dist\Pokemon_Yellow_Extended.bps"

def enc_varint(n):
    out = bytearray()
    while True:
        x = n & 0x7f
        n >>= 7
        if n == 0:
            out.append(0x80 | x); break
        out.append(x)
        n -= 1
    return bytes(out)

def dec_varint(buf, pos):
    data = 0; shift = 1
    while True:
        x = buf[pos]; pos += 1
        data += (x & 0x7f) * shift
        if x & 0x80: break
        shift <<= 7
        data += shift
    return data, pos

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = 0, 1, 2, 3

def make_bps(src, tgt):
    assert len(src) == len(tgt), "this encoder assumes equal sizes"
    n = len(tgt)
    body = bytearray()
    body += b"BPS1"
    body += enc_varint(len(src))
    body += enc_varint(len(tgt))
    body += enc_varint(0)  # no metadata

    def emit(cmd, length):
        body.extend(enc_varint(((length - 1) << 2) | cmd))

    i = 0
    while i < n:
        if src[i] == tgt[i]:
            j = i
            while j < n and src[j] == tgt[j]:
                j += 1
            emit(SOURCE_READ, j - i)   # copy from source at current outputOffset
            i = j
        else:
            j = i
            while j < n and src[j] != tgt[j]:
                j += 1
            emit(TARGET_READ, j - i)
            body.extend(tgt[i:j])      # literal target bytes
            i = j

    body += zlib.crc32(src).to_bytes(4, "little")
    body += zlib.crc32(tgt).to_bytes(4, "little")
    patch_crc = zlib.crc32(bytes(body)).to_bytes(4, "little")
    body += patch_crc
    return bytes(body)

def apply_bps(patch, src):
    assert patch[:4] == b"BPS1", "bad BPS magic"
    pos = 4
    src_size, pos = dec_varint(patch, pos)
    tgt_size, pos = dec_varint(patch, pos)
    meta_size, pos = dec_varint(patch, pos)
    pos += meta_size
    assert len(src) == src_size, f"source size mismatch ({len(src)} != {src_size})"
    if zlib.crc32(src) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("source CRC mismatch (wrong ROM)")
    out = bytearray(tgt_size)
    op = 0
    end = len(patch) - 12
    while pos < end:
        v, pos = dec_varint(patch, pos)
        cmd, length = v & 3, (v >> 2) + 1
        if cmd == SOURCE_READ:
            out[op:op+length] = src[op:op+length]; op += length
        elif cmd == TARGET_READ:
            out[op:op+length] = patch[pos:pos+length]; pos += length; op += length
        else:
            raise NotImplementedError(f"cmd {cmd} not produced by this encoder")
    if zlib.crc32(bytes(out)) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("target CRC mismatch after apply")
    return bytes(out)

def main():
    import os, hashlib
    src = open(STOCK, "rb").read()
    tgt = open(EXT, "rb").read()
    patch = make_bps(src, tgt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(patch)

    # round-trip verify
    result = apply_bps(patch, src)
    ok = (result == tgt)
    print(f"BPS size: {len(patch)} bytes  ({len(patch)/1024:.1f} KB)")
    print(f"source CRC32: {zlib.crc32(src):08x}")
    print(f"target CRC32: {zlib.crc32(tgt):08x}")
    print(f"round-trip apply -> extended: {'OK' if ok else 'FAIL'}")
    print(f"result sha256: {hashlib.sha256(result).hexdigest()}")
    print(f"wrote {OUT}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
