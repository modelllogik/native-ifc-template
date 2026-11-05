# SPDX-FileCopyrightText: 2026 Andràs Marghescu and contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""
build_template.py - builds the native IFC project template for Bonsai (IFC4).

Usage (no Blender needed, IfcOpenShell only):
    python build_template.py  TARGET.ifc

What the template contains:
  - site / building / storeys KG, EG, OG, DG; storey elevations = structural
    level (OKRF, top of structural floor)
  - materials with IfcMaterial.Category and a surface colour
  - layered element types (walls, slabs, coverings)
  - door and window types (parametric as in Bonsai), each in timber and PVC
  - annotation types for level markers
  - profile types: timber by structural role (rafter, purlin, collar, column,
    beam; solid and glued laminated timber), steel IPE/HEA/HEB as beam and column
  - all types in an IfcProjectLibrary, so the file also works as a library

Deliberately NOT included:
  - no georeference. Bonsai merges the template into a new project with
    ifcpatch MergeProjects; if the map origin differs, the whole content is
    moved (MergeProjects.py, lines 101-132). Georeference each project afterwards.
  - no drawings or sheets (separate step).

The same script produces the same file byte for byte (GlobalIds derived from
names, fixed time stamp). Bonsai assigns new GlobalIds when it creates a project.

Names of types and materials are German on purpose: the template follows German
building practice and the drawing conventions of DIN 1356.
Abbreviations used in names and descriptions:
  OKRF  Oberkante Rohfussboden  - top of structural floor
  OKFF  Oberkante Fertigfussboden - top of finished floor
  MW    Mauerwerk (masonry), KS Kalksandstein (sand-lime brick),
  STB   Stahlbeton (reinforced concrete), WDVS external thermal insulation
        composite system, KVH/BSH solid / glued laminated timber
"""
import json
import sys
import uuid

import numpy as np
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.profile
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.style
import ifcopenshell.api.unit
import ifcopenshell.guid
import ifcopenshell.util.shape_builder

VERSION = "0.1.0"
TIMESTAMP = "2026-10-30T00:00:00"

# ---------------------------------------------------------------------------
# DATA - maintained here
# ---------------------------------------------------------------------------

PROJECT = "Native IFC Template"
SITE = "Grundstück"
BUILDING = "Gebäude"

# Storey heights: OKRF EG -0.15, OKFF EG 0.00, clear room height 2.65, slab 0.20.
# Floor build-up therefore 0.15, storey height OKFF to OKFF 3.00.
# The spatial decomposition always follows the structure: elevation and placement
# of a storey = OKRF.
FLOOR_BUILDUP = 0.15
CLEAR_HEIGHT = 2.65
SLAB = 0.20
STOREY_HEIGHT = CLEAR_HEIGHT + SLAB + FLOOR_BUILDUP  # 3.00
SILL_OKFF = 1.00  # window sill height above OKFF

# (name, OKFF, above ground, entrance level)
STOREYS = [
    ("KG", -1 * STOREY_HEIGHT, False, False),  # basement height assumed
    ("EG", 0.0, True, True),
    ("OG", 1 * STOREY_HEIGHT, True, False),
    ("DG", 2 * STOREY_HEIGHT, True, False),
]

# (name, category, RGB 0..1, transparency or None)
# Category = key for hatching and legend in the drawing style (no umlauts).
# Colours marked "assumed" are proposals, not taken from a product.
MATERIALS = [
    ("Hochlochziegel_Mat", "Mauerwerk", (1.0, 0.2588, 0.0788), None),
    ("Kalksandstein", "Mauerwerk", (0.9098, 0.8941, 0.8549), None),
    ("WDVS", "Daemmung", (1.0, 0.7748, 0.6361), None),
    ("Holzfaserplatte", "Daemmung", (0.7882, 0.6353, 0.4784), None),
    # roof structure; colours assumed
    ("Mineralwolle", "Daemmung", (0.93, 0.87, 0.55), None),
    ("Dampfbremse", "Abdichtung", (0.15, 0.15, 0.17), None),
    ("Unterdeckbahn", "Abdichtung", (0.15, 0.15, 0.17), None),   # vapour-open, 0.5 mm
    ("Sichtschalung", "Holz", (0.91, 0.78, 0.55), None),          # planed boarding, roof overhang
    ("Stahlbeton", "Stahlbeton", (0.3743, 0.3743, 0.3743), None),
    ("Beton C25/30", "Beton", (0.62, 0.62, 0.60), None),
    ("Nadelholz C24", "Holz", (0.85, 0.65, 0.38), None),
    ("Brettschichtholz GL24h", "Holz", (0.93, 0.77, 0.52), None),  # colour assumed
    ("OSB-Platte", "Holzwerkstoff", (0.78, 0.62, 0.40), None),
    ("Baustahl S235", "Stahl", (0.45, 0.48, 0.52), None),
    ("Stahl verzinkt", "Stahl", (0.451, 0.4784, 0.5216), None),
    ("Aluminium", "Metall", (0.7255, 0.7373, 0.7529), None),
    ("Kupfer", "Metall", (0.72, 0.45, 0.20), None),   # gutters and downpipes; colour assumed
    ("XPS Perimeter", "Perimeterdaemmung", (0.30, 0.55, 0.80), None),
    ("Bitumenbahn", "Abdichtung", (0.15, 0.15, 0.17), None),
    ("Kalkzementputz", "Putz", (0.88, 0.86, 0.80), None),
    # external and plinth render as coverings; colours assumed
    ("Außenputz", "Putz", (0.95, 0.94, 0.90), None),
    ("Sockelputz", "Putz", (0.55, 0.55, 0.53), None),
    ("Zementestrich", "Estrich", (0.72, 0.71, 0.68), None),
    # floor build-up in layers; colours assumed
    ("EPS Ausgleichsdämmung", "Daemmung", (0.96, 0.92, 0.80), None),
    ("Trittschalldämmung", "Daemmung", (0.90, 0.85, 0.70), None),
    ("PE-Folie", "Abdichtung", (0.15, 0.15, 0.17), None),   # 0.1 mm, exaggerated on the sheet
    ("Parkett", "Belag", (0.80, 0.60, 0.36), None),
    ("Fliesen", "Belag", (0.86, 0.86, 0.84), None),
    ("Gipskartonplatte", "Trockenbau", (0.93, 0.91, 0.86), None),
    ("Floatglas", "Glas", (0.62, 0.78, 0.80), 0.5),
    ("Kunststoff (PVC)", "Kunststoff", (0.95, 0.95, 0.94), None),  # colour assumed
    # doors and windows: frame and leaf as separate materials, so they can be
    # told apart in the model; colours assumed
    ("Holz Rahmen", "Holz", (0.55, 0.36, 0.18), None),
    ("Holz Blatt", "Holz", (0.88, 0.70, 0.45), None),
    ("Kunststoff Rahmen", "Kunststoff", (0.50, 0.52, 0.55), None),
    ("Kunststoff Blatt", "Kunststoff", (0.97, 0.97, 0.96), None),
    ("Dachziegel", "Dachdeckung", (0.6353, 0.2549, 0.1725), None),
    ("Betonpflaster", "Belag", (0.7098, 0.6863, 0.651), None),
    ("Kies 16/32", "Kies", (0.66, 0.62, 0.55), None),
    ("Erdreich", "Erdreich", (0.42, 0.32, 0.22), None),
]

# Layered element types.
# (type name, IFC class, PredefinedType, Pset_*Common {..}, layer set direction or None,
#  [(material, thickness m), ...] - the first layer lies on the reference line)
# Walls: masonry on the reference line, insulation to the left of the drawing
# direction. Drawn clockwise around the building, the insulation is outside;
# otherwise select the wall and press Shift+F (bim.flip_wall).
# Slabs and roofs: bottom to top.
# Direction: None = Bonsai default (wall AXIS2, slab AXIS3);
# AXIS2 on coverings = vertical like a wall.
TYPES = [
    ("Außenwand MW 24 + WDVS 12", "IfcWallType", "SOLIDWALL",
     {"IsExternal": True, "LoadBearing": True}, None,
     [("Hochlochziegel_Mat", 0.24), ("WDVS", 0.12)]),
    ("Innenwand KS 17,5", "IfcWallType", "SOLIDWALL",
     {"IsExternal": False, "LoadBearing": True}, None,
     [("Kalksandstein", 0.175)]),
    ("Trockenbauwand 10", "IfcWallType", "PARTITIONING",
     {"IsExternal": False, "LoadBearing": False}, None,
     [("Gipskartonplatte", 0.10)]),
    ("Abseitenwand Holzständer 15", "IfcWallType", "PARTITIONING",
     {"IsExternal": False, "LoadBearing": False}, None,
     [("Nadelholz C24", 0.15)]),
    ("Bodenplatte STB 25", "IfcSlabType", "BASESLAB",
     {"IsExternal": False, "LoadBearing": True}, None,
     [("Stahlbeton", 0.25)]),
    ("Decke STB 20", "IfcSlabType", "FLOOR",
     {"IsExternal": False, "LoadBearing": True}, None,
     [("Stahlbeton", 0.20)]),
    ("Dachaufbau 35", "IfcSlabType", "ROOF",
     {"IsExternal": True, "LoadBearing": True}, None,
     [("Nadelholz C24", 0.20), ("Holzfaserplatte", 0.05), ("Nadelholz C24", 0.04),
      ("Nadelholz C24", 0.03), ("Dachziegel", 0.03)]),
    # Roof build-up above separately modelled rafters: the insulation between the
    # rafters is its own element, so the roof slab lies above the rafters only.
    # Inside the building wood-fibre board, at the overhang planed boarding on a
    # packing layer of the same total; underlay 0.5 mm.
    ("Dachaufbau über Sparren Holzfaser 5", "IfcSlabType", "ROOF",
     {"IsExternal": True, "LoadBearing": False}, None,
     [("Holzfaserplatte", 0.05), ("Unterdeckbahn", 0.0005), ("Nadelholz C24", 0.04),
      ("Nadelholz C24", 0.03), ("Dachziegel", 0.03)]),
    ("Dachaufbau über Sparren Sichtschalung", "IfcSlabType", "ROOF",
     {"IsExternal": True, "LoadBearing": False}, None,
     [("Nadelholz C24", 0.026), ("Sichtschalung", 0.024), ("Unterdeckbahn", 0.0005), ("Nadelholz C24", 0.04),
      ("Nadelholz C24", 0.03), ("Dachziegel", 0.03)]),
    ("Terrassenbelag Holz 4", "IfcSlabType", "FLOOR",
     {"IsExternal": True, "LoadBearing": False}, None,
     [("Nadelholz C24", 0.04)]),
    # Floor build-up 15 cm, bottom to top; the top layer is the finish shown in the
    # room stamp. PE film 0.1 mm below the screed (exaggerated on the sheet); turned
    # up at the edges only in detail drawings, not modelled here.
    ("Fußbodenaufbau 15 Parkett", "IfcCoveringType", "FLOORING",
     {}, None,
     [("EPS Ausgleichsdämmung", 0.04), ("Trittschalldämmung", 0.03), ("PE-Folie", 0.0001), ("Zementestrich", 0.065), ("Parkett", 0.015)]),
    ("Fußbodenaufbau 15 Fliesen", "IfcCoveringType", "FLOORING",
     {}, None,
     [("EPS Ausgleichsdämmung", 0.04), ("Trittschalldämmung", 0.03), ("PE-Folie", 0.0001), ("Zementestrich", 0.065), ("Fliesen", 0.015)]),
    ("Fußbodenaufbau 15 Estrich", "IfcCoveringType", "FLOORING",
     {}, None,
     [("EPS Ausgleichsdämmung", 0.04), ("Trittschalldämmung", 0.03), ("PE-Folie", 0.0001), ("Zementestrich", 0.08)]),
    ("Perimeterdämmung 12", "IfcCoveringType", "INSULATION",
     {"IsExternal": True}, "AXIS2",
     [("XPS Perimeter", 0.12)]),
    ("Dämmung unter Bodenplatte 12", "IfcCoveringType", "INSULATION",
     {"IsExternal": True}, None,
     [("XPS Perimeter", 0.12)]),
    ("WDVS 12", "IfcCoveringType", "CLADDING",
     {"IsExternal": True}, "AXIS2",
     [("WDVS", 0.12)]),
    # internal plaster as a covering of the room: basis for the living area (WoFlV)
    ("Innenputz 1,5", "IfcCoveringType", "CLADDING",
     {"IsExternal": False}, "AXIS2",
     [("Kalkzementputz", 0.015)]),
    # external render on the insulation and plinth render: dimensions stay structural,
    # render is added as a covering, also in the reveals
    ("Außenputz 1", "IfcCoveringType", "CLADDING",
     {"IsExternal": True}, "AXIS2",
     [("Außenputz", 0.01)]),
    ("Sockelputz 1", "IfcCoveringType", "CLADDING",
     {"IsExternal": True}, "AXIS2",
     [("Sockelputz", 0.01)]),
    # lining of the sloped ceiling below the rafters, a covering of the room;
    # bottom to top: plasterboard 2 x 12.5, battens 2.4, vapour barrier 0.2 mm (assumed)
    ("Dachschräge GK 2 × 12,5", "IfcCoveringType", "CEILING",
     {"IsExternal": False}, None,
     [("Gipskartonplatte", 0.0125), ("Gipskartonplatte", 0.0125), ("Nadelholz C24", 0.024), ("Dampfbremse", 0.0002)]),
]

# Annotation types; the classes are CSS classes of the drawing style
ANNOTATION_TYPES = [
    ("Höhenkote Rohbau", "IfcAnnotation/SECTION_LEVEL", "din-kote-roh"),
    ("Höhenkote Fertig", "IfcAnnotation/SECTION_LEVEL", "din-kote-fertig"),
    ("Höhenkote UK Rohbau", "IfcAnnotation/SECTION_LEVEL", "din-kote-roh din-kote-uk"),
    ("Höhenkote UK Fertig", "IfcAnnotation/SECTION_LEVEL", "din-kote-fertig din-kote-uk"),
]

# Profiles. As in Bonsai's steel library: type without representation, only with an
# IfcMaterialProfileSet; one IfcProfileDef shared by all types of the same section.
# Timber by structural role (rafters and purlins as IfcMember RAFTER/PURLIN).
# Sections b/h in cm: common stock sizes (assumed).
# Name: "<role> <section> <strength class>", e.g. "Sparren KVH 8/20 C24".
KVH = "Nadelholz C24"
BSH = "Brettschichtholz GL24h"
STEEL = "Baustahl S235"
MATERIAL_SHORT = {KVH: "C24", BSH: "GL24h", STEEL: "S235"}
BSH_SIZES = [(10, 20), (10, 24), (12, 24), (12, 28), (14, 28), (14, 32), (16, 32), (16, 40), (20, 40)]
# (role, IFC class, PredefinedType, material, short name, [(b, h) cm, ...])
TIMBER_ROLES = [
    ("Sparren", "IfcMemberType", "RAFTER", KVH, "KVH",
     [(6, 14), (6, 16), (6, 18), (6, 20), (6, 24), (8, 16), (8, 20), (8, 24), (10, 20)]),
    ("Pfette", "IfcMemberType", "PURLIN", KVH, "KVH", [(12, 16), (12, 20), (12, 24)]),
    ("Pfette", "IfcMemberType", "PURLIN", BSH, "BSH", sorted(BSH_SIZES + [(16, 24)])),
    ("Kopfband", "IfcMemberType", "BRACE", KVH, "KVH", [(10, 10), (12, 12)]),
    ("Kehlbalken", "IfcMemberType", "COLLAR", KVH, "KVH", [(6, 16), (6, 18), (6, 20), (8, 16), (8, 20)]),
    ("Stütze", "IfcColumnType", "COLUMN", KVH, "KVH", [(10, 10), (12, 12), (14, 14)]),
    ("Balken", "IfcBeamType", "JOIST", KVH, "KVH",
     [(6, 18), (6, 20), (6, 24), (8, 16), (8, 20), (8, 24), (10, 20), (12, 20), (12, 24)]),
    ("Balken", "IfcBeamType", "JOIST", BSH, "BSH", BSH_SIZES),
]
# Steel: dimensions read from Bonsai's "IFC4 EU Steel.ifc" (IfcOpenShell 0.9.1a261027),
# in mm: width, depth, web, flange, fillet radius. Each section as beam and as column.
STEEL_ROLES = [("Träger", "IfcBeamType", "BEAM"), ("Stütze", "IfcColumnType", "COLUMN")]
STEEL_SECTIONS = {
    "IPE 100": (55, 100, 4.1, 5.7, 7), "IPE 120": (64, 120, 4.4, 6.3, 7),
    "IPE 140": (73, 140, 4.7, 6.9, 7), "IPE 160": (82, 160, 5.0, 7.4, 9),
    "IPE 180": (91, 180, 5.3, 8.0, 9), "IPE 200": (100, 200, 5.6, 8.5, 12),
    "IPE 220": (110, 220, 5.9, 9.2, 12), "IPE 240": (120, 240, 6.2, 9.8, 15),
    "IPE 270": (135, 270, 6.6, 10.2, 15), "IPE 300": (150, 300, 7.1, 10.7, 15),
    "IPE 330": (160, 330, 7.5, 11.5, 18), "IPE 360": (170, 360, 8.0, 12.7, 18),
    "IPE 400": (180, 400, 8.6, 13.5, 21),
    "HEA 100": (100, 96, 5.0, 8.0, 12), "HEA 120": (120, 114, 5.0, 8.0, 12),
    "HEA 140": (140, 133, 5.5, 8.5, 12), "HEA 160": (160, 152, 6.0, 9.0, 15),
    "HEA 180": (180, 171, 6.0, 9.5, 15), "HEA 200": (200, 190, 6.5, 10.0, 18),
    "HEA 220": (220, 210, 7.0, 11.0, 18), "HEA 240": (240, 230, 7.5, 12.0, 21),
    "HEA 260": (260, 250, 7.5, 12.5, 24), "HEA 280": (280, 270, 8.0, 13.0, 24),
    "HEA 300": (300, 290, 8.5, 14.0, 27), "HEA 320": (300, 310, 9.0, 15.5, 27),
    "HEA 340": (300, 330, 9.5, 16.5, 27), "HEA 360": (300, 350, 10.0, 17.5, 27),
    "HEA 400": (300, 390, 11.0, 19.0, 27),
    "HEB 100": (100, 100, 6.0, 10.0, 12), "HEB 120": (120, 120, 6.5, 11.0, 12),
    "HEB 140": (140, 140, 7.0, 12.0, 12), "HEB 160": (160, 160, 8.0, 13.0, 15),
    "HEB 180": (180, 180, 8.5, 14.0, 15), "HEB 200": (200, 200, 9.0, 15.0, 18),
    "HEB 220": (220, 220, 9.5, 16.0, 18), "HEB 240": (240, 240, 10.0, 17.0, 21),
    "HEB 260": (260, 260, 10.0, 17.5, 24), "HEB 280": (280, 280, 10.5, 18.0, 24),
    "HEB 300": (300, 300, 11.0, 19.0, 27), "HEB 320": (300, 320, 11.5, 20.5, 27),
    "HEB 340": (300, 340, 12.0, 21.5, 27), "HEB 360": (300, 360, 12.5, 22.5, 27),
    "HEB 400": (300, 400, 13.5, 24.0, 27),
}

# Doors and windows.
# Bonsai places doors and windows at the storey elevation (= OKRF) and cuts the
# opening from the type's Profile representation (opening.py, line 481).
#   Structural opening from OKRF (the screed runs through), the door/window stands on OKFF:
#   door 2.13 from OKFF -> opening 2.28 from OKRF, a 0.15 threshold lifts the leaf to OKFF
#     (internal door: threshold in frame depth; external door: in frame depth = sub-frame)
#   window 1.26 high, sill 1.00 from OKFF -> 1.15 from OKRF (a matter of placement:
#     Bonsai "RL" for windows = rl2, scene setting, not part of the type)
#   French window and side panel: a window without threshold -> body lifted by 0.15,
#     with a box in frame depth below it (sub-frame). NOT parametric: editing it
#     parametrically in Bonsai rebuilds the body without the box.
#   External doors and windows are placed FROM OUTSIDE. Bonsai puts the element on the
#     wall face nearer to the mouse pointer and measures the frame offset from there
#     (opening.py, lines 304-312). Offset = insulation thickness 0.12 -> outer edge of
#     the frame on the boundary insulation/masonry, independent of the masonry
#     thickness; leaves inside, external doors open inwards. Shift+F (flip fill) does
#     NOT fix an element placed from the wrong side (opening.py, lines 710-720 include
#     the offset) - delete and place again. In reality the insulation overlaps the
#     frame by 2 cm; Bonsai's opening cuts all layers at full width.
# Type names give dimensions from OKFF in cm, the description gives the structural size.
# Each door as DIN left and DIN right: Bonsai switches the hinge side through the
# operation type of the TYPE (door.py, lines 673-684, applies to all doors of the type);
# per door only the turn to the other wall face is possible.
# DIN 107: you stand on the side to which the door opens - hinges on the right =
# DIN right. Bonsai's SINGLE_SWING_LEFT has its hinge at x = 0 and opens towards +y;
# seen from +y it is on the right -> LEFT = DIN right (derived from the geometry).
DIN_SIDE = {"DIN rechts": "SINGLE_SWING_LEFT", "DIN links": "SINGLE_SWING_RIGHT"}
DOOR_H = 2.13 + FLOOR_BUILDUP       # 2.28
WINDOW_H = 1.26
SILL = SILL_OKFF + FLOOR_BUILDUP    # 1.15 from OKFF; used as Bonsai RL when placing
FRENCH_WINDOW_H = SILL + WINDOW_H   # 2.41
THRESHOLD = FLOOR_BUILDUP           # 0.15
FRAME_DEPTH = 0.08                  # external doors and windows - assumed
FRAME_OFFSET = 0.12                 # frame from outer face = insulation 12 - assumed
SUBFRAME = "XPS Perimeter"          # material of the box below - assumed

# Finishes: name -> (frame = Lining, leaf/sash = Framing, glass)
FINISHES = {
    "Holz": ("Holz Rahmen", "Holz Blatt", "Floatglas"),
    "Kunststoff": ("Kunststoff Rahmen", "Kunststoff Blatt", "Floatglas"),
}

# (name without finish, width, height from OKRF, external, fanlight or None)
# Fanlight: (bottom edge from OKRF, transom thickness) - assumed
DOORS = [
    ("Innentür {a} 76 × 213", 0.76, DOOR_H, False, None),
    ("Innentür {a} 88,5 × 213", 0.885, DOOR_H, False, None),
    ("Innentür {a} 101 × 213", 1.01, DOOR_H, False, None),
    ("Außentür {a} 113,5 × 213", 1.135, DOOR_H, True, None),  # width assumed
    ("Außentür {a} mit Oberlicht 113,5 × 263", 1.135, DOOR_H + 0.50, True,
     (DOOR_H, 0.05)),  # fanlight 50 cm assumed
    ("Außentür {a} 101 × 211", 1.01, 2.26, True, None),  # lintel 2.26 from OKRF
]

# (name, width, height from OKRF, Bonsai partitioning, on OKFF with sub-frame)
WINDOWS = [
    ("Fenster 1-flg. {a} 76 × 126", 0.76, WINDOW_H, "SINGLE_PANEL", False),
    ("Fenster 1-flg. {a} 88,5 × 126", 0.885, WINDOW_H, "SINGLE_PANEL", False),
    ("Fenster 1-flg. {a} 101 × 126", 1.01, WINDOW_H, "SINGLE_PANEL", False),
    ("Fenster 2-flg. {a} 126 × 126", 1.26, WINDOW_H, "DOUBLE_PANEL_VERTICAL", False),
    ("Fenster 2-flg. {a} 151 × 126", 1.51, WINDOW_H, "DOUBLE_PANEL_VERTICAL", False),
    ("Fenstertür {a} 88,5 × 226", 0.885, FRENCH_WINDOW_H, "SINGLE_PANEL", True),
    ("Fenstertür {a} 101 × 226", 1.01, FRENCH_WINDOW_H, "SINGLE_PANEL", True),
    ("Seitenteil fest {a} 51 × 213", 0.51, DOOR_H, "SINGLE_PANEL", True),  # width assumed
    # sill 0.875 / lintel 2.26 from OKRF
    ("Fenster 2-flg. {a} 126 × 138,5", 1.26, 1.385, "DOUBLE_PANEL_VERTICAL", False),
    ("Fenster 2-flg. {a} 151 × 138,5", 1.51, 1.385, "DOUBLE_PANEL_VERTICAL", False),
    ("Fenster 1-flg. {a} 63,5 × 87,5", 0.635, 0.875, "SINGLE_PANEL", False),
    ("Fenster 1-flg. {a} 76 × 100", 0.76, 1.00, "SINGLE_PANEL", False),
    ("Fenstertür 2-flg. {a} 201 × 211", 2.01, 2.26, "DOUBLE_PANEL_VERTICAL", True),
]
# Sill from OKRF where it differs from the rule (only for the type description)
SILL_DIFFERENT = {
    "Fenster 2-flg. {a} 126 × 138,5": 0.875, "Fenster 2-flg. {a} 151 × 138,5": 0.875,
    "Fenster 1-flg. {a} 63,5 × 87,5": 1.385, "Fenster 1-flg. {a} 76 × 100": 1.26,
}

# Bonsai defaults (Add Door / Add Window, read in Bonsai 0.9.1)
DOOR_LINING = {"lining_depth": 0.05, "lining_thickness": 0.05, "lining_offset": 0.0,
               "lining_to_panel_offset_x": 0.025, "lining_to_panel_offset_y": 0.025,
               "transom_thickness": 0.0, "casing_thickness": 0.075, "casing_depth": 0.005,
               "threshold_thickness": 0.025, "threshold_depth": 0.1, "threshold_offset": 0.0}
DOOR_PANEL = {"panel_depth": 0.035, "panel_width_ratio": 1.0}
# Internal doors: wrap-around frame in wall thickness, one set per internal wall type.
# Bonsai then puts the casing on both wall faces (add_door_representation.py,
# lines 542-557, IfcOpenShell 0.9.1); the leaf sits 2.5 cm from the opening side as
# in Bonsai's default. Wall thicknesses come from TYPES - a new internal wall type
# brings its own door set.
INTERNAL_WALLS = [(n.split()[-1], round(sum(d for _, d in s), 4)) for n, k, _, c, _, s in TYPES
                  if k == "IfcWallType" and not c["IsExternal"]]
WINDOW_LINING = {"lining_depth": 0.05, "lining_thickness": 0.05, "lining_offset": 0.05,
                 "lining_to_panel_offset_x": 0.025, "lining_to_panel_offset_y": 0.025}
WINDOW_PANEL = {"frame_depth": [0.035, 0.035, 0.035], "frame_thickness": [0.035, 0.035, 0.035]}
# Mullion: Bonsai takes its position as absolute (mullion centre from the left outer
# edge); its default 0.3 only fits a 60 cm window. Here: half the width.
MULLION_THICKNESS = 0.05  # assumed
PANEL_COUNT = {"SINGLE_PANEL": 1, "DOUBLE_PANEL_VERTICAL": 2}

# ---------------------------------------------------------------------------
# BUILD - mechanics only from here
# ---------------------------------------------------------------------------

api = ifcopenshell.api
_NS = uuid.UUID("6f1c2a52-9d0e-4c39-9b1e-0c7e3b6a1d18")

_ASSIGNED = set()


def gid(key):
    """Fixed GlobalId from a key - same data, same file."""
    _ASSIGNED.add(key)
    return ifcopenshell.guid.compress(uuid.uuid5(_NS, key).hex)


def new(f, ifc_class, key, **kw):
    e = api.root.create_entity(f, ifc_class=ifc_class, **kw)
    e.GlobalId = gid(key)
    return e


def _camel(name):
    """lining_to_panel_offset_x -> LiningToPanelOffsetX (as the API expects)"""
    return "".join(t.upper() if len(t) == 1 else t.capitalize() for t in name.split("_"))


def represent(f, typ, contexts, make):
    """Create the representations of a door/window type in Bonsai's order.
    The parts (Lining, Framing, Glazing) get their colour through shape aspects,
    and these only exist with part_of_product = the type's RepresentationMap
    (util/representation.py get_part_of_product). Hence: create, then create
    again with that reference and swap."""
    for c in contexts:
        r = make(c, None)
        api.geometry.assign_representation(f, product=typ, representation=r)
        rmap = [m for m in typ.RepresentationMaps if m.MappedRepresentation == r][0]
        r2 = make(c, rmap)
        rmap.MappedRepresentation = r2
        api.geometry.remove_representation(f, representation=r)


def lift(f, r, c, b, h, part, lining):
    """Lift the window body by THRESHOLD and add the box below (sub-frame);
    redraw the profile (= opening) from OKRF to h."""
    sb = ifcopenshell.util.shape_builder.ShapeBuilder(f)
    if c.ContextIdentifier == "Body" and c.TargetView == "MODEL_VIEW":
        sb.translate(list(r.Items), (0.0, 0.0, THRESHOLD))
        depth = lining["LiningDepth"]
        box = sb.extrude(sb.rectangle(size=(b, depth)), magnitude=THRESHOLD,
                         position=(0.0, lining["LiningOffset"], 0.0))
        r.Items = list(r.Items) + [box]
        if part is not None:
            api.geometry.add_shape_aspect(f, "Unterbau", items=[box], representation=r, part_of_product=part)
    elif c.ContextIdentifier == "Profile":
        line = sb.polyline([(0.0, 0.0, 0.0), (b, 0.0, 0.0), (b, 0.0, h), (0.0, 0.0, h)], closed=True)
        r.Items = [line]


def place(f, product, z):
    m = np.eye(4)
    m[2][3] = z
    api.geometry.edit_object_placement(f, product=product, matrix=m, is_si=True)


def pset(f, product, name, values, key):
    if not values:
        return
    p = api.pset.add_pset(f, product=product, name=name)
    p.GlobalId = gid(key)
    api.pset.edit_pset(f, pset=p, properties=values)


def build():
    f = api.project.create_file(version="IFC4")
    project = new(f, "IfcProject", "projekt", name=PROJECT)
    project.Description = f"Native IFC template (drawing conventions DIN 1356-1), version {VERSION}"

    units = [
        api.unit.add_si_unit(f, unit_type="LENGTHUNIT"),
        api.unit.add_si_unit(f, unit_type="AREAUNIT"),
        api.unit.add_si_unit(f, unit_type="VOLUMEUNIT"),
        api.unit.add_conversion_based_unit(f, name="degree"),
    ]
    api.unit.assign_unit(f, units=units)

    model = api.context.add_context(f, context_type="Model")
    body = api.context.add_context(
        f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model
    )
    profile = api.context.add_context(
        f, context_type="Model", context_identifier="Profile", target_view="ELEVATION_VIEW", parent=model
    )
    plan = api.context.add_context(f, context_type="Plan")
    plan_body = api.context.add_context(
        f, context_type="Plan", context_identifier="Body", target_view="PLAN_VIEW", parent=plan
    )
    contexts = (profile, body, plan_body)  # order as in Bonsai (Body before Plan/Body, #2744)

    # Spatial structure
    site = new(f, "IfcSite", "site", name=SITE)
    building = new(f, "IfcBuilding", "building", name=BUILDING)
    api.aggregate.assign_object(f, products=[site], relating_object=project)
    api.aggregate.assign_object(f, products=[building], relating_object=site)
    place(f, site, 0.0)
    place(f, building, 0.0)
    for name, okff, above, entrance in STOREYS:
        okrf = round(okff - FLOOR_BUILDUP, 4)
        s = new(f, "IfcBuildingStorey", "storey/" + name, name=name)
        s.Elevation = okrf
        s.Description = f"OKRF {okrf:+.2f} / OKFF {okff:+.2f}"
        api.aggregate.assign_object(f, products=[s], relating_object=building)
        place(f, s, okrf)
        # AboveGround is an IfcLogical; edit_pset fails on a bool there (0.9.0)
        pset(f, s, "Pset_BuildingStoreyCommon",
             {"AboveGround": f.create_entity("IfcLogical", above), "EntranceLevel": entrance}, "pset/storey/" + name)
        # as IfcLengthMeasure, so that MergeProjects converts them into a mm project
        length = lambda v: f.create_entity("IfcLengthMeasure", float(v))
        # property names are read by the add-on - keep them
        pset(f, s, "EPset_Geschoss", {
            "OKRF": length(okrf), "OKFF": length(round(okff, 4)), "Fussbodenaufbau": length(FLOOR_BUILDUP),
            "LichteRaumhoehe": length(CLEAR_HEIGHT), "Deckenstaerke": length(SLAB),
            "Bruestungshoehe": length(SILL_OKFF),
        }, "epset/storey/" + name)

    # Materials
    mat = {}
    for name, category, rgb, transparency in MATERIALS:
        m = api.material.add_material(f, name=name, category=category)
        mat[name] = m
        style = api.style.add_style(f, name=name)
        attr = {"SurfaceColour": {"Name": None, "Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]}}
        if transparency is not None:
            attr["Transparency"] = transparency
        api.style.add_surface_style(f, style=style, ifc_class="IfcSurfaceStyleShading", attributes=attr)
        api.style.assign_material_style(f, material=m, style=style, context=body)

    # Library
    library = new(f, "IfcProjectLibrary", "library", name=PROJECT)
    api.project.assign_declaration(f, definitions=[library], relating_context=project)

    types = []
    for name, ifc_class, predefined, common, direction, layers in TYPES:
        t = new(f, ifc_class, "type/" + name, name=name, predefined_type=predefined)
        lset = api.material.add_material_set(f, name=name, set_type="IfcMaterialLayerSet")
        for mname, thickness in layers:
            layer = api.material.add_layer(f, layer_set=lset, material=mat[mname])
            api.material.edit_layer(f, layer=layer, attributes={"LayerThickness": thickness, "Name": mname})
        api.material.assign_material(f, products=[t], type="IfcMaterialLayerSet", material=lset)
        common_name = "Pset_" + ifc_class[3:-4] + "Common"
        pset(f, t, common_name, common, "pset/type/" + name)
        if direction:
            pset(f, t, "EPset_Parametric", {"LayerSetDirection": direction}, "epset/type/" + name)
        types.append(t)

    for pattern, b, h, external, fanlight in DOORS:
        for wall, wall_thickness in ([(None, None)] if external else INTERNAL_WALLS):
            for side, operation in DIN_SIDE.items():
                for a, (frame, leaf, glass) in FINISHES.items():
                    name = pattern.format(a=a) + (f" Wand {wall}" if wall else "") + " " + side
                    t = new(f, "IfcDoorType", "type/" + name, name=name, predefined_type="DOOR")
                    t.OperationType = operation
                    t.Description = f"Rohbau {b:.3f} x {h:.3f} ab OKRF, Blatt auf OKFF (Schwelle {THRESHOLD:.2f})"
                    if wall:
                        t.Description += f", Umfassungszarge für Wand {wall}"
                    lining = dict(DOOR_LINING)
                    lining["threshold_thickness"] = THRESHOLD
                    if external:  # frame on the boundary masonry/insulation, no casing
                        lining["lining_depth"] = FRAME_DEPTH
                        lining["lining_offset"] = FRAME_OFFSET
                        lining["casing_thickness"] = 0.0
                        lining["casing_depth"] = 0.0
                    else:  # wrap-around frame in wall thickness, leaf on the opening side
                        lining["lining_depth"] = wall_thickness
                        lining["lining_to_panel_offset_y"] = round(
                            wall_thickness - (DOOR_LINING["lining_depth"] - DOOR_LINING["lining_to_panel_offset_y"]), 4)
                    lining["threshold_depth"] = lining["lining_depth"]   # threshold only in frame depth
                    lining["threshold_offset"] = lining["lining_offset"]  # Bonsai measures from the door origin, not the frame
                    if fanlight:
                        lining["transom_offset"], lining["transom_thickness"] = fanlight
                    data = {"door_type": operation, "overall_height": h, "overall_width": b,
                            "lining_properties": lining, "panel_properties": dict(DOOR_PANEL)}
                    rep = dict(
                        operation_type=operation, overall_height=h, overall_width=b,
                        lining_properties={_camel(k): v for k, v in lining.items()},
                        panel_properties={"PanelDepth": DOOR_PANEL["panel_depth"], "PanelWidth": DOOR_PANEL["panel_width_ratio"],
                                          "FrameDepth": 0.035, "FrameThickness": 0.035},
                    )
                    make = lambda c, part: api.geometry.add_door_representation(f, context=c, part_of_product=part, **rep)
                    represent(f, t, contexts, make)
                    parts = {"Lining": mat[frame], "Framing": mat[leaf]}
                    if fanlight:
                        parts["Glazing"] = mat[glass]
                    api.material.set_shape_aspect_constituents(f, element=t, context=body, materials=parts)
                    pset(f, t, "BBIM_Door", {"Data": f.createIfcText(json.dumps(data))}, "bbim/type/" + name)
                    pset(f, t, "Pset_DoorCommon", {"IsExternal": external}, "pset/type/" + name)
                    types.append(t)

    for pattern, b, h, partitioning, on_okff in WINDOWS:
        for a, (frame, sash, glass) in FINISHES.items():
            name = pattern.format(a=a)
            if on_okff:
                # Bonsai places IfcDoor at wall bottom + rl1 (= 0), everything else at + rl2
                # (sill) - opening.py, lines 314-318. French windows and side panels are
                # therefore door types; the representation stays that of a window, without
                # BBIM_Window, so Bonsai does not rebuild them as a parametric window.
                t = new(f, "IfcDoorType", "type/" + name, name=name, predefined_type="DOOR")
                t.OperationType = "NOTDEFINED" if name.startswith("Seitenteil") else (
                    "DOUBLE_DOOR_SINGLE_SWING" if partitioning == "DOUBLE_PANEL_VERTICAL" else "SINGLE_SWING_LEFT")
            else:
                t = new(f, "IfcWindowType", "type/" + name, name=name, predefined_type="WINDOW")
                t.PartitioningType = partitioning
            t.Description = f"Rohbau {b:.3f} x {h:.3f} ab OKRF" + (
                f", steht auf OKFF mit Unterbau {THRESHOLD:.2f}" if on_okff
                else f", Brüstung {SILL_DIFFERENT.get(pattern, SILL):.2f} ab OKRF")
            n = PANEL_COUNT[partitioning]
            lining_json = dict(WINDOW_LINING)
            lining_json["lining_depth"] = FRAME_DEPTH
            lining_json["lining_offset"] = FRAME_OFFSET
            hb = round(h - THRESHOLD, 4) if on_okff else h   # height of the window body
            if n > 1:  # as Bonsai's get_lining_kwargs for DOUBLE_PANEL_VERTICAL
                lining_json["mullion_thickness"] = MULLION_THICKNESS
                lining_json["first_mullion_offset"] = round(b / 2, 4)
            data = {"window_type": partitioning, "overall_height": hb, "overall_width": b,
                    "lining_properties": lining_json, "panel_properties": WINDOW_PANEL}
            lining = {_camel(k): v for k, v in lining_json.items()}
            lining.setdefault("MullionThickness", 0.0)
            lining.setdefault("FirstMullionOffset", 0.0)
            lining.update({"SecondMullionOffset": 0.0, "TransomThickness": 0.0,
                           "FirstTransomOffset": 0.0, "SecondTransomOffset": 0.0})
            panels = [{"FrameDepth": WINDOW_PANEL["frame_depth"][i], "FrameThickness": WINDOW_PANEL["frame_thickness"][i]}
                      for i in range(n)]

            def make(c, part, b=b, h=h, hb=hb, partitioning=partitioning, lining=lining, panels=panels, on_okff=on_okff):
                r = api.geometry.add_window_representation(
                    f, context=c, partition_type=partitioning, overall_height=hb, overall_width=b,
                    lining_properties=lining, panel_properties=panels, part_of_product=part)
                if on_okff:
                    lift(f, r, c, b, h, part, lining)
                return r
            represent(f, t, contexts, make)
            parts = {"Lining": mat[frame], "Framing": mat[sash], "Glazing": mat[glass]}
            if on_okff:
                parts["Unterbau"] = mat[SUBFRAME]
            api.material.set_shape_aspect_constituents(f, element=t, context=body, materials=parts)
            if on_okff:
                pset(f, t, "Pset_DoorCommon", {"IsExternal": True}, "pset/type/" + name)
            else:
                pset(f, t, "BBIM_Window", {"Data": f.createIfcText(json.dumps(data))}, "bbim/type/" + name)
                pset(f, t, "Pset_WindowCommon", {"IsExternal": True}, "pset/type/" + name)
            types.append(t)

    # Profiles
    sections = {}

    def section(pname, ifc_class, values):
        if pname not in sections:
            p = api.profile.add_parameterized_profile(f, ifc_class=ifc_class)
            p.ProfileName = pname
            for k, v in values.items():
                setattr(p, k, v)
            sections[pname] = p
        return sections[pname]

    def profile_type(name, ifc_class, predefined, material, prof):
        t = new(f, ifc_class, "type/" + name, name=name, predefined_type=predefined)
        pset_ = api.material.add_material_set(f, name=name, set_type="IfcMaterialProfileSet")
        api.material.add_profile(f, profile_set=pset_, material=mat[material], profile=prof)
        api.material.assign_material(f, products=[t], type="IfcMaterialProfileSet", material=pset_)
        pset(f, t, "Pset_" + ifc_class[3:-4] + "Common", {"LoadBearing": True}, "pset/type/" + name)
        types.append(t)

    for role, ifc_class, predefined, material, short, sizes in TIMBER_ROLES:
        for b, h in sizes:
            pname = f"{short} {b}/{h}"
            prof = section(pname, "IfcRectangleProfileDef",
                           {"XDim": round(b / 100, 4), "YDim": round(h / 100, 4)})
            profile_type(f"{role} {pname} {MATERIAL_SHORT[material]}", ifc_class, predefined, material, prof)
    for pname, (b, h, web, flange, r) in STEEL_SECTIONS.items():
        prof = section(pname, "IfcIShapeProfileDef", {
            "OverallWidth": round(b / 1000, 5), "OverallDepth": round(h / 1000, 5),
            "WebThickness": round(web / 1000, 5), "FlangeThickness": round(flange / 1000, 5),
            "FilletRadius": round(r / 1000, 5)})
        for role, ifc_class, predefined in STEEL_ROLES:
            profile_type(f"{role} {pname} {MATERIAL_SHORT[STEEL]}", ifc_class, predefined, STEEL, prof)

    for name, applicable, classes in ANNOTATION_TYPES:
        t = new(f, "IfcTypeProduct", "annot/" + name, name=name)
        t.ApplicableOccurrence = applicable
        pset(f, t, "EPset_Annotation", {"Classes": classes}, "pset/annot/" + name)
        types.append(t)

    api.project.assign_declaration(f, definitions=types, relating_context=library)

    # Relationships get a random GlobalId from the API - fix them here,
    # and bring lists into a fixed order.
    own = {gid(k) for k in _ASSIGNED}
    for e in f.by_type("IfcRoot"):
        if e.GlobalId not in own:
            e.GlobalId = gid(f"auto/{e.is_a()}/{e.id()}")
    # Under 0.9.1 assign_unit and assign_declaration create their lists in random
    # order - sort them afterwards.
    # Bonsai takes the FIRST storey of the list as the default storey
    # (tool/spatial.py, line 1683, guess_default_container) - so the entrance level
    # comes first, the others follow by elevation.
    entrance = {s[0] for s in STOREYS if s[3]}

    def order(x):
        is_entrance = x.is_a("IfcBuildingStorey") and x.Name in entrance
        return (not is_entrance, getattr(x, "Elevation", None) or 0.0, x.id())

    for r in f.by_type("IfcRelAggregates"):
        r.RelatedObjects = sorted(r.RelatedObjects, key=order)
    for r in f.by_type("IfcRelDeclares"):
        r.RelatedDefinitions = sorted(r.RelatedDefinitions, key=lambda x: x.id())
    for u in f.by_type("IfcUnitAssignment"):
        u.Units = sorted(u.Units, key=lambda x: x.id())

    f.header.file_name.time_stamp = TIMESTAMP
    f.header.file_name.name = "native_template.ifc"
    f.header.file_description.description = ("ViewDefinition [DesignTransferView]", f"Native IFC template {VERSION}")
    return f


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python build_template.py TARGET.ifc")
    model = build()
    model.write(sys.argv[1])
    print(f"written: {sys.argv[1]} ({len(list(model))} entities, version {VERSION})")
