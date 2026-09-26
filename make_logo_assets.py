# -*- coding: utf-8 -*-
"""Derive site logo assets from the vector master (trollservice-svart.eps).

Outputs (static/img/):
  logo-full.png        emblem + wordmark, black, transparent bg, width 640
  logo-mark.png        circle emblem only, black, transparent bg, <=160
  logo-mark-cream.png  circle emblem only, #FFF8CF on transparent, <=160
  favicon.png          circle emblem, black, 64x64, transparent bg

Pipeline:
  eps --ghostscript(r600, EPSCrop)--> logo-master.png (cached, project root)
  master alpha --> connected-component split (emblem vs arced wordmark)
  --> resized outputs.  The mark/favicon are NOT alpha-posterised (that ate
  the face/lawnmower detail); the hero full logo keeps 8 levels for size.
  Falls back to trollservice-svart.jpg if Ghostscript/EPS is unavailable.

Run:  .venv\\Scripts\\python.exe make_logo_assets.py
"""

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops

BASE = Path(__file__).resolve().parent
SRC_EPS = BASE / "trollservice-svart.eps"
SRC_JPG = BASE / "trollservice-svart.jpg"
MASTER = BASE / "logo-master.png"
OUT = BASE / "static" / "img"
CREAM = (255, 248, 207)

FULL_W = 640
MARK = 160
FAVICON = 64
GRID_W = 1024  # downscale width for component labelling (large master)
GS_DPI = 600


def find_gs():
    for name in ("gswin64c", "gswin64c.exe", "gswin32c", "gswin32c.exe", "gs"):
        p = shutil.which(name)
        if p:
            return p
    shim = Path.home() / "scoop" / "shims" / "gswin64c.exe"
    if shim.exists():
        return str(shim)
    return None


def render_master():
    """Rasterize the EPS with Ghostscript (cached; re-render if EPS newer)."""
    if not SRC_EPS.exists():
        return None
    if MASTER.exists() and MASTER.stat().st_mtime >= SRC_EPS.stat().st_mtime:
        return MASTER
    gs = find_gs()
    if not gs:
        print("  ghostscript not found -> falling back to JPG source")
        return None
    cmd = [
        gs, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
        "-sDEVICE=pngalpha", f"-r{GS_DPI}", f"-o{MASTER}", str(SRC_EPS),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  rendered master from eps: {MASTER.name}")
    return MASTER


def load_alpha():
    """Alpha with white/art=opaque-in-art semantics from the best source."""
    master = render_master()
    if master:
        img = Image.open(master).convert("RGBA")
        alpha = img.getchannel("A")
        if alpha.getbbox() and sum(alpha.histogram()[8:]) > 0.01 * alpha.size[0] * alpha.size[1]:
            print(f"  source: vector master {img.size[0]}x{img.size[1]}")
            return alpha
        print("  master alpha unusable -> falling back to JPG source")
    img = Image.open(SRC_JPG).convert("L")
    print(f"  source: jpg {img.size[0]}x{img.size[1]}")
    return img.point(lambda v: 255 - v)  # white -> transparent, black -> opaque


def components(alpha):
    """Connected components of the ink on a downscaled binary copy.

    Returns (find, grid, ranked_roots, (sw, sh)); find(id) -> root label.
    """
    w, h = alpha.size
    sw = GRID_W
    sh = max(1, round(h * sw / w))
    small = alpha.resize((sw, sh), Image.Resampling.LANCZOS, reducing_gap=2.0)
    px = small.load()
    grid = [[1 if px[x, y] > 64 else 0 for x in range(sw)] for y in range(sh)]

    parent = list(range(sw * sh))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for y in range(sh):
        for x in range(sw):
            if not grid[y][x]:
                continue
            i = y * sw + x
            if x + 1 < sw and grid[y][x + 1]:
                union(i, i + 1)
            if y + 1 < sh and grid[y + 1][x]:
                union(i, i + sw)

    boxes = {}
    for y in range(sh):
        for x in range(sw):
            if grid[y][x]:
                r = find(y * sw + x)
                b = boxes.get(r)
                if b is None:
                    boxes[r] = [x, y, x, y]
                else:
                    b[0] = min(b[0], x)
                    b[1] = min(b[1], y)
                    b[2] = max(b[2], x)
                    b[3] = max(b[3], y)

    ranked = sorted(
        boxes,
        key=lambda r: (boxes[r][2] - boxes[r][0]) * (boxes[r][3] - boxes[r][1]),
        reverse=True,
    )
    print("  top components (grid bbox):")
    for r in ranked[:6]:
        print(f"    root={r} {boxes[r]}")
    return find, grid, ranked, boxes, (sw, sh)


def emblem_alpha(alpha):
    """Full-res alpha cropped to the emblem, keeping ALL interior ink.

    The emblem's face features (eyes, nose, mouth) and mower details are
    separate island components from the ring/body outline, so we keep every
    component whose bbox sits inside the emblem's bbox and drop only what
    falls outside — the arced wordmark letters.
    """
    find, grid, ranked, boxes, (sw, sh) = components(alpha)
    root = ranked[0]
    rx0, ry0, rx1, ry1 = boxes[root]
    tol = 1
    keep = {
        r for r, b in boxes.items()
        if b[0] >= rx0 - tol and b[1] >= ry0 - tol
        and b[2] <= rx1 + tol and b[3] <= ry1 + tol
    }
    dropped = [boxes[r] for r in boxes if r not in keep]
    print(f"  keeping {len(keep)} component(s) inside emblem bbox, "
          f"dropped {len(dropped)} (wordmark): {dropped[:6]}")
    w, h = alpha.size

    keep_img = Image.new("L", (sw, sh), 0)
    kp = keep_img.load()
    for y in range(sh):
        for x in range(sw):
            if grid[y][x] and find(y * sw + x) in keep:
                kp[x, y] = 255
    keep_img = keep_img.resize((w, h), Image.Resampling.LANCZOS, reducing_gap=2.0)
    return ImageChops.multiply(alpha, keep_img)


def tinted(alpha, rgb, size=None):
    """Solid-colour RGBA with the given alpha mask, optionally resized."""
    if size:
        alpha = alpha.resize(size, Image.Resampling.LANCZOS, reducing_gap=2.0)
    out = Image.new("RGBA", alpha.size, rgb + (0,))
    out.putalpha(alpha)
    return out


def quantize_alpha(img, levels):
    """Reduce alpha to `levels` steps for smaller PNGs (None = keep crisp)."""
    if not levels:
        return img
    table = [min(255, (i * levels // 256) * 255 // (levels - 1)) for i in range(256)]
    *bands, a = img.split()
    return Image.merge(img.mode, (*bands, a.point(table)))


def save(img, name, levels=None):
    img = quantize_alpha(img, levels)
    path = OUT / name
    img.save(path, optimize=True, compress_level=9)
    print(f"  {name}: {img.size[0]}x{img.size[1]}  {path.stat().st_size // 1024} KB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    alpha = load_alpha()
    w, h = alpha.size

    # Full logo (emblem + wordmark): posterised to 8 alpha levels for size
    full = tinted(alpha, (0, 0, 0), size=(FULL_W, round(h * FULL_W / w)))
    save(full.convert("LA"), "logo-full.png", levels=8)

    # Emblem only (wordmark removed via component mask), trimmed, crisp
    em = emblem_alpha(alpha)
    bbox = em.getbbox()
    if bbox:
        em = em.crop(bbox)
    ew, eh = em.size

    def fit(box):
        scale = box / max(ew, eh)
        return (max(1, round(ew * scale)), max(1, round(eh * scale)))

    save(tinted(em, (0, 0, 0), size=fit(MARK)).convert("LA"), "logo-mark.png")
    save(tinted(em, CREAM, size=fit(MARK)), "logo-mark-cream.png")
    save(tinted(em, (0, 0, 0), size=fit(FAVICON)).convert("LA"), "favicon.png")
    print("done")


if __name__ == "__main__":
    main()
