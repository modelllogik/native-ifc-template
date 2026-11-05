# native-ifc-template

**A project template that lives in native IFC, and a way to derive drawings from it.**

*Modelllogik is German for model logic.*

> **Status: early.** This repository has its structure, licences and contribution rules.
> The template, the drawing style and the example model follow in the first release.

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

## Requirements

Tested versions are named with every release. Planned baseline:

- Blender with the Bonsai add-on
- IfcOpenShell (Python) for the build and check scripts

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

## Related work upstream

Findings that belong to Bonsai or IfcOpenShell are reported there, not worked around
silently here. Links to those reports will be listed in this section.
