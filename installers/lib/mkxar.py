#!/usr/bin/env python3
"""Empaqueta un directorio como archivo xar — el contenedor de los .pkg
planos de macOS — sin necesitar el binario `xar` (no existe empaquetado
para Linux moderno). Implementa solo lo que installer(8)/pkgutil leen:
TOC XML comprimido con zlib, checksums SHA-1 y datos con encoding
"application/x-gzip" (que en xar significa deflate zlib, no gzip real).
Ojo con el TOC: <length> es el tamaño comprimido en el heap y <size>
el tamaño extraído — al revés de lo que sugieren los nombres.

Uso: mkxar.py <directorio-origen> <salida.pkg>
"""
import hashlib
import os
import struct
import sys
import time
import zlib
from xml.sax.saxutils import escape

CKSUM_SIZE = 20  # SHA-1 del TOC comprimido, primer objeto del heap


def _file_entry(fid, name, full, heap):
    """Nodo <file> de un archivo regular; agrega sus datos zlib al heap."""
    with open(full, "rb") as f:
        data = f.read()
    comp = zlib.compress(data, 9)
    offset = len(heap)
    heap.extend(comp)
    mode = "0755" if os.access(full, os.X_OK) else "0644"
    return (
        f'<file id="{fid}"><name>{escape(name)}</name><type>file</type>'
        f"<mode>{mode}</mode><uid>0</uid><gid>0</gid>"
        f"<user>root</user><group>wheel</group>"
        f"<data><offset>{offset}</offset><size>{len(data)}</size>"
        f"<length>{len(comp)}</length>"
        f'<encoding style="application/x-gzip"/>'
        f'<extracted-checksum style="sha1">{hashlib.sha1(data).hexdigest()}</extracted-checksum>'
        f'<archived-checksum style="sha1">{hashlib.sha1(comp).hexdigest()}</archived-checksum>'
        f"</data></file>"
    )


def _walk(dir_path, heap, counter):
    parts = []
    for name in sorted(os.listdir(dir_path)):
        full = os.path.join(dir_path, name)
        counter[0] += 1
        fid = counter[0]
        if os.path.isdir(full):
            children = _walk(full, heap, counter)
            parts.append(
                f'<file id="{fid}"><name>{escape(name)}</name><type>directory</type>'
                f"<mode>0755</mode><uid>0</uid><gid>0</gid>"
                f"<user>root</user><group>wheel</group>{children}</file>"
            )
        else:
            parts.append(_file_entry(fid, name, full, heap))
    return "".join(parts)


def build(src_dir, out_path):
    heap = bytearray(CKSUM_SIZE)  # hueco para el SHA-1 del TOC, se rellena al final
    entries = _walk(src_dir, heap, [0])
    toc = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?><xar><toc>"
        f"<creation-time>{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}</creation-time>"
        f'<checksum style="sha1"><offset>0</offset><size>{CKSUM_SIZE}</size></checksum>'
        f"{entries}</toc></xar>"
    ).encode()
    comp_toc = zlib.compress(toc, 9)
    heap[:CKSUM_SIZE] = hashlib.sha1(comp_toc).digest()
    header = struct.pack(">4sHHQQL", b"xar!", 28, 1, len(comp_toc), len(toc), 1)
    with open(out_path, "wb") as f:
        f.write(header)
        f.write(comp_toc)
        f.write(heap)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
