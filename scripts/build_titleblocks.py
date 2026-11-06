# SPDX-FileCopyrightText: 2026 Andràs Marghescu
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build DIN A4 to A0 sheet frames with title block for Bonsai sheets.

Reads the title block style/titleblocks/parts/title_block.svg and writes one
frame per format to style/titleblocks/ (DIN_A4_hoch.svg ... DIN_A0_quer.svg;
hoch = portrait, quer = landscape). Standard library only; runs in Blender
(Text Editor, Run Script) and with a plain Python:

    python scripts/build_titleblocks.py [source_dir] [target_dir] [--overwrite]

Frame after DIN 824 form A: binding margin left 20 mm, otherwise 5 mm, frame
line 0.5; trim line 0.18 at the sheet edge (moved inwards by half its width).
Fold marks: every sheet larger than A4 gets at most two folds - 190 mm from
the right edge (vertical, if wider than 210) and 297 mm from the bottom edge
(horizontal, if higher than 297). Marks are 5 mm long at both sheet edges.
The title block sits bottom right, flush with the frame line. If less than
20 mm remain to its left (A4 portrait), the title block is stretched to the
left frame: the outer rectangle (x 0, full width) and all horizontal lines of
full width are pulled to the left; texts and groups left of the first
vertical line move with them.

Existing files are only replaced with --overwrite.
"""

import os
import re
import sys

FORMATS = [  # name, width, height (mm)
    ("DIN_A4_hoch", 210, 297),
    ("DIN_A4_quer", 297, 210),
    ("DIN_A3_hoch", 297, 420),
    ("DIN_A3_quer", 420, 297),
    ("DIN_A2_hoch", 420, 594),
    ("DIN_A2_quer", 594, 420),
    ("DIN_A1_hoch", 594, 841),
    ("DIN_A1_quer", 841, 594),
    ("DIN_A0_hoch", 841, 1189),
    ("DIN_A0_quer", 1189, 841),
]

BINDING_MARGIN = 20.0
MARGIN = 5.0
FOLD_WIDTH = 190.0    # from the right
FOLD_HEIGHT = 297.0   # from the bottom
MARK = 5.0
MIN_GAP = 20.0        # below this the title block is stretched to the left frame

FRAME_STYLE = """      .d50 { stroke:#000000; stroke-width:0.5; stroke-linejoin:miter; }
      .d18 { stroke:#000000; stroke-width:0.18; fill:none; }
      .d25 { stroke:#000000; stroke-width:0.25; stroke-linecap:butt; fill:none; }"""


def num(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def mm(value, what):
    m = re.fullmatch(r"\s*([0-9.]+)\s*(mm)?\s*", value or "")
    if not m:
        raise ValueError("title block: %s must be given in mm, found %r" % (what, value))
    return float(m.group(1))


def read_title_block(path):
    text = open(path, encoding="utf-8").read()
    root = re.search(r"<svg\b[^>]*>", text, re.S)
    if not root:
        raise ValueError("title block: no svg element")
    attr = dict(re.findall(r'([\w:-]+)="([^"]*)"', root.group(0)))
    w = mm(attr.get("width"), "width")
    h = mm(attr.get("height"), "height")
    style = re.search(r"<style[^>]*>(.*?)</style>", text, re.S)
    end_defs = text.find("</defs>")
    end_svg = text.rfind("</svg>")
    if end_defs < 0 or end_svg < 0:
        raise ValueError("title block: expected defs with style and a closing svg")
    content = text[end_defs + len("</defs>"):end_svg].strip("\n")
    style_text = style.group(1).strip("\n") if style else ""
    for c in re.findall(r"<!--(.*?)-->", text, re.S):
        if "{{" in c:
            raise ValueError("title block: double curly braces in a comment")
    return w, h, style_text.rstrip(), content


def stretch(content, bw, d):
    """Pull the outer rectangle and horizontal lines of full width left by d."""
    b = re.escape(num(bw))

    def rectangle(m):
        return m.group(0).replace('x="0"', 'x="%s"' % num(-d), 1).replace(
            'width="%s"' % num(bw), 'width="%s"' % num(bw + d), 1)

    content = re.sub(r'<rect\b(?=[^>]*\bx="0")(?=[^>]*\bwidth="%s")[^>]*>' % b, rectangle, content)

    def line(m):
        return m.group(0).replace('x1="0"', 'x1="%s"' % num(-d), 1)

    content = re.sub(r'<line\b(?=[^>]*\bx1="0")(?=[^>]*\bx2="%s")(?=[^>]*\by1="([^"]*)")(?=[^>]*\by2="\1")[^>]*>' % b,
                     line, content)

    # move the left column with it: everything left of the first vertical line
    vertical = [float(m.group(1)) for m in re.finditer(
        r'<line\b(?=[^>]*\bx1="([^"]*)")(?=[^>]*\bx2="\1")[^>]*>', content) if float(m.group(1)) > 0]
    limit = min(vertical) if vertical else bw

    def text(m):
        x = float(m.group(2))
        return m.group(1) + (num(x - d) if x < limit else m.group(2)) + '"'

    content = re.sub(r'(<text\b[^>]*?\bx=")([-0-9.]+)"', text, content)

    def group(m):
        x = float(m.group(2))
        return m.group(1) + (num(x - d) if x < limit else m.group(2)) + m.group(3)

    content = re.sub(r'(<g\b[^>]*?\btransform="translate\()([-0-9.]+)([ ,])', group, content)
    return content


def frame(name, W, H, bw, bh, style, content):
    is_a4 = (W, H) in ((210, 297), (297, 210))
    fx = W - FOLD_WIDTH if (not is_a4 and W > 210) else None
    fy = H - FOLD_HEIGHT if (not is_a4 and H > 297) else None
    rx, ry = BINDING_MARGIN, MARGIN
    rw, rh = W - BINDING_MARGIN - MARGIN, H - 2 * MARGIN
    kx, ky = W - MARGIN - bw, H - MARGIN - bh
    gap = kx - BINDING_MARGIN
    if 0 < gap < MIN_GAP:
        content = stretch(content, bw, gap)
    title = name.replace("_", " ")
    folds = []
    if fx is not None:
        folds.append('    <line x1="%s" y1="0" x2="%s" y2="%s" class="d25"/>' % (num(fx), num(fx), num(MARK)))
        folds.append('    <line x1="%s" y1="%s" x2="%s" y2="%s" class="d25"/>' % (num(fx), num(H - MARK), num(fx), num(H)))
    if fy is not None:
        folds.append('    <line x1="0" y1="%s" x2="%s" y2="%s" class="d25"/>' % (num(fy), num(MARK), num(fy)))
        folds.append('    <line x1="%s" y1="%s" x2="%s" y2="%s" class="d25"/>' % (num(W - MARK), num(fy), num(W), num(fy)))
    fold_text = ("from the right %s" % num(FOLD_WIDTH) if fx is not None else "") + \
                (" and " if fx is not None and fy is not None else "") + \
                ("from the bottom %s" % num(FOLD_HEIGHT) if fy is not None else "")
    comment = """<!--
  Sheet frame %s with title block for Bonsai sheets
  native-ifc-template - CC BY 4.0
  GENERATED by scripts/build_titleblocks.py - do not edit by hand.
  To change the title block, edit style/titleblocks/parts/title_block.svg
  and run the script again.

  Sheet %s x %s mm. Frame after DIN 824 form A: binding margin left 20,
  otherwise 5, line 0.5. Trim line 0.18 at the sheet edge, moved inwards by
  half its width.
  Fold marks: %s.
  Title block %s x %s bottom right (x %s, y %s)%s.
  Bonsai reads the file from layouts/titleblocks/ (file name without .svg is
  the name in the selection) and fills the fields from the sheet's
  IfcDocumentInformation.
-->
""" % (title, num(W), num(H), fold_text or "none (A4 filing format)", num(bw), num(bh), num(kx), num(ky),
       ", stretched to the left frame" if 0 < gap < MIN_GAP else "")
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n',
        comment,
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"\n',
        '     width="%smm" height="%smm" viewBox="0 0 %s %s" version="1.1" id="root">\n' % (num(W), num(H), num(W), num(H)),
        '  <title>%s</title>\n' % title,
        '  <defs>\n    <style type="text/css">\n%s\n%s\n    </style>\n  </defs>\n' % (FRAME_STYLE, style),
        '  <g id="sheet">\n',
        '    <rect x="0" y="0" width="%s" height="%s" fill="#ffffff" stroke="none"/>\n' % (num(W), num(H)),
        '    <rect x="0.09" y="0.09" width="%s" height="%s" class="d18" fill="none"/>\n' % (num(W - 0.18), num(H - 0.18)),
        '    <rect x="%s" y="%s" width="%s" height="%s" class="d50" fill="none"/>\n' % (num(rx), num(ry), num(rw), num(rh)),
        '  </g>\n',
        '  <g id="fold-marks">\n' + ("\n".join(folds) + "\n" if folds else "") + '  </g>\n',
        '  <g id="title-block" transform="translate(%s,%s)">\n%s\n  </g>\n' % (num(kx), num(ky), content),
        '</svg>\n',
    ]
    return "".join(parts)


def repository_root():
    try:  # Blender: Text Editor, Run Script with a file from disk
        import bpy
        t = bpy.context.space_data.text
        if t and t.filepath:
            return os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath)))
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(source=None, target=None, overwrite=False):
    root = repository_root()
    target = target or os.path.join(root, "style", "titleblocks")
    source = source or os.path.join(target, "parts")
    bw, bh, style, content = read_title_block(os.path.join(source, "title_block.svg"))
    messages = []
    if bw > 185 or bh > 287:
        raise ValueError("title block %s x %s mm is too large (at most 185 x 287)" % (num(bw), num(bh)))
    if bw > FOLD_WIDTH - MARGIN:
        messages.append("note: title block is wider than the cover panel (185 mm)")
    for name, W, H in FORMATS:
        path = os.path.join(target, name + ".svg")
        if os.path.exists(path) and not overwrite:
            messages.append("skipped (exists): " + name + ".svg")
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(frame(name, W, H, bw, bh, style, content))
        messages.append("written: " + name + ".svg")
    for m in messages:
        print(m)
    return messages


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--overwrite"]
    main(*args[:2], overwrite="--overwrite" in sys.argv[1:])
