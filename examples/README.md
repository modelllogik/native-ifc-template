# Example house

[`example_house.ifc`](example_house.ifc) is a plain, fictitious single-family house built
from the template by [`build_example.py`](build_example.py). It has no location, no
terrain and no georeference.

It serves two purposes:

- **Show the template in use.** Every family of types occurs at least once, in a place
  where it makes sense.
- **Test model.** Drawings, line weights, hatching, door and window symbols and
  schedules can be checked against a known model. bonsai-btk uses it for the same
  purpose.

## What is in it

| Part | Content |
|---|---|
| Ground floor (EG) | living room, hall with stair, kitchen, WC, utility room; four external doors (front door and utility door each coupled with a side panel in one opening, back door, kitchen door); external walls masonry 24 + ETICS 12, butt-jointed; sand-lime brick and drywall partitions |
| Upper floor (OG) | converted attic: knee walls, gables, two bedrooms, study, bathroom; a gallery with a walkway on either side of the stair hole, so that no door leads into the hole, and a landing of about 1 m in front of the arrival; knee partitions in timber studs, sloped plasterboard lining, plasterboard ceiling below the collar beams |
| Roof | gable roof 40°: rafters about 70 cm apart, verge rafters (Flugsparren), a rafter in front of the gable render and one at its inner face; birdsmouths (Kerven) at all purlins; foot purlins on a bitumen membrane, ridge purlin on posts with braces, collar beams; insulation between the rafters, one piece per bay; build-up on the rafters, verge and eaves in planed boarding; gutters and downpipes |
| Facade | ETICS and render up to the rafter top, at the gables and, with the rafters running through, at the eaves; plinth render up to +0.30; ETICS and plinth render below French windows and external doors; window sills in aluminium; external and internal reveals rendered and plastered |
| Stair | one straight flight of 17 risers, grouped as an `IfcStair`; stair hole plastered; entrance landing in front of the front door |
| Railings | stair, stair hole and the upper French windows; each generated from a line (its axis) with the parameters of the railing type: posts, handrail, bottom rail, bars at most 12 cm apart |
| Foundation | ground slab on insulation, strip footings, perimeter insulation in one plane with the ETICS |
| Finishes | floor build-ups (parquet, tiles, screed), internal plaster on all masonry and sand-lime walls, ETICS as a covering on the edge of the floor slab |
| Terrace | timber decking |
| Carport | 3 m east of the house: steel columns HEA, IPE, HEB on pad footings, steel beams, timber joists, flat roof |

Doors and windows cover timber and PVC, single and double sash, French windows with and
without a second leaf, side panels, external doors with and without fanlight, internal
doors for all three partition thicknesses and both hinge sides (DIN links, DIN rechts).

Every element is an occurrence of a template type, including the stair assembly, the
window sills, the gutters and the downpipes. Annotation types (level markers) are not used:
they belong to drawings.

The roof, the eaves, the plinth and the opening details follow a worked reference house;
only the construction is taken over, no data of that house.

## Building it yourself

```bash
python template/build_template.py native_template.ifc
python examples/build_example.py native_template.ifc example_house.ifc
```

IfcOpenShell only, no Blender. The same scripts give the same file byte for byte.

At the end the script checks that every type family occurs at least once and lists the
missing ones (exit code 1). A family is a type name without its dimensions:
"Stütze HEA 160 S235" belongs to "Stütze HEA S235". So when you add a type family to the
template, the check tells you that the example needs it too.

## Known simplifications

- Rafters end in plumb cuts at the eaves and the ridge.
- Internal doors in plastered masonry have a frame two plaster thicknesses deeper than the
  wall; the reveals are not plastered. The casings still reach down to the raw floor and
  overlap the floor build-up by a few millimetres (Bonsai's door geometry starts at the
  door origin).
- Stair flights are plain extrusions of their side profile, not Bonsai's parametric
  stair; the values are in `Pset_StairFlightCommon`.
- The gable walls and the upper partitions are clipped by the roof planes. Bonsai keeps
  these clippings when it regenerates a wall (`BBIM_Boolean`).
- Openings in render and insulation coverings are separate opening elements, one per
  covering.
