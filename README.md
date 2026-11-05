# native-ifc-template

**A project template that lives in native IFC, and a way to derive drawings from it.**

*Modelllogik is German for model logic.*

> **Status: v0.1.0.** This release contains the IFC project template and the script that
> builds it. The drawing style, a neutral example model and an IDS follow in later releases.

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
| `style/` | Drawing style: CSS, hatch patterns, dimension markers, title blocks A4 to A0 | CC BY 4.0 |
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

What is inside: storeys KG, EG, OG and DG with their levels, 39 materials with
categories and colours, and 234 types (layered walls, slabs and coverings; doors and
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

## Requirements

Tested with:

- Blender 5.2.0 LTS
- Bonsai 0.9.1 (unstable channel)
- IfcOpenShell 0.9.1a261028

## Licences

This repository follows the [REUSE](https://reuse.software) convention.

- **Code** (Python scripts and add-on code): **GPL-3.0-or-later**, in line with Bonsai.
  See [`LICENSE`](LICENSE).
- **Templates, drawing style, examples, IDS and documentation**: **CC BY 4.0**.
  See [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt).

Which licence applies to which path is recorded in [`REUSE.toml`](REUSE.toml).

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
