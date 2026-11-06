# SPDX-FileCopyrightText: 2026 Andràs Marghescu
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install the DIN 1356 drawing style of this repository into Bonsai.

Bonsai keeps its drawing resources in two places:

- the data dir (add-on preferences, on Windows %APPDATA%\\bonsai\\bonsai\\data):
  assets/default.css and assets/patterns.svg are copied into a project when a
  drawing is generated and the project has no such file yet;
  templates/titleblocks/*.svg are offered as title blocks for new sheets.
- the project: drawings/assets/default.css and patterns.svg next to the
  drawings. Once they exist, Bonsai uses them and never looks at the data dir
  again for that project.

This script does not replace Bonsai's files. It appends style/din.css to a
default.css and adds the patterns of style/din-patterns.svg to a
patterns.svg; everything Bonsai has in those files stays. Running it again
replaces the earlier addition, so it can be run after every change to the
style.

    python scripts/install_style.py --data-dir DIR [--bonsai-assets DIR] [--overwrite]
    python scripts/install_style.py --project-assets DIR

--data-dir        Bonsai's data dir. If assets/default.css or patterns.svg are
                  missing there, Bonsai's own files are the base: from
                  --bonsai-assets, or found automatically when run inside
                  Blender. Title blocks are copied to templates/titleblocks/;
                  existing ones only with --overwrite.
--project-assets  A project's drawings/assets folder. Both files must exist
                  (generate one drawing in Bonsai first).

A file that already carries a DIN block of another origin (a rule
.din-1356-hinweise, for instance) is left alone with a message, so that no
second, conflicting block is appended. Standard library only; runs in
Blender (Text Editor, Run Script, with sys.argv set) and with a plain Python.
"""

import argparse
import glob
import os
import re
import shutil
import sys

CSS_START = ".din-1356-notes {"
PATTERN_MARK = "<!-- native-ifc-template: din-patterns.svg -->"
FOREIGN_CSS = re.compile(r"^\s*\.din-1356-(?!notes\b)[\w-]+\s*\{", re.M)


def repository_root():
    try:  # Blender: Text Editor, Run Script with a file from disk
        import bpy
        t = bpy.context.space_data.text
        if t and t.filepath:
            return os.path.dirname(os.path.dirname(bpy.path.abspath(t.filepath)))
    except Exception:
        pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text, newline):
    text = text.replace("\r\n", "\n")
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def merge_css(base, din):
    """Return base with din appended; an earlier din block is replaced."""
    text = base.replace("\r\n", "\n")
    i = text.find(CSS_START)
    if i >= 0:
        text = text[:i]
    elif FOREIGN_CSS.search(text):
        raise ValueError("contains a DIN block of another origin; not changed")
    return text.rstrip("\n") + "\n\n" + din.replace("\r\n", "\n").strip("\n") + "\n"


def pattern_blocks(din_svg):
    blocks = re.findall(r"<pattern\b.*?</pattern>", din_svg, re.S)
    ids = [re.search(r'\bid="([^"]+)"', b).group(1) for b in blocks]
    if not blocks or any(not i.startswith("din-") for i in ids):
        raise ValueError("din-patterns.svg: expected pattern elements with ids din-*")
    return blocks, ids


def merge_patterns(base, din_svg):
    """Return base with the din-* patterns inserted before the closing tag."""
    blocks, ids = pattern_blocks(din_svg)
    text = base.replace("\r\n", "\n")
    i = text.find(PATTERN_MARK)
    if i >= 0:  # our earlier addition: from the mark to the closing tag
        j = text.rfind("</defs>") if "</defs>" in text[i:] else text.rfind("</svg>")
        text = text[:i].rstrip("\n") + "\n" + text[j:]
    for pid in ids:  # same ids from elsewhere would shadow ours
        if re.search(r'<pattern\b[^>]*\bid="%s"' % re.escape(pid), text):
            raise ValueError("already has a pattern %s of another origin; not changed" % pid)
    close = "</defs>" if "</defs>" in text else "</svg>"
    j = text.rfind(close)
    if j < 0:
        raise ValueError("no closing %s" % close)
    addition = PATTERN_MARK + "\n" + "\n".join(blocks) + "\n"
    return text[:j].rstrip("\n") + "\n" + addition + text[j:]


def install_file(target, base_path, din_text, merge, messages):
    base = read(target) if os.path.exists(target) else read(base_path)
    new = merge(base, din_text)
    if os.path.exists(target) and read(target).replace("\r\n", "\n") == new:
        messages.append("unchanged: " + target)
        return
    os.makedirs(os.path.dirname(target), exist_ok=True)
    write(target, new, eol(base))
    messages.append("written: " + target)


def bonsai_assets_in_blender():
    try:
        import bonsai
        return os.path.join(os.path.dirname(bonsai.__file__), "bim", "data", "assets")
    except Exception:
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--data-dir")
    g.add_argument("--project-assets")
    p.add_argument("--bonsai-assets")
    p.add_argument("--overwrite", action="store_true", help="replace existing title blocks")
    a = p.parse_args(argv)

    style = os.path.join(repository_root(), "style")
    din_css = read(os.path.join(style, "din.css"))
    din_svg = read(os.path.join(style, "din-patterns.svg"))
    messages = []

    if a.project_assets:
        assets = a.project_assets
        missing = [f for f in ("default.css", "patterns.svg") if not os.path.exists(os.path.join(assets, f))]
        if missing:
            raise SystemExit("not found in %s: %s (generate a drawing first)" % (assets, ", ".join(missing)))
        base = None
    else:
        assets = os.path.join(a.data_dir, "assets")
        base = a.bonsai_assets or bonsai_assets_in_blender()

    for name, din, merge in (("default.css", din_css, merge_css), ("patterns.svg", din_svg, merge_patterns)):
        target = os.path.join(assets, name)
        if not os.path.exists(target) and not (base and os.path.exists(os.path.join(base, name))):
            raise SystemExit("%s is missing and Bonsai's own file was not found; use --bonsai-assets" % target)
        try:
            install_file(target, os.path.join(base or assets, name), din, merge, messages)
        except ValueError as e:
            messages.append("skipped: %s %s" % (target, e))

    if a.data_dir:
        source = os.path.join(style, "titleblocks")
        dest = os.path.join(a.data_dir, "templates", "titleblocks")
        os.makedirs(dest, exist_ok=True)
        for f in sorted(glob.glob(os.path.join(source, "DIN_*.svg"))):
            t = os.path.join(dest, os.path.basename(f))
            if os.path.exists(t) and not a.overwrite:
                messages.append("skipped (exists): " + t)
                continue
            shutil.copyfile(f, t)
            messages.append("written: " + t)

    for m in messages:
        print(m)
    return messages


if __name__ == "__main__":
    main(sys.argv[1:])
