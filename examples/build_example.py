# SPDX-FileCopyrightText: 2026 Andràs Marghescu and contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""
build_example.py - builds the example house from the native IFC template (IFC4).

Usage (no Blender needed, IfcOpenShell 0.9 only):
    python build_example.py  ../template/native_template.ifc  example_house.ifc

What it is:
  A deliberately plain, fictitious single-family house - ground floor, a converted
  attic with knee walls under a gable roof, a straight stair, a terrace - and a
  carport with steel columns. It has no location, no site terrain and
  no georeference.

  Its purpose is twofold: to show every family of types of the template in a sensible
  place, and to serve as a test model (drawings, line weights, hatching, schedules).
  At the end the script checks that every type family occurs at least once and lists
  the ones that do not (exit code 1).

  A "family" is a type name without its dimensions: "Stütze HEA 160 S235" belongs to the
  family "Stütze HEA S235". Doors are counted without their hinge side; for external and
  internal doors both hinge sides (DIN links, DIN rechts) have to occur. Internal doors
  keep their wall thickness ("Wand 17,5", "Wand 10", "Wand 15"). Annotation types (level
  markers) are left out of the check: the drawings below do not place any.

Drawings and sheets:
  The script also sets up a drawing set the way Bonsai stores one in the IFC: 19 drawings
  (cameras as IfcAnnotation DRAWING with EPset_Drawing), each with its document, and one
  sheet per drawing with layout and title block references. "E" is the design set (1:100,
  site plan 1:500), "W" the working set (1:50). Plans leave out floor slabs, floor
  build-ups and footings (EPset_Drawing.Exclude), so that the walls are cut, not the
  floor; sections and elevations leave out the drawing cameras.
  The SVG files themselves are not part of the IFC: Bonsai writes them when a drawing is
  created, and the layout of a sheet when the sheets are loaded and its drawings exist
  (see README.md).

How it is built:
  Everything is placed in absolute coordinates (m). The interior of the house is
  0.00-9.00 (x, east) by 0.00-7.00 (y, north), measured to the inner face of the
  masonry. The storeys are those of the template: EG with OKRF -0.15 / OKFF 0.00,
  OG with OKRF 2.85 / OKFF 3.00.
  Walls follow the rule of the template: masonry on the reference line, insulation to
  the left of the drawing direction, drawn clockwise. External masonry is butt-jointed:
  the west and east walls run through, north and south abut (layer priorities on
  IfcRelConnectsPathElements); the insulation is mitred.
  Doors and windows in external walls are placed from outside: origin on the outer face,
  turned by 180 degrees, so that the frame sits on the boundary masonry/insulation and
  doors open inwards.
  Roof, eaves, plinth and opening details as in a worked reference house
  (construction only): rafters with birdsmouths, verge rafters, foot purlins on a
  membrane, ETICS and render up to the rafter top, insulation per rafter bay, sub-frame
  insulation below French windows and doors, window sills, reveals, gutters and downpipes.
  Every element is an occurrence of a template type.
  The same script produces the same file byte for byte.
"""
import json
import math
import re
import sys
import uuid

import numpy as np
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.document
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.group
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
import ifcopenshell.guid
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
from ifcopenshell.util.data import Clipping

VERSION = "0.4.0"
TIMESTAMP = "2026-11-10T00:00:00"
NAME = "Musterhaus"

api = ifcopenshell.api

# ---------------------------------------------------------------------------
# DIMENSIONS (m) - maintained here
# ---------------------------------------------------------------------------
LX, LY = 9.00, 7.00          # interior, inner face of masonry
MW, WD = 0.24, 0.12          # masonry, insulation (external wall type)
AP, IP = 0.01, 0.015         # external render, internal plaster
EG, OG = -0.15, 2.85         # OKRF of the storeys
FB = 0.15                    # floor build-up: OKFF = OKRF + FB
EG_WALL = 2.80               # EG walls up to the underside of the floor slab
SLAB = 0.20
SOCKEL = 0.30                # plinth render up to here
KNEE = 1.00                  # knee wall above OKRF OG
PITCH = math.radians(40.0)
EAVE = 0.50                  # overhang beyond the insulation, eaves and verge
RIDGE_Y = LY / 2
SB, RAFTER_H = 0.08, 0.20    # Sparren KVH 8/20
RAFTER_CLEAR = 0.70          # clear distance between rafters, about
PURLIN_FOOT = 0.16           # Pfette KVH 12/16 on the knee wall, outer half of the masonry
RIDGE_B, RIDGE_H = 0.16, 0.24  # Pfette BSH 16/24
KERVE = 0.025                # birdsmouth, perpendicular to the rafter underside
BITUMEN = 0.003              # membrane below the foot purlin
GK = 0.0492                  # Dachschräge GK 2 x 12,5 total
COLLAR_BOTTOM = OG + 2.50    # Kehlbalken 8/16; the GK ceiling below them clears the window heads (2.41)
COLLAR_H = 0.16
GK_CEILING = 0.0492          # Decke GK 2 x 12,5 below the collar beams
OG_WALL = COLLAR_BOTTOM - GK_CEILING - OG   # OG partitions up to the ceiling
RIDGE_POSTS = (2.0, 7.0)     # x of the posts below the ridge purlin
RISER_COUNT = 17             # one straight flight; 0.99 m clear ahead of the arrival
TREAD = 0.26
STAIR_X, STAIR_Y = 4.175 + IP, 1.10    # along the plastered hall wall, clear of the door casing; arrives at y 5.26
STAIR_W = 1.00
CARPORT_X = LX + MW + WD + AP + 3.00   # west edge of the carport roof: 3 m from the render
# window sill as in the reference house: aluminium 2 mm, 4 cm beyond the render,
# 5 degrees, drip 2 cm, side upstands 1 cm
SILL_OUT, SILL_SLOPE, SILL_T, SILL_DRIP, SILL_UP = 0.04, math.radians(5.0), 0.002, 0.02, 0.01
FRAME_OFFSET, FRAME_DEPTH = 0.12, 0.08   # external frames: outer face on masonry/insulation
GUTTER_R, PIPE_R, WALL_T = 0.0765, 0.05, 0.0007

T, C, S = math.tan(PITCH), math.cos(PITCH), math.sin(PITCH)
OUT = MW + WD                                   # outer face of the insulation
Z_KNEE = OG + KNEE
KV = KERVE / C                                  # birdsmouth, plumb
Z_FOOT_TOP = Z_KNEE + BITUMEN + PURLIN_FOOT     # top of the foot purlins
Z_REF = Z_FOOT_TOP - KV                         # rafter underside above the outer masonry face
DSP = RAFTER_H / C                              # rafter depth, plumb


def z_under(y):
    """Underside of the rafters above plan point y (both roof sides)."""
    return Z_REF + (min(y, LY - y) + MW) * T


def z_top(y):
    return z_under(y) + DSP


Z_RIDGE_TOP = z_under(RIDGE_Y - RIDGE_B / 2) + KV   # top of the ridge purlin
COLLAR_TOP = COLLAR_BOTTOM + COLLAR_H


def rafter_lines():
    """Left edges of the rafters (x): verge rafter, rafter in front of the gable render,
    rafter at the inner face of the gable, rafters about 70 cm apart, the same at the east."""
    inner = (LX - SB) - SB
    fields = math.ceil((inner + SB) / (RAFTER_CLEAR + SB))
    clear = (inner - (fields - 1) * SB) / fields
    return ([-OUT - EAVE, -OUT - AP - SB, 0.0]
            + [SB + k * clear + (k - 1) * SB for k in range(1, fields)]
            + [LX - SB, LX + OUT + AP, LX + OUT + EAVE - SB])


# ---------------------------------------------------------------------------
# HELPERS - mechanics only from here
# ---------------------------------------------------------------------------
_NS = uuid.UUID("0b6a6c1e-5b9b-4c3a-9d53-7a4c2f0e8a11")
# recorded openings in world coordinates, cut through coverings as well:
# a, b (plan points), dir, z_in / z_out (z range on the inner / outer face or None), tol
OPENINGS = []


def combine_layers_fixed(self, layers, override_priorities):
    """IfcOpenShell 0.9 assigns into a namedtuple as soon as layer priorities are set
    (regenerate_wall_representation.py, combine_layers). Same logic, with _replace."""
    if override_priorities:
        for i, priority in enumerate(override_priorities[: len(layers)]):
            layers[i] = layers[i]._replace(priority=priority)
    if not layers:
        return []
    results = [layers.pop(0)]
    for layer in layers:
        if not layer.thickness:
            continue
        if layer.priority == results[-1].priority:
            results[-1] = results[-1]._replace(thickness=results[-1].thickness + layer.thickness)
        else:
            results.append(layer)
    return results


import importlib
_wallregen = importlib.import_module("ifcopenshell.api.geometry.regenerate_wall_representation")
_wallregen.Regenerator.combine_layers = combine_layers_fixed


def _placement(e):
    """Absolute placement matrix (get_placement in 0.9.1, get_local_placement in 0.9.0)."""
    p = ifcopenshell.util.placement
    return (getattr(p, "get_placement", None) or p.get_local_placement)(e.ObjectPlacement)


def frame(origin, x, z):
    """4x4 placement: local X and Z given, Y = Z x X (for walls: left of the direction)."""
    x = np.array(x, dtype=float)
    z = np.array(z, dtype=float)
    x /= np.linalg.norm(x)
    z /= np.linalg.norm(z)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, origin
    return m


def to_local(m, point, normal=None):
    inv = np.linalg.inv(m)
    p = (inv @ np.append(np.array(point, dtype=float), 1.0))[:3]
    if normal is None:
        return p
    return p, inv[:3, :3] @ np.array(normal, dtype=float)


def _ccw(pts):
    a = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


class Model:
    def __init__(self, path):
        self.f = ifcopenshell.open(path)
        f = self.f
        self.template_ids = {e.GlobalId for e in f.by_type("IfcRoot")}
        self.types = {t.Name: t for t in f.by_type("IfcTypeProduct")}
        self.storeys = {s.Name: s for s in f.by_type("IfcBuildingStorey")}
        get = ifcopenshell.util.representation.get_context
        self.body = get(f, "Model", "Body", "MODEL_VIEW")
        self.axis = get(f, "Plan", "Axis", "GRAPH_VIEW")
        if self.axis is None:
            self.axis = api.context.add_context(f, context_type="Plan", context_identifier="Axis",
                                                target_view="GRAPH_VIEW", parent=get(f, "Plan"))
        self.model_axis = get(f, "Model", "Axis", "GRAPH_VIEW") or api.context.add_context(
            f, context_type="Model", context_identifier="Axis", target_view="GRAPH_VIEW", parent=get(f, "Model"))
        self.walls = {}
        self.external = []      # openings in external walls, for reveals, sills and sub-frames
        self.used = []

    # ---- basics
    def element(self, ifc_class, name, type_name=None, storey="EG", predefined=None):
        f = self.f
        e = api.root.create_entity(f, ifc_class=ifc_class, name=name, predefined_type=predefined)
        if storey:
            api.spatial.assign_container(f, products=[e], relating_structure=self.storeys[storey])
        if type_name:
            api.type.assign_type(f, related_objects=[e], relating_type=self.types[type_name])
            self.used.append(type_name)
        return e

    def place(self, e, m):
        api.geometry.edit_object_placement(self.f, product=e, matrix=m, is_si=True)

    def thickness(self, e):
        return sum(l.LayerThickness for l in ifcopenshell.util.element.get_material(e, should_skip_usage=True).MaterialLayers)

    def layer_usage(self, e, direction, offset=0.0):
        usage = ifcopenshell.util.element.get_material(e)
        usage.LayerSetDirection = direction
        usage.DirectionSense = "POSITIVE"
        usage.OffsetFromReferenceLine = float(offset)

    def clip(self, e, m, planes):
        """Cut the body with half spaces given in world coordinates (normal = removed side)
        and register them in BBIM_Boolean, as geometry.clip_solid does, so that Bonsai
        keeps them when it regenerates the wall."""
        rep = ifcopenshell.util.representation.get_representation(e, "Model", "Body", "MODEL_VIEW")
        ids = []
        for point, normal in planes:
            p, n = to_local(m, point, normal)
            n = n / np.linalg.norm(n)
            item = rep.Items[0]
            result = Clipping(location=tuple(p), normal=tuple(n)).apply(self.f, item, 1.0)
            rep.Items = [result] + list(rep.Items[1:])
            ids.append(result.id())
        rep.RepresentationType = "Clipping"
        if ids:
            ps = api.pset.add_pset(self.f, product=e, name="BBIM_Boolean")
            api.pset.edit_pset(self.f, pset=ps, properties={"Data": json.dumps(ids)})

    # ---- free-form solids: profile (p, q) extruded along axis; q = axis x ref
    def extrusion(self, pts, origin, axis, ref, depth):
        f = self.f
        pts = _ccw([(float(a), float(b)) for a, b in pts])
        curve = f.createIfcPolyline([f.createIfcCartesianPoint(p) for p in pts + [pts[0]]])
        prof = f.createIfcArbitraryClosedProfileDef("AREA", None, curve)
        pos = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint([float(v) for v in origin]),
                                          f.createIfcDirection([float(v) for v in axis]),
                                          f.createIfcDirection([float(v) for v in ref]))
        return f.createIfcExtrudedAreaSolid(prof, pos, f.createIfcDirection((0.0, 0.0, 1.0)), float(depth))

    def box(self, x0, x1, y0, y1, z0, z1):
        return self.extrusion([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (0, 0, z0), (0, 0, 1), (1, 0, 0), z1 - z0)

    def along_x(self, prof_yz, x0, x1):
        """Profile (y, z), extruded from x0 to x1 (world or local coordinates)."""
        return self.extrusion(prof_yz, (x0, 0, 0), (1, 0, 0), (0, 1, 0), x1 - x0)

    def along_y(self, prof_xz, y0, y1):
        return self.extrusion(prof_xz, (0, y1, 0), (0, -1, 0), (1, 0, 0), y1 - y0)

    def solid(self, ifc_class, name, type_name, storey, m, items, predefined=None, usage=None):
        """Element with a body of its own solids in the local system m."""
        e = self.element(ifc_class, name, type_name, storey, predefined)
        self.place(e, m)
        kind = "AdvancedSweptSolid" if any(i.is_a("IfcSweptDiskSolid") for i in items) else "SweptSolid"
        rep = self.f.createIfcShapeRepresentation(self.body, "Body", kind, items)
        api.geometry.assign_representation(self.f, product=e, representation=rep)
        if usage:
            self.layer_usage(e, *usage)
        return e

    def world_void(self, host, name, item, predefined="OPENING"):
        """Opening element in world coordinates (identity placement)."""
        op = api.root.create_entity(self.f, ifc_class="IfcOpeningElement", name=name, predefined_type=predefined)
        self.place(op, np.eye(4))
        api.geometry.assign_representation(self.f, product=op, representation=self.f.createIfcShapeRepresentation(
            self.body, "Body", "SweptSolid", [item]))
        api.feature.add_feature(self.f, feature=op, element=host)
        return op

    def covers(self, wall, coverings):
        """IfcRelCoversBldgElements: the coverings belong to the wall."""
        self.f.createIfcRelCoversBldgElements(ifcopenshell.guid.new(), None, None, None,
                                              self.walls[wall]["e"], coverings)

    # ---- walls and vertical coverings
    def wall(self, name, type_name, p1, p2, z0, height, storey):
        e = self.element("IfcWall", name, type_name, storey)
        p1, p2 = np.array(p1, dtype=float), np.array(p2, dtype=float)
        length = float(np.linalg.norm(p2 - p1))
        m = frame((p1[0], p1[1], z0), (*(p2 - p1), 0.0), (0, 0, 1))
        self.place(e, m)
        f = self.f
        api.geometry.assign_representation(f, product=e, representation=api.geometry.add_axis_representation(
            f, context=self.axis, axis=[(0.0, 0.0), (length, 0.0)]))
        api.geometry.assign_representation(f, product=e, representation=api.geometry.add_wall_representation(
            f, context=self.body, length=length, height=height, thickness=self.thickness(e)))
        self.walls[name] = dict(e=e, m=m, length=length, height=height, p1=p1, p2=p2, z0=z0, storey=storey,
                                type=type_name, d=(p2 - p1) / length)
        return e

    def u_of(self, wall, point):
        w = self.walls[wall]
        return float(np.dot(np.array(point[:2], dtype=float) - w["p1"], w["d"]))

    def connect(self, a, b, priorities=None):
        rel = api.geometry.connect_wall(self.f, wall1=self.walls[a]["e"], wall2=self.walls[b]["e"])
        if priorities:
            rel.RelatingPriorities, rel.RelatedPriorities = priorities
        return rel

    def tee(self, a, b):
        api.geometry.connect_wall(self.f, wall1=self.walls[a]["e"], wall2=self.walls[b]["e"], is_atpath=True)

    def regenerate(self, names):
        for n in names:
            w = self.walls[n]
            api.geometry.regenerate_wall_representation(self.f, wall=w["e"], length=w["length"], height=w["height"])
            w["m"] = _placement(w["e"])

    def cover(self, name, type_name, p1, p2, z0, z1, storey, clips=(), side="out"):
        """Vertical covering, layers to the left of p1 -> p2 (AXIS2); cut by the recorded
        openings on the same face (side "out": render, "in": plaster)."""
        e = self.element("IfcCovering", name, type_name, storey)
        self.layer_usage(e, "AXIS2")
        p1, p2 = np.array(p1, dtype=float), np.array(p2, dtype=float)
        length = float(np.linalg.norm(p2 - p1))
        m = frame((p1[0], p1[1], z0), (*(p2 - p1), 0.0), (0, 0, 1))
        self.place(e, m)
        th = self.thickness(e)
        api.geometry.assign_representation(self.f, product=e, representation=api.geometry.add_wall_representation(
            self.f, context=self.body, length=length, height=z1 - z0, thickness=th))
        if clips:
            self.clip(e, m, clips)
        d = (p2 - p1) / length
        for o in OPENINGS:
            zr = o["z_" + side]
            if zr is None:
                continue
            u = sorted(float(np.dot(np.array(q) - p1, d)) for q in (o["a"], o["b"]))
            v = np.array(o["a"]) - p1
            dist = abs(float(d[0] * v[1] - d[1] * v[0]))
            parallel = abs(abs(float(np.dot(d, o["dir"]))) - 1.0) < 1e-6
            lo, hi = max(u[0], 0.0), min(u[1], length)
            za, zb = max(zr[0], z0), min(zr[1], z1)
            if parallel and dist < o.get("tol", 0.6) and hi - lo > 0.01 and zb - za > 0.01:
                self.void(e, m, lo, hi, za - z0, zb - z0, th)
        return e

    def void(self, host, m, u0, u1, v0, v1, th, name="Öffnung"):
        op = api.root.create_entity(self.f, ifc_class="IfcOpeningElement", name=name)
        om = m @ frame((u0, -0.05, v0), (1, 0, 0), (0, 0, 1))
        self.place(op, om)
        api.geometry.assign_representation(self.f, product=op, representation=api.geometry.add_wall_representation(
            self.f, context=self.body, length=u1 - u0, height=v1 - v0, thickness=th + 0.10))
        api.feature.add_feature(self.f, feature=op, element=host)
        return op

    # ---- doors and windows
    def opening(self, wall, type_name, u0, face="out", face_offset=0.0):
        """Door or window in a wall. u0: distance from the wall start to the near edge of the
        opening. face "out": placed from the +Y face (outer face of an external wall), turned
        by 180 degrees - doors open towards -Y. face "in": placed on the -Y face, doors open
        towards +Y. face_offset: outer face lies further out (covering on the wall)."""
        w = self.walls[wall]
        t = self.types[type_name]
        b, h = (float(v) for v in re.match(r"Rohbau ([\d.]+) x ([\d.]+)", t.Description).groups())
        sill = 0.0 if t.is_a("IfcDoorType") else SILLS.get(type_name.split(" ", 3)[-1], 1.15)
        th = self.thickness(w["e"])
        cls = "IfcDoor" if t.is_a("IfcDoorType") else "IfcWindow"
        el = self.element(cls, type_name, type_name, storey=None)
        api.spatial.assign_container(self.f, products=[el], relating_structure=ifcopenshell.util.element.get_container(w["e"]))
        m = w["m"]
        if face == "out":
            local = frame((u0 + b, th + face_offset, sill), (-1, 0, 0), (0, 0, 1))
        else:
            local = frame((u0, -face_offset, sill), (1, 0, 0), (0, 0, 1))
        self.place(el, m @ local)
        op = self.void(w["e"], m, u0, u0 + b, sill, sill + h, th)
        api.feature.add_filling(self.f, opening=op, element=el)
        d = w["d"]
        z = w["z0"] + sill
        o = dict(a=tuple(w["p1"] + d * u0), b=tuple(w["p1"] + d * (u0 + b)), dir=d,
                 z_in=(z, z + h), z_out=(z, z + h))
        OPENINGS.append(o)
        if w["type"].startswith("Außenwand"):
            kind = ("window" if cls == "IfcWindow" else "french" if type_name.startswith("Fenstertür") else "door")
            o.update(wall=wall, u0=u0, u1=u0 + b, zu=z, zo=z + h, kind=kind,
                     label=f"{wall} {sum(1 for x in self.external if x['wall'] == wall) + 1}")
            self.external.append(o)
        return el

    def opening_group(self, wall, type_names, u0, face="out", face_offset=0.0):
        """Coupled elements in one opening (door with side panel): one void, the frames side
        by side along the wall, recorded as one external opening."""
        n0 = len(OPENINGS)
        u, els = u0, []
        for t in type_names:
            els.append(self.opening(wall, t, u, face, face_offset))
            u += float(re.match(r"Rohbau ([\d.]+)", self.types[t].Description).group(1))
        group = OPENINGS[n0:]
        del OPENINGS[n0:]
        for o in group:
            if o in self.external:
                self.external.remove(o)
        # one void for all: remove the single voids, fill one common opening
        w = self.walls[wall]
        for el in els:
            op = el.FillsVoids[0].RelatingOpeningElement
            api.feature.remove_filling(self.f, element=el)
            api.feature.remove_feature(self.f, feature=op)
        z0, z1 = min(o["z_in"][0] for o in group), max(o["z_in"][1] for o in group)
        op = self.void(w["e"], w["m"], u0, u, z0 - w["z0"], z1 - w["z0"], self.thickness(w["e"]))
        for el in els:
            api.feature.add_filling(self.f, opening=op, element=el)
        o = dict(group[0])
        o.update(b=tuple(w["p1"] + w["d"] * u), z_in=(z0, z1), z_out=(z0, z1))
        OPENINGS.append(o)
        if "kind" in o:
            o.update(u1=u, zo=z1, kind="door")
            self.external.append(o)
        return els

    def railing(self, name, type_name, storey, path, posts=None, post_floor=None):
        """Railing generated from a line: posts, handrail, bottom rail and vertical bars from
        the parameters of the type (EPset_Railing). path: points (x, y, z) of the reference
        line (floor, or pitch line of a stair); posts: plan points, otherwise at most
        PostSpacingMax apart; post_floor(x, y, z): bottom of a post (default z)."""
        f = self.f
        p = ifcopenshell.util.element.get_pset(self.types[type_name], "EPset_Railing")
        H, ps, smax = p["Height"], p["PostSize"], p["PostSpacingMax"]
        rh, rb, hb, rbar, clear = p["HandrailDiameter"] / 2, p["BottomRailDiameter"] / 2, p["BottomRailHeight"], \
            p["BarDiameter"] / 2, p["BarClearMax"]
        pts = [np.array(q, dtype=float) for q in path]
        P = lambda q: f.createIfcCartesianPoint([float(v) for v in q])
        disk = lambda line, r: f.createIfcSweptDiskSolid(f.createIfcPolyline([P(q) for q in line]), r, None, None, None)
        items = [disk([q + (0, 0, H - rh) for q in pts], rh), disk([q + (0, 0, hb) for q in pts], rb)]
        # stations along the line: (plan position, z on the line, segment direction)
        segs = [(a, b) for a, b in zip(pts, pts[1:])]

        def at(xy):
            for a, b in segs:
                d = b[:2] - a[:2]
                t = float(np.dot(xy - a[:2], d) / np.dot(d, d))
                if -1e-6 <= t <= 1 + 1e-6 and np.linalg.norm(a[:2] + d * t - xy) < 1e-6:
                    return a + (b - a) * t, d / np.linalg.norm(d)
            raise ValueError("post not on the railing line")
        if posts is None:
            stations = []
            for a, b in segs:
                n = max(1, math.ceil(float(np.linalg.norm(b[:2] - a[:2])) / smax))
                stations += [a[:2] + (b[:2] - a[:2]) * k / n for k in range(n)]
            stations.append(pts[-1][:2])
        else:
            stations = [np.array(q, dtype=float) for q in posts]
        for xy in stations:
            q, d = at(xy)
            zb = post_floor(q[0], q[1], q[2]) if post_floor else q[2]
            n = np.array((-d[1], d[0]))
            c = [xy + d * sx * ps / 2 + n * sy * ps / 2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            items.append(self.extrusion([tuple(v) for v in c], (0, 0, zb), (0, 0, 1), (1, 0, 0), q[2] + H - rh - zb))
        # bars between neighbouring posts (and from the line ends to the first and last post)
        at_post = [round(self._chain(pts, s), 6) for s in stations]
        marks = sorted({0.0, *at_post, round(self._chain(pts, pts[-1][:2]), 6)})
        for s0, s1 in zip(marks, marks[1:]):
            a0 = s0 + (ps / 2 if s0 in at_post else 0.0)
            a1 = s1 - (ps / 2 if s1 in at_post else 0.0)
            free = a1 - a0
            m = max(0, math.ceil((free - clear) / (clear + 2 * rbar)))
            gap = (free - m * 2 * rbar) / (m + 1)
            for i in range(m):
                q = self._point(pts, a0 + gap * (i + 1) + 2 * rbar * i + rbar)
                items.append(disk([q + (0, 0, hb), q + (0, 0, H - rh)], rbar))
        e = self.element("IfcRailing", name, type_name, storey, "GUARDRAIL")
        self.place(e, np.eye(4))
        api.geometry.assign_representation(f, product=e, representation=f.createIfcShapeRepresentation(
            self.body, "Body", "SolidModel", items))
        api.geometry.assign_representation(f, product=e, representation=f.createIfcShapeRepresentation(
            self.model_axis, "Axis", "Curve3D", [f.createIfcPolyline([P(q) for q in pts])]))
        return e

    @staticmethod
    def _chain(pts, xy):
        """Plan distance along the line up to the plan point xy (on the line)."""
        s = 0.0
        for a, b in zip(pts, pts[1:]):
            d = b[:2] - a[:2]
            L = float(np.linalg.norm(d))
            t = float(np.dot(np.array(xy) - a[:2], d) / (L * L))
            if -1e-6 <= t <= 1 + 1e-6 and np.linalg.norm(a[:2] + d * t - xy) < 1e-6:
                return s + t * L
            s += L
        raise ValueError("point not on the line")

    @staticmethod
    def _point(pts, s):
        for a, b in zip(pts, pts[1:]):
            L = float(np.linalg.norm(b[:2] - a[:2]))
            if s <= L + 1e-9:
                return a + (b - a) * (s / L)
            s -= L
        return pts[-1]

    # ---- layered slabs and horizontal coverings
    def layered(self, ifc_class, name, type_name, polygon, m, storey, clips=(), holes=()):
        """Slab or covering with layers bottom to top (AXIS3). polygon in the local XY plane
        of m; holes: (x0, y0, x1, y1) in the same plane."""
        e = self.element(ifc_class, name, type_name, storey)
        self.layer_usage(e, "AXIS3")
        self.place(e, m)
        depth = self.thickness(e)
        api.geometry.assign_representation(self.f, product=e, representation=api.geometry.add_slab_representation(
            self.f, context=self.body, depth=depth, polyline=[tuple(p) for p in polygon]))
        if clips:
            self.clip(e, m, clips)
        for x0, y0, x1, y1 in holes:
            op = api.root.create_entity(self.f, ifc_class="IfcOpeningElement", name="Aussparung")
            self.place(op, m @ frame((x0, y0, -0.05), (1, 0, 0), (0, 0, 1)))
            api.geometry.assign_representation(self.f, product=op, representation=api.geometry.add_wall_representation(
                self.f, context=self.body, length=x1 - x0, height=depth + 0.10, thickness=y1 - y0))
            api.feature.add_feature(self.f, feature=op, element=e)
        return e

    def flat(self, ifc_class, name, type_name, x0, y0, x1, y1, z, storey, holes=()):
        m = frame((0.0, 0.0, z), (1, 0, 0), (0, 0, 1))
        poly = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return self.layered(ifc_class, name, type_name, poly, m, storey, holes=holes)

    # ---- profiles (members, beams, columns, footings)
    def profiled(self, ifc_class, name, type_name, origin, axis, x_dir, length, storey, clips=()):
        """Extrusion of the type's profile along local Z = axis, centred on it."""
        e = self.element(ifc_class, name, type_name, storey)
        usage = ifcopenshell.util.element.get_material(e)
        profile = usage.ForProfileSet.MaterialProfiles[0].Profile
        m = frame(origin, x_dir, axis)
        self.place(e, m)
        api.geometry.assign_representation(self.f, product=e, representation=api.geometry.add_profile_representation(
            self.f, context=self.body, profile=profile, depth=length, cardinal_point=5))
        if clips:
            self.clip(e, m, clips)
        return e

    # ---- stair flight: stepped side profile, extruded across the width
    def flight(self, name, type_name, origin, risers, riser_h, tread, width, base_drop, storey):
        e = self.element("IfcStairFlight", name, type_name, storey, predefined="STRAIGHT")
        waist = 0.16
        cos_p = tread / math.hypot(tread, riser_h)
        pts = [(0.0, -base_drop), (0.0, riser_h)]
        for i in range(1, risers):               # the last riser is the edge of the landing or slab
            pts += [(i * tread, i * riser_h)] + ([(i * tread, (i + 1) * riser_h)] if i < risers - 1 else [])
        u_end = (risers - 1) * tread
        under = lambda u: u * riser_h / tread - waist / cos_p
        pts.append((u_end, under(u_end)))
        u_start = (-base_drop + waist / cos_p) * tread / riser_h
        pts.append((max(u_start, 0.0), -base_drop))
        pts.append(pts[0])                       # closed curve
        f = self.f
        points = f.createIfcCartesianPointList2D([[float(a), float(b)] for a, b in pts])
        curve = f.createIfcIndexedPolyCurve(points, None, False)
        prof = f.createIfcArbitraryClosedProfileDef("AREA", None, curve)
        pos = f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)))
        solid = f.createIfcExtrudedAreaSolid(prof, pos, f.createIfcDirection((0.0, 0.0, 1.0)), float(width))
        rep = f.createIfcShapeRepresentation(self.body, "Body", "SweptSolid", [solid])
        api.geometry.assign_representation(f, product=e, representation=rep)
        # local X = run (+y), local Y = up, local Z = across (+x)
        self.place(e, frame(origin, (0, 1, 0), (1, 0, 0)))
        ps = api.pset.add_pset(f, product=e, name="Pset_StairFlightCommon")
        api.pset.edit_pset(f, pset=ps, properties={"NumberOfRiser": risers, "NumberOfTreads": risers - 1,
                                                   "RiserHeight": round(riser_h, 4), "TreadLength": tread})
        return e, u_start


# window sills from OKRF where they differ from 1.15 (key: dimensions in the type name)
SILLS = {"126 × 138,5": 0.875, "151 × 138,5": 0.875, "63,5 × 87,5": 1.385, "76 × 100": 1.26}


# ---------------------------------------------------------------------------
# THE HOUSE
# ---------------------------------------------------------------------------
def build(template):
    md = Model(template)
    f = md.f
    OPENINGS.clear()
    AW, KS, TB, AB = ("Außenwand MW 24 + WDVS 12", "Innenwand KS 17,5", "Trockenbauwand 10",
                      "Abseitenwand Holzständer 15")
    ring = [("West", (0, 0), (0, LY)), ("Nord", (0, LY), (LX, LY)), ("Ost", (LX, LY), (LX, 0)), ("Süd", (LX, 0), (0, 0))]
    run_through = {"West", "Ost"}                       # masonry runs through, north/south abut
    n_s, n_n = (0.0, -S, C), (0.0, S, C)                # up-normals of the two roof sides
    top_plane = lambda north: ((0.0, LY + MW if north else -MW, Z_REF + DSP), n_n if north else n_s)
    lining_under = lambda north: ((0.0, LY + MW if north else -MW, Z_REF - GK / C), n_n if north else n_s)
    roof_tops = [top_plane(False), top_plane(True)]
    linings = [lining_under(False), lining_under(True)]

    # ---- ground floor walls
    for n, a, b in ring:
        md.wall(f"AW {n} EG", AW, a, b, EG, EG_WALL, "EG")
    for (n1, _, _), (n2, _, _) in zip(ring, ring[1:] + ring[:1]):
        md.connect(f"AW {n1} EG", f"AW {n2} EG",
                   ([10, 20] if n1 in run_through else [5, 20], [10, 20] if n2 in run_through else [5, 20]))
    md.wall("IW Flur EG", KS, (4.0, LY), (4.0, 0), EG, EG_WALL, "EG")       # x 4.000-4.175
    md.wall("TW Flur EG", TB, (6.0, LY), (6.0, 0), EG, EG_WALL, "EG")       # x 6.000-6.100
    md.wall("TW WC EG", TB, (6.1, 1.6), (LX, 1.6), EG, EG_WALL, "EG")       # y 1.600-1.700
    md.wall("TW Küche EG", TB, (6.1, 3.5), (LX, 3.5), EG, EG_WALL, "EG")    # y 3.500-3.600
    for a, b in (("IW Flur EG", "AW Nord EG"), ("IW Flur EG", "AW Süd EG"), ("TW Flur EG", "AW Nord EG"),
                 ("TW Flur EG", "AW Süd EG"), ("TW WC EG", "AW Ost EG"), ("TW Küche EG", "AW Ost EG")):
        md.tee(a, b)
    md.regenerate([n for n in md.walls if n.endswith(" EG")])

    # ---- upper floor walls: the gables run through, the knee walls abut
    gable_h = z_top(RIDGE_Y) + 0.4 - OG
    for n, a, b in ring:
        md.wall(f"AW {n} OG", AW, a, b, OG, KNEE if n in ("Nord", "Süd") else gable_h, "OG")
    for (n1, _, _), (n2, _, _) in zip(ring, ring[1:] + ring[:1]):
        md.connect(f"AW {n1} OG", f"AW {n2} OG",
                   ([10, 20] if n1 in run_through else [5, 20], [10, 20] if n2 in run_through else [5, 20]))
    md.wall("Abseite Süd OG", AB, (0, 0.6), (LX, 0.6), OG, 1.9, "OG")        # y 0.60-0.75
    md.wall("Abseite Nord OG", AB, (LX, 6.4), (0, 6.4), OG, 1.9, "OG")       # y 6.25-6.40
    # gallery: the stair hole in the middle, a walkway on either side, so that every room
    # is reached outside the hole and where the roof leaves full height
    md.wall("Wand Flur OG", AB, (3.15, 6.25), (3.15, 0.75), OG, OG_WALL, "OG")  # x 3.15-3.30
    md.wall("TW Flur OG", TB, (6.1, 6.25), (6.1, 0.75), OG, OG_WALL, "OG")      # x 6.10-6.20
    md.wall("TW Arbeiten OG", TB, (0, 3.6), (3.15, 3.6), OG, OG_WALL, "OG")     # y 3.60-3.70
    md.wall("TW Bad OG", TB, (6.2, 3.6), (LX, 3.6), OG, OG_WALL, "OG")          # y 3.60-3.70
    md.regenerate([n for n in md.walls if n.endswith(" OG")])
    for n in ("West", "Ost"):                            # gables: masonry and ETICS up to the rafter top
        w = md.walls[f"AW {n} OG"]
        md.clip(w["e"], w["m"], roof_tops)
    for n in ("Abseite Süd OG", "Abseite Nord OG", "Wand Flur OG", "TW Flur OG", "TW Arbeiten OG", "TW Bad OG"):
        w = md.walls[n]
        md.clip(w["e"], w["m"], linings)

    # ---- doors and windows, ground floor (u0 from the start of the wall)
    # front door coupled with its side panel: one opening, one frame line (no pier between)
    md.opening_group("AW Süd EG", ["Seitenteil fest Holz 51 × 213", "Außentür Holz 113,5 × 213 DIN rechts"], LX - 5.91)
    md.opening("AW Süd EG", "Fenstertür 2-flg. Holz 201 × 211", LX - 3.01)
    md.opening("AW Süd EG", "Fenster 1-flg. Kunststoff 63,5 × 87,5", LX - 7.835)
    md.opening("AW West EG", "Fenstertür 2-flg. Kunststoff 201 × 211", 4.5)
    md.opening("AW Nord EG", "Fenster 2-flg. Holz 126 × 126", 1.4)
    md.opening("AW Nord EG", "Fenster 2-flg. Kunststoff 126 × 126", 6.8)
    md.opening("AW Ost EG", "Außentür Holz mit Oberlicht 113,5 × 263 DIN links", LY - 6.01)  # kitchen, y 4.875-6.01
    md.opening("AW Nord EG", "Außentür Kunststoff mit Oberlicht 113,5 × 263 DIN rechts", 4.6)  # back door, hall
    md.opening_group("AW Ost EG", ["Seitenteil fest Kunststoff 51 × 213", "Außentür Kunststoff 113,5 × 213 DIN links"],
                     LY - 3.41)                                                     # utility room, y 1.765-3.41
    # masonry plastered on both faces: the frame (wall + 2 x plaster) stands out by the plaster
    md.opening("IW Flur EG", "Innentür Holz 88,5 × 213 Wand 17,5 DIN rechts", LY - 6.885, face="out", face_offset=IP)
    md.opening("IW Flur EG", "Innentür Kunststoff 88,5 × 213 Wand 17,5 DIN links", LY - 1.0, face="out", face_offset=IP)
    md.opening("TW Flur EG", "Innentür Kunststoff 88,5 × 213 Wand 10 DIN links", LY - 6.885, face="in")
    md.opening("TW Flur EG", "Innentür Kunststoff 76 × 213 Wand 10 DIN rechts", LY - 2.76, face="in")
    md.opening("TW Flur EG", "Innentür Holz 76 × 213 Wand 10 DIN links", LY - 1.36, face="in")
    # upper floor: all room doors outside the stair hole
    md.opening("AW West OG", "Fenster 2-flg. Holz 151 × 126", 1.5)
    md.opening("AW West OG", "Fenstertür Holz 88,5 × 226", 4.2)
    md.opening("AW Ost OG", "Fenster 1-flg. Holz 101 × 126", LY - 2.61)
    md.opening("AW Ost OG", "Fenstertür Kunststoff 88,5 × 226", LY - 4.785)
    md.opening("Wand Flur OG", "Innentür Holz 76 × 213 Wand 15 DIN links", 6.25 - 3.16, face="out")      # y 2.40-3.16
    md.opening("Wand Flur OG", "Innentür Kunststoff 76 × 213 Wand 15 DIN rechts", 6.25 - 5.16, face="out")  # y 4.40-5.16
    md.opening("TW Flur OG", "Innentür Holz 88,5 × 213 Wand 10 DIN links", 6.25 - 3.285, face="in")        # y 2.40-3.285
    md.opening("TW Flur OG", "Innentür Kunststoff 88,5 × 213 Wand 10 DIN rechts", 6.25 - 5.285, face="in")  # y 4.40-5.285

    # ---- stair geometry (needed for the slab hole)
    rise = (OG + FB - (EG + FB)) / RISER_COUNT               # OKFF EG 0.00 to OKFF OG 3.00
    y_top = STAIR_Y + (RISER_COUNT - 1) * TREAD               # last riser = edge of the slab plaster
    hole = (4.175, STAIR_Y + 0.80, STAIR_X + STAIR_W + IP, y_top + IP)   # structural hole, headroom 2.00
    x_hole_in = (hole[0] + IP, hole[2] - IP)                  # x 4.19 .. 5.19 = stair width

    # ---- foundation, slabs, floors
    # Outer edge of masonry = outer edge of slab and strip footings; perimeter insulation
    # and ETICS form one plane (outer face -0.36).
    c = MW - 0.25                                          # footing axis, 0.50 wide, flush outside
    for n, a, b in (("Süd", (-MW, -c), (LX + MW, -c)), ("Nord", (-MW, LY + c), (LX + MW, LY + c)),
                    ("West", (-c, 0.26), (-c, LY - 0.26)), ("Ost", (LX + c, 0.26), (LX + c, LY - 0.26))):
        a, b = np.array(a), np.array(b)
        md.profiled("IfcFooting", f"Frostschürze {n}", "Streifenfundament 50/80", (a[0], a[1], -0.80),
                    (*(b - a), 0.0), _across(b - a), float(np.linalg.norm(b - a)), "EG")
    md.flat("IfcCovering", "Dämmung unter Bodenplatte", "Dämmung unter Bodenplatte 12", 0.26, 0.26, LX - 0.26, LY - 0.26, -0.52, "EG")
    md.flat("IfcSlab", "Bodenplatte", "Bodenplatte STB 25", -MW, -MW, LX + MW, LY + MW, EG - 0.25, "EG")
    md.flat("IfcSlab", "Decke über EG", "Decke STB 20", -MW, -MW, LX + MW, LY + MW, EG + EG_WALL, "EG", holes=[hole])

    # rooms: (name, storey, box inside the structure, floor finish, plastered sides, extra floor holes)
    post_holes = [(x - 0.06, RIDGE_Y - 0.06, x + 0.06, RIDGE_Y + 0.06) for x in RIDGE_POSTS]
    rooms = [("Wohnen", "EG", (0, 0, 4.0, LY), "Parkett", "SWNE", ()),
             ("Flur EG", "EG", (4.175, 0, 6.0, LY), "Fliesen", "SWN", ()),
             ("WC", "EG", (6.1, 0, LX, 1.6), "Fliesen", "SE", ()),
             ("HWR", "EG", (6.1, 1.7, LX, 3.5), "Estrich", "E", ()),
             ("Küche", "EG", (6.1, 3.6, LX, LY), "Fliesen", "NE", ()),
             ("Schlafen", "OG", (0, 0.75, 3.15, 3.6), "Parkett", "W", (post_holes[0],)),
             ("Arbeiten", "OG", (0, 3.7, 3.15, 6.25), "Parkett", "W", ()),
             ("Flur OG", "OG", (3.30, 0.75, 6.1, 6.25), "Parkett", "",
              ((x_hole_in[0], hole[1] + IP, x_hole_in[1], hole[3] - IP),)),
             ("Kind", "OG", (6.2, 0.75, LX, 3.6), "Parkett", "E", (post_holes[1],)),
             ("Bad", "OG", (6.2, 3.7, LX, 6.25), "Fliesen", "E", ())]

    # ---- stair: one straight flight (17 risers), as an assembly of the type "Treppe STB gerade".
    # Two flights with a landing would not leave a landing at the top in front of the knee
    # partition (author: "der Treppenaustritt endet vor einer Wand").
    f1, _ = md.flight("Treppenlauf", "Treppenlauf STB 16", (STAIR_X, STAIR_Y, EG + FB), RISER_COUNT, rise,
                      TREAD, STAIR_W, FB, "EG")
    stair = md.element("IfcStair", "Treppe EG-OG", "Treppe STB gerade", storey="EG", predefined="STRAIGHT_RUN_STAIR")
    api.aggregate.assign_object(f, products=[f1], relating_object=stair)
    # entrance landing in front of the front door (Podest STB 16), top 2 cm below OKFF
    md.flat("IfcSlab", "Eingangspodest", "Podest STB 16", 4.0, -OUT - AP - 1.20, 6.20, -OUT - AP, -0.18, "EG")
    # the floor build-up of the hall stops where the first flight lifts off the slab
    cos_p = TREAD / math.hypot(TREAD, rise)
    stair_foot = (STAIR_X, STAIR_Y, STAIR_X + STAIR_W, STAIR_Y + 0.16 / cos_p * TREAD / rise)

    for name, storey, (x0, y0, x1, y1), finish_, sides, holes in rooms:
        z0 = EG if storey == "EG" else OG
        fx0, fy0 = x0 + (IP if "W" in sides else 0), y0 + (IP if "S" in sides else 0)
        fx1, fy1 = x1 - (IP if "E" in sides else 0), y1 - (IP if "N" in sides else 0)
        extra = (stair_foot,) if name == "Flur EG" else ()
        md.flat("IfcCovering", f"Fußboden {name}", f"Fußbodenaufbau 15 {finish_}", fx0, fy0, fx1, fy1, z0, storey,
                holes=tuple(holes) + extra)

    # ---- terrace (with a hole for the downpipe)
    pipe_x = (-OUT + 0.20, LX + OUT - 0.20)
    pipe_off = OUT + AP + 0.03 + PIPE_R                       # downpipe axis from the masonry inner face
    md.flat("IfcSlab", "Terrasse", "Terrassenbelag Holz 4", -OUT, -3.36, 4.0, -OUT - AP, -0.10, "EG",
            holes=[(pipe_x[0] - 0.06, -pipe_off - 0.06, pipe_x[0] + 0.06, -pipe_off + 0.06)])

    # ---- roof structure (OG): purlins, posts, rafters with birdsmouths, collars
    eave_s, eave_n = -OUT - EAVE, LY + OUT + EAVE
    x_end0, x_end1 = -OUT - EAVE, LX + OUT + EAVE
    purlins = []      # (name, y0, y1, z0, z1) for birdsmouths and the openings in the gables
    for n, y0 in (("Süd", -MW), ("Nord", LY + MW - 0.12)):
        md.profiled("IfcMember", f"Fußpfette {n}", "Pfette KVH 12/16 C24", (x_end0, y0 + 0.06, Z_FOOT_TOP - PURLIN_FOOT / 2),
                    (1, 0, 0), (0, 1, 0), x_end1 - x_end0, "OG")
        purlins.append((f"Fußpfette {n}", y0, y0 + 0.12, Z_FOOT_TOP - PURLIN_FOOT, Z_FOOT_TOP))
        md.flat("IfcCovering", f"Bitumenbahn Fußpfette {n}", "Bitumenbahn 0,3", -MW, y0, LX + MW, y0 + 0.12, Z_KNEE, "OG")
    md.profiled("IfcMember", "Firstpfette", "Pfette BSH 16/24 GL24h", (x_end0, RIDGE_Y, Z_RIDGE_TOP - RIDGE_H / 2),
                (1, 0, 0), (0, 1, 0), x_end1 - x_end0, "OG")
    purlins.append(("Firstpfette", RIDGE_Y - RIDGE_B / 2, RIDGE_Y + RIDGE_B / 2, Z_RIDGE_TOP - RIDGE_H, Z_RIDGE_TOP))
    z_purlin_bottom = Z_RIDGE_TOP - RIDGE_H
    for i, xc in enumerate(RIDGE_POSTS):
        md.profiled("IfcColumn", f"Stütze Firstpfette {i + 1}", "Stütze KVH 12/12 C24", (xc, RIDGE_Y, OG),
                    (0, 0, 1), (1, 0, 0), z_purlin_bottom - OG, "OG")
        for side in (-1, 1):                     # braces 45 degrees, cut at the post and the purlin
            leg = 0.55
            d = np.array((side, 0.0, 1.0)) / math.sqrt(2)
            start = np.array((xc + side * 0.06, RIDGE_Y, z_purlin_bottom - leg)) - d * 0.1
            md.profiled("IfcMember", f"Kopfband {i + 1}{'a' if side < 0 else 'b'}", "Kopfband KVH 10/10 C24",
                        start, d, (0, 1, 0), leg * math.sqrt(2) + 0.2, "OG",
                        clips=[((xc + side * 0.06, 0.0, 0.0), (-side, 0.0, 0.0)), ((0.0, 0.0, z_purlin_bottom), (0.0, 0.0, 1.0))])

    lines = rafter_lines()
    inner = range(2, len(lines) - 2)                     # rafters over the heated house
    y_collar_end = (COLLAR_TOP - Z_REF - DSP) / T - MW   # collar top meets the rafter top
    y_collar_in = (COLLAR_BOTTOM - Z_REF) / T - MW       # collar bottom meets the rafter underside
    y_collar_out = (COLLAR_TOP - Z_REF) / T - MW         # collar top meets the rafter underside
    collars = []
    for i, x0 in enumerate(lines):
        xc = x0 + SB / 2
        label = ("Flugsparren West" if i == 0 else "Flugsparren Ost" if i == len(lines) - 1 else f"Sparren {i}")
        for north in (False, True):
            d = np.array((0.0, -C, S)) if north else np.array((0.0, C, S))
            n = np.array(n_n if north else n_s)
            y_start = eave_n + 0.4 if north else eave_s - 0.4
            start = np.array((xc, y_start, z_under(y_start))) + n * RAFTER_H / 2
            length = (abs(RIDGE_Y - y_start) + 0.4) / C
            eave = ((0.0, eave_n, 0.0), (0.0, 1.0, 0.0)) if north else ((0.0, eave_s, 0.0), (0.0, -1.0, 0.0))
            ridge = ((0.0, RIDGE_Y, 0.0), (0.0, -1.0, 0.0)) if north else ((0.0, RIDGE_Y, 0.0), (0.0, 1.0, 0.0))
            r = md.profiled("IfcMember", f"{label} {'N' if north else 'S'}", "Sparren KVH 8/20 C24",
                            start, d, (1, 0, 0) if north else (-1, 0, 0), length, "OG", clips=[eave, ridge])
            for pn, py0, py1, pz0, pz1 in purlins:          # birdsmouth = cross-section of the purlin
                if (pn == "Firstpfette") or (pn.endswith("Nord") == north):
                    md.world_void(r, f"Kerve {r.Name} {pn}", md.box(x0 - 0.001, x0 + SB + 0.001, py0, py1, pz1 - 0.30, pz1),
                                  "RECESS")
        if i in inner and (i - inner[0]) % 2 == 0:         # collar beams on every second pair, beside them
            side = -1 if i == inner[-1] else 1
            cx = xc + side * (SB / 2 + 0.04)
            md.profiled("IfcMember", f"Kehlbalken {len(collars) + 1}", "Kehlbalken KVH 8/16 C24",
                        (cx, y_collar_end, COLLAR_BOTTOM + COLLAR_H / 2), (0, 1, 0), (-1, 0, 0), LY - 2 * y_collar_end, "OG")
            collars.append((cx - 0.04, cx + 0.04))
            assert all(abs(cx - p) > 0.15 for p in RIDGE_POSTS), "collar beside a ridge post"

    # insulation between the rafters, one piece per bay and roof side (Mineralwolle 20)
    xk = KV / T
    rp0, rp1 = RIDGE_Y - RIDGE_B / 2, RIDGE_Y
    prof_s = [(-MW, Z_FOOT_TOP), (-MW + xk, Z_FOOT_TOP), (rp0, z_under(rp0)), (rp0, Z_RIDGE_TOP),
              (rp0 + xk, Z_RIDGE_TOP), (rp1, z_under(rp1)), (rp1, z_top(rp1)), (-MW, z_top(-MW))]
    for north in (False, True):
        for k, i in enumerate(list(inner)[:-1]):
            bx0, bx1 = lines[i] + SB, lines[i + 1]
            if north:
                m = frame((bx1, LY + MW, z_under(-MW)), (-1, 0, 0), n_n)
                pts = [to_local(m, (bx1, LY - y, z))[1:] for y, z in prof_s]
            else:
                m = frame((bx0, -MW, z_under(-MW)), (1, 0, 0), n_s)
                pts = [to_local(m, (bx0, y, z))[1:] for y, z in prof_s]
            e = md.solid("IfcCovering", f"Zwischensparrendämmung {'Nord' if north else 'Süd'} {k + 1:02d}",
                         "Zwischensparrendämmung 20", "OG", m, [md.along_x(pts, 0.0, bx1 - bx0)],
                         predefined="INSULATION", usage=("AXIS3",))
            for cx0, cx1 in collars:
                if bx0 - 1e-6 <= cx0 and cx1 <= bx1 + 1e-6:
                    ya, yb = (LY - y_collar_out, LY - y_collar_end) if north else (y_collar_end, y_collar_out)
                    md.world_void(e, f"Kehlbalken {e.Name}", md.box(cx0, cx1, ya - 0.001, yb + 0.001,
                                                                   COLLAR_BOTTOM - 0.001, COLLAR_TOP + 0.001), "RECESS")

    # ---- roof build-up on the rafters: house part up to the render, overhangs in planed boarding
    for north in (False, True):
        y0 = eave_n if north else eave_s
        x0 = x_end1 if north else x_end0
        origin = (x0, y0, z_top(y0))
        m = frame(origin, (-1, 0, 0) if north else (1, 0, 0), n_n if north else n_s)
        loc = lambda x, y, m=m: to_local(m, (x, y, z_top(y)))[:2]
        ridge = [((0.0, RIDGE_Y, 0.0), (0.0, -1.0, 0.0) if north else (0.0, 1.0, 0.0))]
        y_wall = LY + OUT + AP if north else -OUT - AP
        y_over = RIDGE_Y + (-0.4 if north else 0.4)
        xa, xb = -OUT - AP, LX + OUT + AP
        side = "Nord" if north else "Süd"
        for name, typ, (u0, v0, u1, v1) in (
                (f"Dach {side}", "Dachaufbau über Sparren Holzfaser 5", (xa, y_wall, xb, y_over)),
                (f"Dachüberstand Traufe {side}", "Dachaufbau über Sparren Sichtschalung", (x_end0, y0, x_end1, y_wall)),
                (f"Dachüberstand Ortgang West {side}", "Dachaufbau über Sparren Sichtschalung", (x_end0, y_wall, xa, y_over)),
                (f"Dachüberstand Ortgang Ost {side}", "Dachaufbau über Sparren Sichtschalung", (xb, y_wall, x_end1, y_over))):
            poly = [loc(u0, v0), loc(u1, v0), loc(u1, v1), loc(u0, v1)]
            if np.cross(np.append(poly[1] - poly[0], 0), np.append(poly[2] - poly[1], 0))[2] < 0:
                poly = poly[::-1]
            md.layered("IfcSlab", name, typ, poly, m, "OG", clips=ridge)
        # sloped lining of the room below the rafters, from the knee partition to the collars
        y_from = 6.25 if north else 0.75
        y_to = y_collar_in                                # the lining ends below the collars
        y_to = LY - y_to if north else y_to
        o = (LX if north else 0.0, y_from, z_under(y_from) - GK / C)
        mg = frame(o, (-1, 0, 0) if north else (1, 0, 0), n_n if north else n_s)
        v = abs(y_to - y_from) / C
        md.layered("IfcCovering", f"Dachschräge {side}", "Dachschräge GK 2 × 12,5", [(0, 0), (LX, 0), (LX, v), (0, v)], mg, "OG")

    # ---- purlins through the gables: openings in masonry and ETICS, recorded for the render
    for g in ("West", "Ost"):
        w = md.walls[f"AW {g} OG"]
        xg = -OUT if g == "West" else LX + OUT
        for pn, py0, py1, pz0, pz1 in purlins:
            zb = Z_KNEE if pn.startswith("Fuß") else pz0          # foot purlin with its membrane
            u = sorted((md.u_of(f"AW {g} OG", (0, py0)), md.u_of(f"AW {g} OG", (0, py1))))
            md.void(w["e"], w["m"], u[0], u[1], zb - OG, pz1 - OG, md.thickness(w["e"]), name=f"Durchgang {pn}")
            OPENINGS.append(dict(a=(xg, py0), b=(xg, py1), dir=np.array((0.0, 1.0)), z_in=None,
                                 z_out=(zb, pz1), tol=0.05))

    # ---- ETICS at the eaves, from the knee wall up to the rafter top; mitred at the corners,
    # the rafters run through 
    rafters_in = [lines[i] for i in inner]
    eave_etics = {}
    for north in (False, True):
        sgn = 1 if north else -1
        y_in = LY + MW if north else -MW                  # outer face of the masonry
        y_out = y_in + sgn * WD
        if north:
            m = frame((-OUT, y_in, Z_KNEE), (1, 0, 0), (0, 0, 1))
        else:
            m = frame((LX + OUT, y_in, Z_KNEE), (-1, 0, 0), (0, 0, 1))
        prof = [(0.0, 0.0), (WD, 0.0), (WD, z_top(y_out) - Z_KNEE), (0.0, z_top(y_in) - Z_KNEE)]
        e = md.solid("IfcCovering", f"WDVS Traufe {'Nord' if north else 'Süd'}", "WDVS 12", "OG", m,
                     [md.along_x(prof, 0.0, LX + 2 * OUT)], predefined="CLADDING", usage=("AXIS2",))
        r2 = 1 / math.sqrt(2)
        md.clip(e, m, [((-MW, y_in, 0.0), (-r2, -sgn * r2, 0.0)), ((LX + MW, y_in, 0.0), (r2, -sgn * r2, 0.0))])
        eave_etics[north] = e
        lo, hi = (y_in - 0.01, y_out + 0.01) if north else (y_out - 0.01, y_in + 0.01)
        for x0 in rafters_in:
            md.world_void(e, f"Sparren {x0:.3f} durch {e.Name}",
                          md.along_x([(lo, z_under(lo)), (hi, z_under(hi)), (hi, z_top(hi)), (lo, z_top(lo))], x0, x0 + SB))

    # ---- details at the external openings (reference house):
    # sub-frame insulation below French windows and doors, window sills, external and
    # internal reveals. Local system of the wall: x along, y outwards (0 = inner face of
    # the masonry), z from the wall base.
    y_r, y_w, y_a = MW, OUT, OUT + AP                       # frame outer face, ETICS, render
    y_fi = MW - FRAME_DEPTH                                 # frame inner face
    tan_s = math.tan(SILL_SLOPE)
    for o in md.external:
        w = md.walls[o["wall"]]
        m, base, storey = w["m"], w["z0"], w["storey"]
        u0, u1, zu, zo = o["u0"], o["u1"], o["zu"] - w["z0"], o["zo"] - w["z0"]
        kind, label = o["kind"], o["label"]
        zb = zu + (FB if kind in ("french", "door") else 0.0)   # bottom of the frame / OKFF
        sheet = kind in ("window", "french")
        top = lambda y: zb - tan_s * (y - y_r)                  # sill top
        under = lambda y: top(y) - SILL_T
        parts = []
        if kind in ("french", "door"):                         # ETICS in front of the sub-frame
            prof = [(y_r, zu), (y_w, zu), (y_w, under(y_w) if sheet else zb), (y_r, under(y_r) if sheet else zb)]
            parts.append(md.solid("IfcCovering", f"WDVS Unterbau {label}", "WDVS 12", storey, m,
                                  [md.along_x(prof, u0, u1)], "CLADDING", usage=("AXIS2", y_r)))
        elif sheet:                                            # ETICS below the sill, in its slope
            yv = y_w + 0.01
            op = api.root.create_entity(f, ifc_class="IfcOpeningElement", name=f"Aussparung Fensterblech {label}",
                                        predefined_type="RECESS")
            md.place(op, m)
            api.geometry.assign_representation(f, product=op, representation=f.createIfcShapeRepresentation(
                md.body, "Body", "SweptSolid", [md.along_x([(y_r, zb + 0.001), (y_r, under(y_r)), (yv, under(yv)),
                                                            (yv, zb + 0.001)], u0 - 0.001, u1 + 0.001)]))
            api.feature.add_feature(f, feature=op, element=w["e"])
        if sheet:
            y1 = y_a + SILL_OUT
            prof = [(y_r, top(y_r)), (y1, top(y1)), (y1, top(y1) - SILL_DRIP), (y1 - SILL_T, top(y1) - SILL_DRIP),
                    (y1 - SILL_T, under(y1 - SILL_T)), (y_r, under(y_r))]
            up = [(y_r, top(y_r)), (y1, top(y1)), (y1, top(y1) + SILL_UP), (y_r, top(y_r) + SILL_UP)]
            e = md.solid("IfcCovering", f"Fensterblech {label}", "Fensterblech Aluminium", storey, m,
                         [md.along_x(prof, u0, u1), md.along_x(up, u0, u0 + AP), md.along_x(up, u1 - AP, u1)],
                         "USERDEFINED")
            e.ObjectType = "Fensterblech"
            parts.append(e)
        o["z_out"] = (base + (under(y_a) - 0.001 if sheet else zb), o["zo"])
        # external reveals: render from the facade to the frame, plinth render below +0.30
        c0, k0 = (zb + SILL_UP, tan_s) if sheet else (zb, 0.0)
        bottom = lambda y: c0 - k0 * (y - y_r)
        sockel = SOCKEL - base
        pieces = [("Sturz", "Außenputz 1", md.along_x([(y_r, zo - AP), (y_a, zo - AP), (y_a, zo), (y_r, zo)], u0, u1),
                   ("AXIS3", zo - AP))]
        if bottom(y_r) < sockel - 0.001 and zo - AP > sockel + 0.001:
            segments = [(None, sockel), (sockel, zo - AP)]
        else:
            segments = [(None, zo - AP)]
        for z1, z2 in segments:
            lowest = z1 is None
            for tag, a, b in (("links", u0, u0 + AP), ("rechts", u1 - AP, u1)):
                prof = ([(y_r, bottom(y_r)), (y_a, bottom(y_a)), (y_a, z2), (y_r, z2)] if lowest
                        else [(y_r, z1), (y_a, z1), (y_a, z2), (y_r, z2)])
                typ = "Sockelputz 1" if z2 <= sockel + 1e-6 else "Außenputz 1"
                pieces.append((f"{tag} {'unten' if lowest else 'oben'}", typ, md.along_x(prof, a, b), ("AXIS1", a)))
        for tag, typ, item, usage in pieces:
            parts.append(md.solid("IfcCovering", f"{typ.split()[0]} Laibung {label} {tag}", typ, storey, m, [item],
                                  "CLADDING", usage=usage))
        # internal reveals: plaster from the plastered face to the frame
        zi = zb if kind != "window" else zu
        for tag, prof, a, b, usage in (
                ("links", [(-IP, zi), (y_fi, zi), (y_fi, zo - IP), (-IP, zo - IP)], u0, u0 + IP, ("AXIS1", u0)),
                ("rechts", [(-IP, zi), (y_fi, zi), (y_fi, zo - IP), (-IP, zo - IP)], u1 - IP, u1, ("AXIS1", u1 - IP)),
                ("Sturz", [(-IP, zo - IP), (y_fi, zo - IP), (y_fi, zo), (-IP, zo)], u0, u1, ("AXIS3", zo - IP))):
            parts.append(md.solid("IfcCovering", f"Laibungsputz {label} {tag}", "Innenputz 1,5", storey, m,
                                  [md.along_x(prof, a, b)], "CLADDING", usage=usage))
        md.covers(o["wall"], parts)
        if kind in ("french", "door"):                          # floor build-up up to the frame
            left = np.array((-w["d"][1], w["d"][0]))
            q = [w["p1"] + w["d"] * u + left * y for u in (u0 + IP, u1 - IP) for y in (-IP, y_fi)]
            xs, ys = [p[0] for p in q], [p[1] for p in q]
            inside = w["p1"] + w["d"] * (u0 + u1) / 2 - left * 0.5
            fin = next(r[3] for r in rooms if r[1] == storey and r[2][0] <= inside[0] <= r[2][2] and r[2][1] <= inside[1] <= r[2][3])
            md.flat("IfcCovering", f"Fußboden Laibung {label}", f"Fußbodenaufbau 15 {fin}", min(xs), min(ys), max(xs), max(ys),
                    w["z0"], storey)

    # ---- render: plinth up to +0.30, render above, up to the rafter top; eave render with
    # the rafters running through, gable render with the purlins
    for n, a, b in (("Süd", (LX + OUT + AP, -OUT), (-OUT - AP, -OUT)), ("West", (-OUT, -OUT), (-OUT, LY + OUT)),
                    ("Nord", (-OUT - AP, LY + OUT), (LX + OUT + AP, LY + OUT)), ("Ost", (LX + OUT, LY + OUT), (LX + OUT, -OUT))):
        md.cover(f"Sockelputz {n}", "Sockelputz 1", a, b, EG, SOCKEL, "EG")
        e = md.cover(f"Außenputz {n}", "Außenputz 1", a, b, SOCKEL, z_top(RIDGE_Y) + 0.4, "EG", clips=roof_tops)
        if n in ("Süd", "Nord"):
            north = n == "Nord"
            lo, hi = (LY + OUT - 0.01, LY + OUT + AP + 0.01) if north else (-OUT - AP - 0.01, -OUT + 0.01)
            for x0 in rafters_in:
                md.world_void(e, f"Sparren {x0:.3f} durch {e.Name}",
                              md.along_x([(lo, z_under(lo)), (hi, z_under(hi)), (hi, z_top(hi)), (lo, z_top(lo))], x0, x0 + SB))
    for n, a, b in (("Süd", (LX + OUT, -MW), (-OUT, -MW)), ("West", (-MW, -MW), (-MW, LY + MW)),
                    ("Nord", (-OUT, LY + MW), (LX + OUT, LY + MW)), ("Ost", (LX + MW, LY + MW), (LX + MW, -MW))):
        md.cover(f"Perimeterdämmung {n}", "Perimeterdämmung 12", a, b, -1.20, EG, "EG")

    # ---- ETICS on the edge of the floor slab: the external walls end below and start above it
    for n, a, b in (("Süd", (LX + MW + WD, -MW), (-MW - WD, -MW)), ("West", (-MW, -MW), (-MW, LY + MW)),
                    ("Nord", (-MW - WD, LY + MW), (LX + MW + WD, LY + MW)), ("Ost", (LX + MW, LY + MW), (LX + MW, -MW))):
        md.cover(f"WDVS Deckenstirn {n}", "WDVS 12", a, b, EG + EG_WALL, OG, "EG")

    # ---- internal plaster on masonry and sand-lime walls, rooms and stair hole
    for name, storey, (x0, y0, x1, y1), finish_, sides, holes in rooms:
        z0, z1 = (EG, EG + EG_WALL) if storey == "EG" else (OG, OG + OG_WALL)
        clips = linings if storey == "OG" else ()
        ya = y0 + (IP if "S" in sides else 0)
        yb = y1 - (IP if "N" in sides else 0)
        for s, p1, p2 in (("S", (x0, y0), (x1, y0)), ("N", (x1, y1), (x0, y1)),
                          ("W", (x0, yb), (x0, ya)), ("E", (x1, ya), (x1, yb))):
            if s in sides:
                md.cover(f"Innenputz {name} {s}", "Innenputz 1,5", p1, p2, z0, z1, storey, clips=clips, side="in")
    hx0, hy0, hx1, hy1 = hole
    for s, p1, p2 in (("S", (hx0, hy0), (hx1, hy0)), ("N", (hx1, hy1), (hx0, hy1)),
                      ("W", (hx0, hy1 - IP), (hx0, hy0 + IP)), ("E", (hx1, hy0 + IP), (hx1, hy1 - IP))):
        md.cover(f"Innenputz Treppenloch {s}", "Innenputz 1,5", p1, p2, EG + EG_WALL, OG, "EG", side="in")

    # ---- ceiling below the collar beams (Kehlbalkenlage), from lining to lining
    md.flat("IfcCovering", "Decke Kehlbalken", "Decke GK 2 × 12,5", 0.0, y_collar_in, LX, LY - y_collar_in,
            COLLAR_BOTTOM - GK_CEILING, "OG", holes=post_holes)

    # ---- railings, each generated from a line (its axis): stair, stair hole, French windows OG
    z_nose = lambda y: (EG + FB) + rise + (y - STAIR_Y) * rise / TREAD        # pitch line through the nosings
    x_r = STAIR_X + STAIR_W - 0.03
    tread_posts = [(x_r, STAIR_Y + (k - 0.5) * TREAD) for k in (1, 6, 11, 16)]
    tread_top = lambda x, y, z: (EG + FB) + (min(int((y - STAIR_Y) / TREAD), RISER_COUNT - 2) + 1) * rise
    md.railing("Geländer Treppe", "Geländer Stahl 90", "EG",
               [(x_r, STAIR_Y + 0.03, z_nose(STAIR_Y + 0.03)), (x_r, y_top - 0.05, z_nose(y_top - 0.05))],
               posts=tread_posts, post_floor=tread_top)
    zf = OG + FB
    xw, xe, ys = x_hole_in[0] - 0.03, x_hole_in[1] + 0.03, hole[1] + IP - 0.03
    md.railing("Geländer Treppenloch", "Geländer Stahl 90", "OG",
               [(xw, y_top + 0.03, zf), (xw, ys, zf), (xe, ys, zf), (xe, y_top + 0.03, zf)])
    for o in md.external:
        w = md.walls[o["wall"]]
        if o["kind"] == "french" and w["storey"] == "OG":
            zb = o["zu"] + FB
            q = [w["p1"] + w["d"] * u + np.array((-w["d"][1], w["d"][0])) * 0.30
                 for u in (o["u0"] + AP + 0.03, o["u1"] - AP - 0.03)]
            md.railing(f"Geländer {o['label']}", "Geländer Stahl 90", "OG", [(*q[0], zb), (*q[1], zb)],
                       post_floor=lambda x, y, z: z + 0.03)

    # ---- gutters and downpipes (reference house): half-round gutter in front of
    # the rafter heads, just below the boarding; downpipes 20 cm from the corners, 3 cm
    # in front of the render, down to the ground at -0.15
    steps = 24
    for north in (False, True):
        sgn = 1 if north else -1
        y_head = eave_n if north else eave_s
        yc = y_head + sgn * (GUTTER_R + 0.005)
        zr = z_top(y_head) - 0.02
        arc = lambda r: [(yc + r * math.cos(math.pi + math.pi * k / steps), zr + r * math.sin(math.pi + math.pi * k / steps))
                         for k in range(steps + 1)]
        side = "Nord" if north else "Süd"
        md.solid("IfcPipeSegment", f"Dachrinne {side}", "Dachrinne halbrund NG 333 Kupfer", "OG", np.eye(4),
                 [md.along_x(arc(GUTTER_R) + arc(GUTTER_R - WALL_T)[::-1], x_end0, x_end1)], "GUTTER")
        y_pipe = LY + pipe_off if north else -pipe_off
        for corner, xp in (("West", pipe_x[0]), ("Ost", pipe_x[1])):
            z1 = zr - GUTTER_R - 0.10
            path = [(xp, yc, zr - GUTTER_R), (xp, yc, z1), (xp, y_pipe, z1 - abs(y_pipe - yc)), (xp, y_pipe, EG)]
            curve = f.createIfcPolyline([f.createIfcCartesianPoint([float(v) for v in p]) for p in path])
            md.solid("IfcPipeSegment", f"Fallrohr {side} {corner}", "Fallrohr DN 100 Kupfer", "EG", np.eye(4),
                     [f.createIfcSweptDiskSolid(curve, PIPE_R, PIPE_R - WALL_T, None, None)], "RIGIDSEGMENT")

    # ---- carport (EG), 3 m east of the house
    dx = CARPORT_X - 9.8
    cols = {-0.8: "HEA 160", 2.1: "IPE 160", 5.0: "HEB 160"}
    for y, prof in cols.items():
        for x in (10.2 + dx, 12.8 + dx):
            md.profiled("IfcFooting", f"Einzelfundament {x:.2f}/{y}", "Einzelfundament 60/60", (x, y, EG - 0.80),
                        (0, 0, 1), (1, 0, 0), 0.80, "EG")
            md.profiled("IfcColumn", f"Stütze Carport {x:.2f}/{y}", f"Stütze {prof} S235", (x, y, EG),
                        (0, 0, 1), (1, 0, 0), 2.60 - EG, "EG")
    md.profiled("IfcBeam", "Träger Carport West", "Träger HEA 160 S235", (10.2 + dx, -1.0, 2.60 + 0.076),
                (0, 1, 0), (-1, 0, 0), 6.2, "EG")
    md.profiled("IfcBeam", "Träger Carport Ost", "Träger HEB 160 S235", (12.8 + dx, -1.0, 2.60 + 0.08),
                (0, 1, 0), (-1, 0, 0), 6.2, "EG")
    md.profiled("IfcBeam", "Träger Carport Mitte", "Träger IPE 160 S235", (10.28 + dx, 2.1, 2.60 + 0.08),
                (1, 0, 0), (0, 1, 0), 2.44, "EG")
    joists = [round(float(v), 2) for v in np.arange(-0.95, 4.70, 0.80)] + [5.25]
    for i, y in enumerate(joists):
        edge = i in (0, len(joists) - 1)
        md.profiled("IfcBeam", f"Balken Carport {i + 1}", "Balken BSH 10/20 GL24h" if edge else "Balken KVH 8/20 C24",
                    (9.9 + dx, float(y), 2.76 + 0.10), (1, 0, 0), (0, 1, 0), 3.2, "EG")
    md.flat("IfcSlab", "Dach Carport", "Dachaufbau 35", 9.8 + dx, -1.1, 13.2 + dx, 5.4, 2.96, "EG")

    drawing_set(md)
    finish(md)
    return md


# ---------------------------------------------------------------------------
# DRAWING SET - as Bonsai keeps it in the IFC (cameras, documents, sheets)
# ---------------------------------------------------------------------------
# Bonsai's default resources, relative to the IFC; Bonsai copies them from its data dir
# into the project when the first drawing is created (scripts/install_style.py puts
# din.css there).
RESOURCES = {
    "Stylesheet": "drawings/assets/default.css",
    "Markers": "drawings/assets/markers.svg",
    "Symbols": "drawings/assets/symbols.svg",
    "Patterns": "drawings/assets/patterns.svg",
    "ShadingStyles": "drawings/assets/shading_styles.json",
}
PLAN_EXCLUDE = ('IfcSlab, PredefinedType="BASESLAB" + IfcSlab, PredefinedType="FLOOR" + '
                'IfcCovering, PredefinedType="FLOORING" + IfcCovering, PredefinedType="INSULATION" + IfcFooting')
CAMERA_EXCLUDE = 'IfcAnnotation, ObjectType="DRAWING"'
PLAN_CUT = 1.60              # camera above OKRF of the storey, as Bonsai places a plan
VIEW_CENTRE = (7.6, 2.2)     # house and carport
TITLEBLOCK = {"E-01": "DIN_A4_hoch", "E": "DIN_A3_quer", "W": "DIN_A2_quer"}


def drawing_views():
    """The 19 drawings: (name, target view, scale, camera location, camera Z axis, camera X
    axis, box (x, y, z, dx, dy, dz) in camera coordinates, Exclude, GlobalReferencing).
    The camera looks along its -Z; the box is its view volume."""
    cx, cy = VIEW_CENTRE
    plan_box = (-12.0, -8.0, -2.0, 24.0, 16.0, 2.0)
    views = []
    for prefix, scale in (("E", 100), ("W", 50)):
        if prefix == "E":
            views.append(("E Lageplan", "PLAN_VIEW", 500, (0.0, 0.0, 30.0), (0, 0, 1), (1, 0, 0),
                          (-40.0, -30.0, -40.0, 80.0, 60.0, 40.0), None, True))
        for storey, z in (("KG", -3.15), ("EG", EG), ("OG", OG), ("DG", 5.85)):
            views.append((f"{prefix} Grundriss {storey}", "PLAN_VIEW", scale, (cx, cy, round(z + PLAN_CUT, 3)),
                          (0, 0, 1), (1, 0, 0), plan_box, PLAN_EXCLUDE, True))
        # across the ridge, looking east, through the stair
        views.append((f"{prefix} Schnitt A-A", "SECTION_VIEW", scale, (4.7, 3.2, 3.0), (-1, 0, 0), (0, -1, 0),
                      (-10.0, -8.0, -20.0, 20.0, 16.0, 20.0), CAMERA_EXCLUDE, prefix == "E"))
        for side, loc, axis, ref in (("Nord", (cx, 20.0, 3.0), (0, 1, 0), (-1, 0, 0)),
                                     ("Ost", (20.0, cy, 3.0), (1, 0, 0), (0, 1, 0)),
                                     ("Süd", (cx, -20.0, 3.0), (0, -1, 0), (1, 0, 0)),
                                     ("West", (-20.0, cy, 3.0), (-1, 0, 0), (0, -1, 0))):
            views.append((f"{prefix} Ansicht {side}", "ELEVATION_VIEW", scale, loc, axis, ref,
                          (-12.0, -8.0, -40.0, 24.0, 16.0, 40.0), CAMERA_EXCLUDE, False))
    return views


def _sorted_documents(f):
    """add_information collects the documents of a parent in a set - sort them."""
    for rel in f.by_type("IfcDocumentInformationRelationship"):
        rel.RelatedDocuments = sorted(rel.RelatedDocuments, key=lambda x: x.id())


def drawing_set(md):
    f = md.f
    project = f.by_type("IfcProject")[0]
    doc = api.document
    parent_doc = doc.add_information(f)
    doc.edit_information(f, information=parent_doc,
                         attributes={"Identification": "DRAWINGS", "Name": "DRAWINGS", "Scope": "DRAWINGS"})
    parent_group = api.group.add_group(f, name="DRAWINGS")
    parent_group.ObjectType = "DRAWINGS"
    groups, drawings = [], []
    for name, target, scale, loc, axis, ref, box, exclude, global_ref in drawing_views():
        e = api.root.create_entity(f, ifc_class="IfcAnnotation", name=name)
        e.ObjectType = "DRAWING"
        api.geometry.edit_object_placement(f, product=e, matrix=frame(loc, ref, axis), is_si=True)
        x, y, z, dx, dy, dz = box
        block = f.createIfcBlock(f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((x, y, z))), dx, dy, dz)
        rep = f.createIfcShapeRepresentation(md.body, "Body", "CSG", [f.createIfcCsgSolid(block)])
        api.geometry.assign_representation(f, product=e, representation=rep)
        group = api.group.add_group(f, name=name)
        group.ObjectType = "DRAWING"
        api.group.assign_group(f, products=[e], group=group)
        groups.append(group)
        props = {"TargetView": target, "Scale": f"1/{scale}", "HumanScale": f"1:{scale}",
                 "HasUnderlay": False, "HasLinework": True, "HasAnnotation": True,
                 "GlobalReferencing": global_ref, **RESOURCES, "CurrentShadingStyle": "Blender Default"}
        if exclude:
            props["Exclude"] = exclude
        pset = api.pset.add_pset(f, product=e, name="EPset_Drawing")
        api.pset.edit_pset(f, pset=pset, properties=props)
        info = doc.add_information(f, parent=parent_doc)
        doc.edit_information(f, information=info, attributes={"Identification": "X", "Name": name, "Scope": "DRAWING"})
        reference = doc.add_reference(f, information=info)
        doc.edit_reference(f, reference=reference, attributes={"Location": f"drawings/{name}.svg"})
        doc.assign_document(f, products=[e], document=reference)
        drawings.append(name)
    api.group.assign_group(f, products=groups, group=parent_group)

    # one sheet per drawing: E-01 site plan, E-02 ... design set, W-01 ... working set
    counters = {"E": 0, "W": 0}
    for name in drawings:
        prefix, title = name.split(" ", 1)
        counters[prefix] += 1
        ident = f"{prefix}-{counters[prefix]:02d}"
        sheet = doc.add_information(f)
        doc.edit_information(f, information=sheet, attributes={"Identification": ident, "Name": title, "Scope": "SHEET"})
        block_name = TITLEBLOCK.get(ident, TITLEBLOCK[prefix])
        for location, description, identification in (
                (f"layouts/{ident} - {title}.svg", "LAYOUT", "X"),
                (f"layouts/titleblocks/{block_name}.svg", "TITLEBLOCK", "X"),
                (f"drawings/{name}.svg", "DRAWING", "1")):
            r = doc.add_reference(f, information=sheet)
            doc.edit_reference(f, reference=r, attributes={"Identification": identification, "Location": location,
                                                           "Description": description})
    _sorted_documents(f)


def _across(direction):
    """Local X for a horizontal axis: horizontal and perpendicular to it (profile width)."""
    d = np.array((*direction[:2], 0.0), dtype=float)
    d /= np.linalg.norm(d)
    return (-d[1], d[0], 0.0)


def finish(md):
    f = md.f
    project = f.by_type("IfcProject")[0]
    project.Name = NAME
    project.Description = f"Example house built from the native IFC template, version {VERSION}"
    own = md.template_ids
    ns = uuid.UUID(int=_NS.int)
    for e in f.by_type("IfcRoot"):
        if e.GlobalId not in own:
            e.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(ns, f"{e.is_a()}/{e.id()}").hex)
    # IfcOpenShell 0.9.1 fills some relationship lists in random order - sort them
    for rel in f.by_type("IfcRelationship"):
        for i in range(len(rel)):
            v = rel[i]
            if isinstance(v, tuple) and v and all(isinstance(x, ifcopenshell.entity_instance) for x in v):
                rel[i] = sorted(v, key=lambda x: x.id())
    f.header.file_name.time_stamp = TIMESTAMP
    f.header.file_name.name = "example_house.ifc"
    f.header.file_description.description = ("ViewDefinition [DesignTransferView]", f"Example house {VERSION}")


# ---------------------------------------------------------------------------
# COVERAGE CHECK
# ---------------------------------------------------------------------------
_DIM = re.compile(r"^[\d.,/×x-]+$")


def family(name):
    words = name.replace("DIN links", "").replace("DIN rechts", "").split()
    keep = []
    for i, w in enumerate(words):
        if i > 0 and words[i - 1] == "Wand":
            keep.append(w)                       # internal doors keep their wall
        elif w == "×" or (_DIM.match(w) and not w.endswith("-flg.")):
            continue
        else:
            keep.append(re.sub(r"\d+", "", w) if re.match(r"^(S|C|GL)\d", w) else w)
    return " ".join(keep)


def coverage(md):
    f = md.f
    used = {t.Name for t in f.by_type("IfcTypeProduct") if t.Types and any(r.RelatedObjects for r in t.Types)}
    wanted, have, missing = {}, {}, []
    for t in f.by_type("IfcTypeProduct"):
        if t.ApplicableOccurrence and t.ApplicableOccurrence.startswith("IfcAnnotation"):
            continue
        wanted.setdefault(family(t.Name), []).append(t.Name)
    for fam, names in sorted(wanted.items()):
        hits = [n for n in names if n in used]
        have[fam] = hits
        if not hits:
            missing.append(fam)
    for kind in ("Außentür", "Innentür"):
        for side in ("DIN links", "DIN rechts"):
            if not any(n.startswith(kind) and n.endswith(side) for n in used):
                missing.append(f"{kind} … {side}")
    return wanted, have, missing


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python build_example.py TEMPLATE.ifc TARGET.ifc")
    model = build(sys.argv[1])
    model.f.write(sys.argv[2])
    wanted, have, missing = coverage(model)
    print(f"written: {sys.argv[2]} ({len(list(model.f))} entities, version {VERSION})")
    print(f"type families: {len(wanted)}, used: {len(wanted) - len([m for m in missing if m in wanted])}")
    sheets = [d for d in model.f.by_type("IfcDocumentInformation") if d.Scope == "SHEET"]
    print(f"drawings: {sum(1 for a in model.f.by_type('IfcAnnotation') if a.ObjectType == 'DRAWING')}, "
          f"sheets: {len(sheets)}")
    for m in missing:
        print("  MISSING:", m)
    sys.exit(1 if missing else 0)
