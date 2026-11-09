# native-ifc-template

**A project template that lives in native IFC, and a way to derive drawings from it.**

*Modelllogik is German for model logic.*

> **Status: v0.3.0.** The material categories are reworked and described in German and
> English in [`docs/material-categories.md`](docs/material-categories.md): a new category
> for membranes and foils, soil types below `Erdreich`, and `Kies` renamed to `Schuettung`
> ([upgrading](#upgrading-from-v020)). v0.2.0 added the drawing style after DIN 1356-1,
> v0.1.0 the IFC project template. A neutral example model and an IDS follow; the
> post-processing of drawings is developed in
> [bonsai-btk](https://github.com/modelllogik/bonsai-btk).

## Why

Most BIM workflows still author in a proprietary format and export to IFC at the end.
Every round trip between the authoring format and IFC loses or rewrites information.

This project tries the other way round: **IFC is the authoring format.**

1. A **project template in IFC**, built reproducibly by a script.
2. A person **models natively in IFC**, with [Bonsai](https://bonsaibim.org) on top of
   [IfcOpenShell](https://ifcopenshell.org).
3. **Drawings are derived from the model** in a post-processing step that follows the
   conventions of the German drawing standard DIN 1356 (line weights, hatching,
   dimensioning, title blocks).

The primary audience is the openBIM community; the second is trainers and teachers who
want to use native IFC in vocational training.

## What will be in here

| Folder | Content | Licence |
|---|---|---|
| `template/` | The IFC project template and the script that builds it | code GPL-3.0-or-later, template CC BY 4.0 |
| `style/` | Drawing style: CSS, hatch patterns, title blocks A4 to A0 | CC BY 4.0 |
| `examples/` | A neutral example model and the drawing set derived from it | CC BY 4.0 |
| `ids/` | Information Delivery Specification (IDS) to check models against the template | CC BY 4.0 |
| `scripts/` | Helpers for building, checking and deriving drawings | GPL-3.0-or-later |
| `docs/` | Documentation; `docs/de/` is a German guide for trainers | CC BY 4.0 |

## Quick start

The template is ready to use: [`template/native_template.ifc`](template/native_template.ifc).

1. Copy it into Bonsai's project template folder, `<data dir>/templates/projects/`.
   The data dir is set in Bonsai's add-on preferences; on Windows it defaults to
   `%APPDATA%\bonsai\bonsai\data`.
2. Restart Blender, then *New Project* in Bonsai and choose the template.

**Note for Bonsai 0.9.1:** after *New Project* with this template, save the project and open it again. Until then the style editor fails and door or window types cannot be placed ([#10134](https://github.com/IfcOpenShell/IfcOpenShell/issues/10134)).

What is inside: storeys KG, EG, OG and DG with their levels, 47 materials in 28
categories ([list](docs/material-categories.md)) with colours, and 234 types (layered walls, slabs and coverings; doors and
windows in timber and PVC; timber and steel profiles; level annotations), all in an
`IfcProjectLibrary`. The template has no georeference on purpose; see the docstring of
the build script.

Names of types and materials are German: the template follows German building
practice and the drawing conventions of DIN 1356.

### Building the template yourself

```bash
python template/build_template.py native_template.ifc
```

The script needs IfcOpenShell only, not Blender. The same script gives the same file
byte for byte.

## Drawing style (DIN 1356-1, scale 1:50)

Bonsai draws from the model as SVG and styles the result with CSS. The style in
`style/` turns that into a German construction drawing:

- [`style/din.css`](style/din.css) – line weights and hatching **by material
  category** (`IfcMaterial.Category`), layer by layer: structural layers 0.50 all
  round, other layers, windows and doors 0.25, hatching 0.10; Arial with 3.5 mm cap
  height. Every category used in the template has a rule.
- [`style/din-patterns.svg`](style/din-patterns.svg) – twelve hatch patterns
  `din-*` for masonry, concrete, reinforced concrete, insulation, soil, gravel and
  more.
- [`style/titleblocks/`](style/titleblocks/) – sheet frames DIN A4 to A0 after
  DIN 824 form A with fold marks and a title block whose fields Bonsai fills from
  the sheet. The title block is a sample with placeholders; edit
  `style/titleblocks/parts/title_block.svg` and run
  `python scripts/build_titleblocks.py --overwrite`.

The style is an **addition** to Bonsai's own `default.css` and `patterns.svg`, not a
replacement. `scripts/install_style.py` merges it in; running it again replaces the
earlier addition and changes nothing else.

```bash
# into Bonsai's data dir: used by every project that has no drawing style yet
python scripts/install_style.py --data-dir "%APPDATA%\bonsai\bonsai\data" --bonsai-assets <bonsai>/bim/data/assets

# into one project that already has drawings
python scripts/install_style.py --project-assets <project>/drawings/assets
```

Inside Blender (Text Editor, Run Script) `--bonsai-assets` is found by itself. Then
regenerate the drawings in Bonsai.

**A new material** needs no change to the style: give it one of the categories of
section 4 in `din.css` (spelt as there, e.g. `Daemmung`, because Bonsai keeps only
a–z, A–Z and 0–9 in class names); the codes and what belongs to them are listed in
[`docs/material-categories.md`](docs/material-categories.md). **A new category** is one line in section 4,
plus a pattern in `din-patterns.svg` if it needs one. The German guide in `docs/de/`
walks through both.

**Not yet in this release:** hatches as real line paths for print (pattern fills can
break up when a PDF is rasterised), the timber cross and the waterproofing band,
German dimension figures and dimension markers. These need a post-processing step of
the drawing SVG; it is developed in [bonsai-btk](https://github.com/modelllogik/bonsai-btk)
(see its roadmap). Line weights and pattern spacing are
checked on screen and in Inkscape; calibrate them on a print before relying on them.

### Upgrading from v0.2.0

- Copy the new `template/native_template.ifc` and run `scripts/install_style.py` again
  (also with `--project-assets` for projects that already have drawings).
- **`Kies` is now `Schuettung`.** In your own projects, materials with category `Kies`
  that mean placed gravel (drainage layer, gravel bed) are changed to `Schuettung` in
  Bonsai; `Kies` now stands for gravel as a soil type.
- Dampfbremse, Unterdeckbahn and PE-Folie moved from `Abdichtung` to `Bahnen`; they are
  drawn as before.
- In the template, the GlobalIds of the material assignments (`IfcRelAssociatesMaterial`)
  changed because new materials were added. GlobalIds of types are unchanged.

## Requirements

Tested with:

- Blender 5.2.0 LTS
- Bonsai 0.9.1 (unstable channel)
- IfcOpenShell 0.9.1a261106

## Licences

This repository follows the [REUSE](https://reuse.software) convention.

- **Code** (Python scripts and add-on code): **GPL-3.0-or-later**, in line with Bonsai.
  See [`LICENSE`](LICENSE).
- **Templates, drawing style, examples, IDS and documentation**: **CC BY 4.0**.
  See [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt).

Which licence applies to which path is recorded in [`REUSE.toml`](REUSE.toml).
Bonsai's own `default.css` and `patterns.svg` (GPL-3.0-or-later) are not part of this
repository; `install_style.py` adds our style to the copies Bonsai already has.

Standards such as DIN 1356 are referred to by content; their text is not reproduced here.

## Contributing

Observations, questions and pull requests are welcome. Please read
[`CONTRIBUTING.md`](CONTRIBUTING.md) first.

## How this is made

The build script and this repository are developed with the help of an AI assistant
(Claude, by Anthropic). The maintainer decides what goes in, reviews every change and
tests it in Bonsai; the build is reproducible and checked against the previous version.

## Related work upstream

Findings that belong to Bonsai or IfcOpenShell are reported there, not worked around silently here:

- [#10133](https://github.com/IfcOpenShell/IfcOpenShell/issues/10133) – GPU wireframe snap: the batch cache is stored and looked up under different keys.
- [#10134](https://github.com/IfcOpenShell/IfcOpenShell/issues/10134) – *New Project* with a template that has a site: merged surface styles and types get no Blender material or object.
