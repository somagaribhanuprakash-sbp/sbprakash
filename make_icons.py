from PIL import Image, ImageDraw

BG_TOP = (14, 20, 27)
BG_BOT = (9, 13, 18)
CYAN = (73, 217, 199)
AMBER = (242, 166, 90)
LINE = (34, 48, 64)


def rounded_bg(size, radius_ratio=0.22):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size))
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        for x in range(size):
            grad.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    img.paste(grad, (0, 0), mask)
    return img


def draw_glyph(img, size, scale=1.0, offset=(0, 0)):
    d = ImageDraw.Draw(img)
    s = size
    ox, oy = offset

    # corner brackets (cyan) — top-left/top-right
    b = s * 0.15 * scale
    lw = max(2, int(s * 0.028 * scale))
    m = s * 0.14
    for cx, cy, dx, dy in [(m, m, 1, 1), (s - m, m, -1, 1)]:
        d.line([(cx + ox, cy + oy + b * dy * 0), (cx + ox, cy + oy)], fill=CYAN + (0,), width=1)  # no-op keep API happy
    # top-left bracket
    d.line([(m + ox, m + b + oy), (m + ox, m + oy), (m + b + ox, m + oy)], fill=CYAN, width=lw, joint="curve")
    # top-right bracket
    d.line([(s - m - b + ox, m + oy), (s - m + ox, m + oy), (s - m + ox, m + b + oy)], fill=CYAN, width=lw, joint="curve")
    # bottom-left bracket (amber)
    d.line([(m + ox, s - m - b + oy), (m + ox, s - m + oy), (m + b + ox, s - m + oy)], fill=AMBER, width=lw, joint="curve")
    # bottom-right bracket (amber)
    d.line([(s - m - b + ox, s - m + oy), (s - m + ox, s - m + oy), (s - m + ox, s - m - b + oy)], fill=AMBER, width=lw, joint="curve")

    # chevron ">" (cyan) — thick polygon
    cw = s * 0.26 * scale
    cx0 = s * 0.30 + ox
    cy0 = s * 0.34 + oy
    cy1 = s * 0.5 + oy
    cy2 = s * 0.66 + oy
    thick = s * 0.075 * scale
    pts = [
        (cx0, cy0 - thick / 1.3),
        (cx0 + cw, cy1 - thick / 1.3),
        (cx0 + cw, cy1 + thick / 1.3),
        (cx0, cy2 + thick / 1.3) if False else (cx0, cy0 + thick / 1.3),
    ]
    # simpler: draw as thick line path for a clean chevron
    d.line([(cx0, cy0), (cx0 + cw, cy1), (cx0, cy2)], fill=CYAN, width=int(s * 0.075 * scale), joint="curve")

    # underscore + dot (amber) — cursor
    uy = s * 0.655 + oy
    ux0 = s * 0.55 + ox
    ux1 = s * 0.78 + ox
    d.line([(ux0, uy), (ux1, uy)], fill=CYAN, width=int(s * 0.06 * scale))
    dotr = s * 0.035 * scale
    dcx, dcy = s * 0.475 + ox, uy
    d.ellipse([dcx - dotr, dcy - dotr, dcx + dotr, dcy + dotr], fill=AMBER)


def make_icon(size, path, maskable=False):
    radius_ratio = 0.0 if maskable else 0.22
    img = rounded_bg(size, radius_ratio)
    scale = 0.82 if maskable else 1.0
    draw_glyph(img, size, scale=scale)
    img.save(path)


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "frontend", "icons")
    os.makedirs(out, exist_ok=True)
    make_icon(512, os.path.join(out, "icon-512.png"))
    make_icon(512, os.path.join(out, "icon-512-maskable.png"), maskable=True)
    make_icon(192, os.path.join(out, "icon-192.png"))
    make_icon(32, os.path.join(out, "favicon-32.png"))
    print("done")
