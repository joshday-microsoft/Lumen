"""Panel-safe GIF encoder for the iDotMatrix wall.

Pillow's GIF writer delta-optimizes frames into sub-rectangles, which the
panel's firmware decoder mishandles (stalls mid-animation). This encoder is
deliberately dumb: every frame is a full 32x32 image at (0,0), one global
color table, no transparency, no interlace, disposal=1, own LZW.

save(frames, path, duration_ms, colors=48) -> byte size (round-trip verified)
"""

from pathlib import Path

from PIL import Image


def _lzw(indices: bytes, min_code_size: int) -> bytes:
    clear = 1 << min_code_size
    end = clear + 1
    out = bytearray()
    bitbuf = 0
    bitcnt = 0

    def emit(code, size):
        nonlocal bitbuf, bitcnt
        bitbuf |= code << bitcnt
        bitcnt += size
        while bitcnt >= 8:
            out.append(bitbuf & 0xFF)
            bitbuf >>= 8
            bitcnt -= 8

    # constant code width: reset the table via CLEAR before the code space
    # fills, so neither side ever changes width (sidesteps the early/late
    # width-bump ambiguity entirely — and it's the simplest stream for the
    # panel's firmware decoder)
    code_size = min_code_size + 1
    table = {bytes([i]): i for i in range(clear)}
    next_code = end + 1
    emit(clear, code_size)
    w = b""
    for b in indices:
        wc = w + bytes([b])
        if wc in table:
            w = wc
            continue
        emit(table[w], code_size)
        table[wc] = next_code
        next_code += 1
        w = bytes([b])
        if next_code >= (1 << code_size) - 2:
            emit(clear, code_size)
            table = {bytes([i]): i for i in range(clear)}
            next_code = end + 1
    if w:
        emit(table[w], code_size)
    emit(end, code_size)
    if bitcnt:
        out.append(bitbuf & 0xFF)
    return bytes(out)


def _blocks(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)
    return bytes(out)


def save(frames, path, duration_ms=140, colors=48):
    """Encode RGB frames as a maximally-conservative animated GIF."""
    w, h = frames[0].size
    # one shared palette built from every frame's content
    montage = Image.new("RGB", (w * len(frames), h))
    for i, f in enumerate(frames):
        montage.paste(f.convert("RGB"), (i * w, 0))
    pal_img = montage.quantize(colors=colors, dither=Image.Dither.NONE)
    quantized = [f.convert("RGB").quantize(palette=pal_img, dither=Image.Dither.NONE) for f in frames]

    bits = 1
    while (1 << bits) < colors:
        bits += 1
    table_size = 1 << bits
    # Pillow trims getpalette() to the USED entries — pad to the full
    # power-of-two table the header declares, or every offset after it shifts
    pal = (pal_img.getpalette() or [])[: table_size * 3]
    pal += [0] * (table_size * 3 - len(pal))
    min_code_size = max(2, bits)

    buf = bytearray()
    buf += b"GIF89a"
    buf += w.to_bytes(2, "little") + h.to_bytes(2, "little")
    buf.append(0xF0 | (bits - 1))          # GCT present, 8-bit color res
    buf += b"\x00\x00"                      # bg index, aspect
    buf += bytes(pal)
    buf += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"   # loop forever
    delay = max(2, round(duration_ms / 10))
    for q in quantized:
        buf += b"\x21\xf9\x04"
        buf.append(0x04)                    # disposal=1 (keep), no transparency
        buf += delay.to_bytes(2, "little")
        buf += b"\x00\x00"                  # transparent idx (unused), terminator
        buf += b"\x2c" + b"\x00\x00\x00\x00" + w.to_bytes(2, "little") + h.to_bytes(2, "little")
        buf.append(0x00)                    # no local table, no interlace
        buf.append(min_code_size)
        buf += _blocks(_lzw(q.tobytes(), min_code_size))
    buf += b"\x3b"

    Path(path).write_bytes(buf)

    # round-trip: PIL must decode every frame pixel-identical to the source
    check = Image.open(path)
    i = 0
    try:
        while True:
            got = check.convert("RGB")
            want = quantized[i].convert("RGB")
            if list(got.getdata()) != list(want.getdata()):
                raise AssertionError(f"round-trip mismatch on frame {i}")
            i += 1
            check.seek(i)
    except EOFError:
        pass
    if i != len(quantized):
        raise AssertionError(f"round-trip frame count {i} != {len(quantized)}")
    return len(buf)
